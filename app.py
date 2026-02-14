import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# 1. පිටුවේ මූලික සැකසුම්
st.set_page_config(page_title="Textile Data Extractor", layout="wide")

# GitHub Logo URL
LOGO_URL = "https://raw.githubusercontent.com/Ishanka-M/Doc_Reader/main/logo.png"

# Header කොටස
col1, col2 = st.columns([1, 6])
with col1:
    try: st.image(LOGO_URL, width=120)
    except: st.write("Logo Loading...")
with col2:
    st.title("Bulk Textile Packing List Extractor")

# 2. Reset Functionality
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

def reset_app():
    st.session_state.uploader_key += 1
    st.rerun()

# 3. South Asia Extraction Logic
def extract_south_asia(text, file_name):
    rows = []
    # Header දත්ත හඳුනා ගැනීම [cite: 9, 10]
    ship_id = re.search(r"Shipment Id[\s\n\",:]+(\d+)", text)
    batch_main = re.search(r"Batch No[\s\n\",:]+(\d+)", text)
    color = re.search(r"Color Name & No[\s\n\",:]+(.*?)\n", text)
    f_type = re.search(r"Fabric Type[\s\n\",:]+(.*?)\n", text)

    shipment_id = ship_id.group(1) if ship_id else "N/A"
    batch_no_main = batch_main.group(1) if batch_main else "N/A"
    color_info = color.group(1).strip().replace('"', '') if color else "N/A"
    fabric_type = f_type.group(1).strip().replace('"', '') if f_type else "N/A"

    # වගුවේ දත්ත (Roll #, Lot Batch No, Kg, yd) [cite: 15]
    pattern = re.compile(r"(\d{7})\s+([\d\-*]+)\s+(\d+\.\d+)\s+(\d+\.\d+)")
    matches = pattern.findall(text)
    for m in matches:
        rows.append({
            "Factory Source": "SOUTH ASIA",
            "File Name": file_name,
            "Delivery Sheet / Shipment ID": shipment_id,
            "Main Batch No": batch_no_main,
            "Color": color_info,
            "Fabric Type": fabric_type,
            "Roll / R No": m[0],
            "Lot Batch No": m[1],
            "Net Weight (Kg)": float(m[2]),
            "Net Length (yd)": float(m[3])
        })
    return rows

# 4. Ocean Lanka Extraction Logic
def extract_ocean_lanka(text, file_name):
    rows = []
    
    # Delivery Sheet No [cite: 24]
    ds_search = re.search(r"Delivery Sheet No\.[\s\n\",]+([A-Z0-9]+)", text)
    delivery_sheet = ds_search.group(1) if ds_search else "N/A"
    
    # Fabric Type [cite: 21]
    ft_search = re.search(r"Fabric Type[\s\n\",]+(.*?)(?=\n\n|\"|$)", text, re.DOTALL)
    fabric_type_raw = ft_search.group(1).strip() if ft_search else "N/A"
    fabric_type = fabric_type_raw.split('\n')[-1].replace('"', '').strip()

    # Batch No [cite: 35]
    bn_search = re.search(r"Batch No\s+([A-Z0-9]+)", text)
    batch_no = bn_search.group(1) if bn_search else "N/A"
    
    # --- Our Colour No සහ Heat Setting එකට සම්බන්ධ කිරීම  ---
    cn_match = re.search(r"Our Colour No\.[\s\n\",]+(.*?)(?=\nHeat Setting|\n[A-Z]|$)", text, re.DOTALL)
    hs_match = re.search(r"Heat Setting[\s\n\",]+(.*?)\n", text)
    
    color_val = cn_match.group(1).strip().replace('"', '').replace('\n', ' ') if cn_match else ""
    heat_val = hs_match.group(1).strip().replace('"', '') if hs_match else ""
    # "VS26164-01 C004 VS WHITE 95D1/LARGE DOTS" ආකාරයට එකතු කිරීම
    final_color = f"{color_val} {heat_val}".strip() if color_val or heat_val else "N/A"

    # 📊 වගුවේ දත්ත (R/ No, Net Length, Net Weight) 
    # මෙහි දත්ත අතර ඇති \n ඉවත් කර නිවැරදිව කියවීමට Regex වැඩිදියුණු කර ඇත
    table_pattern = re.compile(r",\s*\"(\d+)[\s\n]*\"\s*,\s*\"([\d\.,\s\n]+)\"\s*,\s*\"([\d\.,\s\n]+)\"")
    matches = table_pattern.findall(text)
    
    for m in matches:
        roll_no = m[0].strip()
        length_val = m[1].replace(',', '.').replace('\n', '').strip()
        weight_val = m[2].replace(',', '.').replace('\n', '').strip()
        
        try:
            rows.append({
                "Factory Source": "OCEAN LANKA",
                "File Name": file_name,
                "Delivery Sheet / Shipment ID": delivery_sheet,
                "Main Batch No": batch_no,
                "Color": final_color,
                "Fabric Type": fabric_type,
                "Roll / R No": roll_no,
                "Lot Batch No": batch_no,
                "Net Weight (Kg)": float(weight_val),
                "Net Length (yd)": float(length_val)
            })
        except ValueError:
            continue
            
    return rows

# 5. UI කොටස
st.markdown("---")
factory_type = st.selectbox("ආයතනය තෝරන්න (Select Factory)", ["SOUTH ASIA", "OCEAN LANKA"])

uploaded_files = st.file_uploader(
    f"{factory_type} PDF ගොනු upload කරන්න", type=["pdf"], 
    accept_multiple_files=True, key=f"uploader_{st.session_state.uploader_key}"
)

if st.button("Reset All"):
    reset_app()

if uploaded_files:
    all_data = []
    with st.spinner("දත්ත කියවමින් පවතී..."):
        for file in uploaded_files:
            with pdfplumber.open(file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
                
                if factory_type == "SOUTH ASIA":
                    all_data.extend(extract_south_asia(full_text, file.name))
                else:
                    all_data.extend(extract_ocean_lanka(full_text, file.name))

    if all_data:
        df = pd.DataFrame(all_data)
        st.success(f"ගොනු {len(uploaded_files)} සාර්ථකව කියවන ලදී.")
        st.dataframe(df, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Excel File", data=output.getvalue(),
            file_name=f"{factory_type}_Extracted_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("දත්ත හඳුනා ගැනීමට නොහැකි විය. කරුණාකර නිවැරදි ආයතනය තෝරා ඇත්දැයි පරීක්ෂා කරන්න.")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>Developed by <b>Ishanka Madusanka</b></div>", unsafe_allow_html=True)
