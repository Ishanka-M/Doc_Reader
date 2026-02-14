import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# 1. පිටුවේ මූලික සැකසුම්
st.set_page_config(page_title="Textile Data Extractor Pro", layout="wide")

# Header කොටස
st.title("Bulk Textile Packing List Extractor")
st.info("South Asia සහ Ocean Lanka Packing Lists සඳහා පමණි.")
st.markdown("---")

# 2. Reset Functionality
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

def reset_app():
    st.session_state.uploader_key += 1
    st.rerun()

# 3. South Asia Extraction Logic (existing)
def extract_south_asia(text, file_name):
    rows = []
    # Header දත්ත හඳුනා ගැනීම
    ship_id = re.search(r"Shipment Id[\s\n\",:]+(\d+)", text)
    batch_main = re.search(r"Batch No[\s\n\",:]+(\d+)", text)
    color = re.search(r"Color Name & No[\s\n\",:]+(.*?)\n", text)
    f_type = re.search(r"Fabric Type[\s\n\",:]+(.*?)\n", text)

    shipment_id = ship_id.group(1) if ship_id else "N/A"
    batch_no_main = batch_main.group(1) if batch_main else "N/A"
    color_info = color.group(1).strip().replace('"', '').replace(':', '').strip() if color else "N/A"
    fabric_type = f_type.group(1).strip().replace('"', '').replace(':', '').strip() if f_type else "N/A"

    # වගුවේ දත්ත (Roll #, Lot Batch No, Kg, yd)
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

