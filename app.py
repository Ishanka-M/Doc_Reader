import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# 1. පිටුවේ මූලික සැකසුම්
st.set_page_config(page_title="Multi-Factory Data Extractor", layout="wide")

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

# 3. Data Extraction Functions
def extract_south_asia(text, file_name):
    rows = []
    shipment_id = re.search(r"Shipment Id\s*:\s*(\d+)", text).group(1) if re.search(r"Shipment Id\s*:\s*(\d+)", text) else "N/A"
    batch_no_main = re.search(r"Batch No\s*:\s*(\d+)", text).group(1) if re.search(r"Batch No\s*:\s*(\d+)", text) else "N/A"
    color = re.search(r"Color Name & No\s*:\s*(.*)", text).group(1) if re.search(r"Color Name & No\s*:\s*(.*)", text) else "N/A"
    f_type = re.search(r"Fabric Type\s*:\s*(.*)", text).group(1) if re.search(r"Fabric Type\s*:\s*(.*)", text) else "N/A"
    
    pattern = re.compile(r"(\d{7})\s+([\d\-*]+)\s+(\d+\.\d+)\s+(\d+\.\d+)")
    matches = pattern.findall(text)
    for m in matches:
        rows.append({
            "Source": "SOUTH ASIA", "File Name": file_name, "ID/Sheet No": shipment_id,
            "Main Batch No": batch_no_main, "Color": color.strip(), "Fabric Type": f_type.strip(),
            "Roll/R No": m[0], "Lot Batch No": m[1], "Net Weight (Kg)": float(m[2]), "Net Length (yd)": float(m[3])
        })
    return rows

def extract_ocean_lanka(text, file_name):
    rows = []
    # Header දත්ත කියවීම [cite: 24, 21, 35, 37]
    delivery_sheet = re.search(r"Delivery Sheet No\.\s*\n?\s*([A-Z0-9]+)", text).group(1) if re.search(r"Delivery Sheet No\.", text) else "N/A"
    fabric_type = re.search(r"Fabric Type\s*\n?\s*(.*?)\n", text).group(1) if re.search(r"Fabric Type", text) else "N/A"
    batch_no = re.search(r"Batch No\s*([A-Z0-9]+)", text).group(1) if re.search(r"Batch No", text) else "N/A"
    color_no = re.search(r"Our Colour No\.\s*\n?\s*(.*?)\n", text).group(1) if re.search(r"Our Colour No\.", text) else "N/A"

    # වගුවේ දත්ත කියවීම (R/ No, Net Length, Net Weight) 
    # රටාව: Roll No (1-2 digits) -> Length (xx.xx) -> Weight (xx.xx)
    pattern = re.compile(r"(\d{1,2})\s+(\d{2,3}[\.,]\d{2})\s+(\d{2}[\.,]\d{2})")
    lines = text.split('\n')
    for line in lines:
        match = pattern.search(line)
        if match:
            # කොමාව (,) තිබේ නම් තිත (.) බවට පත් කිරීම
            length = match.group(2).replace(',', '.')
            weight = match.group(3).replace(',', '.')
            rows.append({
                "Source": "OCEAN LANKA", "File Name": file_name, "ID/Sheet No": delivery_sheet,
                "Main Batch No": batch_no, "Color": color_no.strip(), "Fabric Type": fabric_type.strip(),
                "Roll/R No": match.group(1), "Lot Batch No": batch_no, 
                "Net Weight (Kg)": float(weight), "Net Length (yd)": float(length)
            })
    return rows

# 4. UI කොටස
st.markdown("---")
factory_type = st.selectbox("ආයතනය තෝරන්න (Select Factory)", ["SOUTH ASIA", "OCEAN LANKA"])

uploaded_files = st.file_uploader(
    f"{factory_type} PDF ගොනු upload කරන්න", 
    type=["pdf"], accept_multiple_files=True, 
    key=f"uploader_{st.session_state.uploader_key}"
)

if st.button("Reset All"):
    reset_app()

if uploaded_files:
    all_extracted_data = []
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
        st.success(f"{len(uploaded_files)} පද්ධතියට ඇතුළත් කරන ලදී.")
        st.dataframe(df, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Excel File",
            data=output.getvalue(),
            file_name=f"{factory_type}_Extracted_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("දත්ත කියවීමට නොහැකි විය. කරුණාකර නිවැරදි ගොනුව සහ ආයතනය තෝරන්න.")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>Developed by <b>Ishanka Madusanka</b></div>", unsafe_allow_html=True)
