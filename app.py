import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# 1. පිටුවේ මූලික සැකසුම්
st.set_page_config(page_title="Textile Data Extractor", layout="wide")

# GitHub වෙතින් Logo එක ලබාගන්නා Link එක
LOGO_URL = "https://raw.githubusercontent.com/Ishanka-M/Doc_Reader/main/logo.png"

# 2. ශීර්ෂය සහ Logo එක සැකසීම
col1, col2 = st.columns([1, 6])
with col1:
    try:
        st.image(LOGO_URL, width=120)
    except:
        st.write("Logo Loading...")

with col2:
    st.title("Bulk Textile Packing List Extractor")

# 3. Reset කිරීමේ පහසුකම (Session State)
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

def reset_app():
    st.session_state.uploader_key += 1
    st.rerun()

# 4. South Asia සඳහා දත්ත කියවීමේ ශ්‍රිතය
def extract_south_asia(text, file_name):
    rows = []
    shipment_id = re.search(r"Shipment Id\s*:\s*(\d+)", text).group(1) if re.search(r"Shipment Id\s*:\s*(\d+)", text) else "N/A"
    batch_no_main = re.search(r"Batch No\s*:\s*(\d+)", text).group(1) if re.search(r"Batch No\s*:\s*(\d+)", text) else "N/A"
    color = re.search(r"Color Name & No\s*:\s*(.*)", text).group(1) if re.search(r"Color Name & No\s*:\s*(.*)", text) else "N/A"
    f_type = re.search(r"Fabric Type\s*:\s*(.*)", text).group(1) if re.search(r"Fabric Type\s*:\s*(.*)", text) else "N/A"
    
    # වගුවේ දත්ත (Roll #, Lot Batch No, Kg, yd)
    pattern = re.compile(r"(\d{7})\s+([\d\-*]+)\s+(\d+\.\d+)\s+(\d+\.\d+)")
    matches = pattern.findall(text)
    for m in matches:
        rows.append({
            "Source": "SOUTH ASIA",
            "File Name": file_name,
            "Delivery Sheet / Shipment ID": shipment_id,
            "Main Batch No": batch_no_main,
            "Color Name & No": color.strip(),
            "Fabric Type": f_type.strip(),
            "Roll / R No": m[0],
            "Lot Batch No": m[1],
            "Net Weight (Kg)": float(m[2]),
            "Net Length (yd)": float(m[3])
        })
    return rows

# 5. Ocean Lanka සඳහා දත්ත කියවීමේ ශ්‍රිතය
def extract_ocean_lanka(text, file_name):
    rows = []
    
    # Header දත්ත කියවීම (Regex වැඩිදියුණු කර ඇත)
    ds_match = re.search(r"Delivery Sheet No\.\s*,\s*\"([A-Z0-9]+)\"", text)
    delivery_sheet = ds_match.group(1) if ds_match else "N/A"
    
    ft_match = re.search(r"Fabric Type\s*\",\s*\"(.*?)\"", text, re.DOTALL)
    fabric_type = ft_match.group(1).replace('\n', ' ').strip() if ft_match else "N/A"
    
    bn_match = re.search(r"Batch No\s*([A-Z0-9]+)", text)
    batch_no = bn_match.group(1) if bn_match else "N/A"
    
    cn_match = re.search(r"Our Colour No\.\s*\n\s*(.*?)\n", text)
    color_no = cn_match.group(1).strip() if cn_match else "N/A"

    # වගුවේ දත්ත කියවීම (R/ No, Net Length, Net Weight)
    # Ocean Lanka වගු පේළි රටාව: ,"No","Length","Weight"
    pattern = re.compile(r",\s*\"(\d+)\"\s*,\s*\"([\d\.,]+)\"\s*,\s*\"([\d\.,]+)\"")
    matches = pattern.findall(text)
    
    for m in matches:
        length_val = m[1].replace(',', '.')
        weight_val = m[2].replace(',', '.')
        
        rows.append({
            "Source": "OCEAN LANKA",
            "File Name": file_name,
            "Delivery Sheet / Shipment ID": delivery_sheet,
            "Main Batch No": batch_no,
            "Color Name & No": color_no,
            "Fabric Type": fabric_type,
            "Roll / R No": m[0],
            "Lot Batch No": batch_no,
            "Net Weight (Kg)": float(weight_val),
            "Net Length (yd)": float(length_val)
        })
    return rows

# 6. පරිශීලක අතුරුමුහුණත (UI)
st.markdown("---")
factory_type = st.selectbox("ආයතනය තෝරන්න (Select Factory)", ["SOUTH ASIA", "OCEAN LANKA"])

uploaded_files = st.file_uploader(
    f"{factory_type} PDF ගොනු upload කරන්න", 
    type=["pdf"], 
    accept_multiple_files=True, 
    key=f"uploader_{st.session_state.uploader_key}"
)

if st.button("Reset All"):
    reset_app()

if uploaded_files:
    all_extracted_data = []
    with st.spinner("දත්ත කියවමින් පවතී..."):
        for file in uploaded_files:
            with pdfplumber.open(file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
                
                if factory_type == "SOUTH ASIA":
                    all_extracted_data.extend(extract_south_asia(full_text, file.name))
                else:
                    all_extracted_data.extend(extract_ocean_lanka(full_text, file.name))

    df = pd.DataFrame(all_extracted_data)
    
    if not df.empty:
        st.success(f"ගොනු {len(uploaded_files)} සාර්ථකව කියවන ලදී.")
        st.dataframe(df, use_container_width=True)

        # Excel Download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Excel File",
            data=output.getvalue(),
            file_name=f"{factory_type}_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("දත්ත හඳුනා ගැනීමට නොහැකි විය. කරුණාකර නිවැරදි ආයතනය තෝරා ඇත්දැයි පරීක්ෂා කරන්න.")

# 7. පාදකය (Footer)
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.9em;'>"
    "Developed by <b>Ishanka Madusanka</b>"
    "</div>", 
    unsafe_allow_html=True
)