# 4. Ocean Lanka Extraction Logic (improved version)
def extract_ocean_lanka(text, file_name, pdf_pages=None):
    """
    Ocean Lanka PDF වලින් පහත ක්ෂේත්‍ර උකහා ගනී:
    - Delivery Sheet No.
    - Fabric Type
    - Batch No. (each row)
    - Our Colour No. (each row)
    - R/No, Net Length, Net Weight
    """
    rows = []
    
    # ---------- 1. ශීර්ෂක දත්ත (Header fields) නිස්සාරණය ----------
    def extract_field(pattern, text, flags=0):
        match = re.search(pattern, text, flags)
        return match.group(1).strip() if match else "N/A"
    
    delivery_sheet = extract_field(r"Delivery\s*Sheet\s*No\.?\s*[:.]?\s*([A-Z0-9\-]+)", text, re.IGNORECASE)
    fabric_type    = extract_field(r"Fabric\s*Type\s*[:.]?\s*(.*?)(?=\n\s*\n|\n\s*[A-Z]|$)", text, re.DOTALL | re.IGNORECASE)
    
    # ---------- 2. pdfplumber භාවිතයෙන් වගු දත්ත ලබා ගැනීම ----------
    if pdf_pages:
        for page in pdf_pages:
            # table extraction settings වැඩිදියුණු කිරීම
            tables = page.extract_tables({
                "vertical_strategy": "lines", 
                "horizontal_strategy": "lines",
                "snap_tolerance": 3
            })
            for table in tables:
                for row in table:
                    if not row or len(row) < 3:
                        continue
                    
                    # පළමු තීරුව රෝල් අංකයද? (ඉලක්කම් පමණක්)
                    roll_cell = str(row[0]).strip() if row[0] else ""
                    if not roll_cell.isdigit():
                        continue
                    
                    # දිග සහ බර තීරු (දෙවන සහ තෙවන තීරු)
                    length_cell = str(row[1]).strip().replace(',', '.') if len(row) > 1 and row[1] else "0"
                    weight_cell = str(row[2]).strip().replace(',', '.') if len(row) > 2 and row[2] else "0"
                    
                    try:
                        length_val = float(length_cell)
                        weight_val = float(weight_cell)
                    except ValueError:
                        continue
                    
                    # ---------- 3. Dyeing and Finishing තීරුව සොයා ගැනීම ----------
                    # සාමාන්‍යයෙන් 7 වන තීරුවේ (index 6) ඇත, නමුත් සමහර විට 5 හෝ 6 විය හැක
                    finishing_cell = ""
                    for idx in [6, 5, 4]:  # 7th, 6th, 5th column
                        if len(row) > idx and row[idx]:
                            finishing_cell = str(row[idx]).strip()
                            if finishing_cell:
                                break
                    
                    # finishing_cell එකෙන් Batch No සහ Colour No උකහා ගැනීම
                    batch_no = "N/A"
                    colour_no = "N/A"
                    
                    if finishing_cell:
                        # Batch No හඳුනාගැනීම (උදා: "Batch No. PAB45980P")
                        bn_match = re.search(r"Batch\s*No\.?\s*[:.]?\s*([A-Z0-9\-]+)", finishing_cell, re.IGNORECASE)
                        if bn_match:
                            batch_no = bn_match.group(1)
                        
                        # Our Colour No හඳුනාගැනීම (උදා: "Our Colour No. VS26164-01 C004 VS WHITE")
                        cn_match = re.search(r"(?:Our\s*)?Colour\s*No\.?\s*[:.]?\s*(.*?)(?=\s*(?:Heat\s*Setting|$))", finishing_cell, re.IGNORECASE)
                        if cn_match:
                            colour_no = cn_match.group(1).strip()
                    
                    # පේළිය DataFrame එකට එකතු කිරීම
                    rows.append({
                        "Factory Source": "OCEAN LANKA",
                        "File Name": file_name,
                        "Delivery Sheet / Shipment ID": delivery_sheet,
                        "Main Batch No": batch_no,
                        "Color": colour_no,
                        "Fabric Type": fabric_type,
                        "Roll / R No": roll_cell,
                        "Lot Batch No": batch_no,  # Lot Batch No නොමැති නම් Main Batch No යොදන්න
                        "Net Weight (Kg)": weight_val,
                        "Net Length (yd)": length_val
                    })
    
    # ---------- 4. විකල්ප: pdfplumber අසාර්ථක වුවහොත් regex මගින් උත්සාහ කරන්න ----------
    if not rows:
        # සරල රේඛීය පාදක ක්‍රමයක් (අවශ්‍ය නම් පමණක්)
        lines = text.split('\n')
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0].isdigit():
                try:
                    roll = parts[0]
                    length = float(parts[1].replace(',', '.'))
                    weight = float(parts[2].replace(',', '.'))
                    rows.append({
                        "Factory Source": "OCEAN LANKA",
                        "File Name": file_name,
                        "Delivery Sheet / Shipment ID": delivery_sheet,
                        "Main Batch No": "N/A",
                        "Color": "N/A",
                        "Fabric Type": fabric_type,
                        "Roll / R No": roll,
                        "Lot Batch No": "N/A",
                        "Net Weight (Kg)": weight,
                        "Net Length (yd)": length
                    })
                except ValueError:
                    continue
    
    return rows

# 5. පරිශීලක අතුරුමුහුණත (Streamlit UI)
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
                pages = pdf.pages  # page objects ලැයිස්තුව
                for page in pages:
                    full_text += (page.extract_text() or "") + "\n"
                
                if factory_type == "SOUTH ASIA":
                    all_extracted_data.extend(extract_south_asia(full_text, file.name))
                else:
                    # pdf_pages ලබාදීම
                    all_extracted_data.extend(extract_ocean_lanka(full_text, file.name, pdf_pages=pages))

    if all_extracted_data:
        df = pd.DataFrame(all_extracted_data)
        st.success(f"ගොනු {len(uploaded_files)} සාර්ථකව කියවන ලදී.")
        st.dataframe(df, use_container_width=True)

        # Excel ගොනුවක් ලෙස ලබා ගැනීම
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
        st.error("දත්ත හඳුනා ගැනීමට නොහැකි විය. කරුණාකර නිවැරදි ආයතනය තෝරා ඇති බව සහ PDF ගොනුව නිවැරදි බව පරීක්ෂා කරන්න.")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>Developed by <b>Ishanka Madusanka</b></div>", unsafe_allow_html=True)
