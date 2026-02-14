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

# 4. Ocean Lanka Extraction Logic (updated for requested fields)
def extract_ocean_lanka(text, file_name):
    rows = []
    
    # Delivery Sheet No.
    ds_search = re.search(r"Delivery Sheet No\.[\s\n\",:]*([A-Z0-9\-]+)", text, re.IGNORECASE)
    delivery_sheet = ds_search.group(1) if ds_search else "N/A"
    
    # Fabric Type (multi-line possible)
    ft_search = re.search(r"Fabric Type[\s\n\",:]+(.*?)(?=\n\n|\"|BPF|Our Colour|Batch|$)", text, re.DOTALL | re.IGNORECASE)
    fabric_type = ft_search.group(1).strip().replace('\n', ' ') if ft_search else "N/A"

    # Batch No
    bn_search = re.search(r"Batch No[\s\n\",:]+([A-Z0-9\-]+)", text, re.IGNORECASE)
    batch_no = bn_search.group(1) if bn_search else "N/A"
    
    # Our Colour No (with possible surrounding quotes)
    cn_search = re.search(r"Our Colour No\.?\s*\n?\s*\"?([^\n\"]+)\"?", text, re.IGNORECASE)
    colour_no = cn_search.group(1).strip() if cn_search else "N/A"
    
    # Table data: R/No, Net Length, Net Weight
    # Regex adapted to match typical Ocean Lanka table format
    # Look for patterns like: "12345" , "123.45" , "67.89"
    table_pattern = re.compile(r',\s*\"(\d+)\s*\"\s*,\s*\"([\d\.,\s]+)\"\s*,\s*\"([\d\.,\s]+)\"')
    matches = table_pattern.findall(text)
    
    # If no matches, try alternative pattern (for different PDF layouts)
    if not matches:
        # Alternative: lines with three comma-separated values
        lines = text.split('\n')
        for line in lines:
            parts = line.strip().split(',')
            if len(parts) >= 3:
                # Try to extract roll, length, weight (may contain quotes)
                roll_match = re.search(r'\"?(\d+)\"?', parts[0])
                length_match = re.search(r'([\d\.]+)', parts[1].replace(',', '.'))
                weight_match = re.search(r'([\d\.]+)', parts[2].replace(',', '.'))
                if roll_match and length_match and weight_match:
                    matches.append((
                        roll_match.group(1),
                        length_match.group(1),
                        weight_match.group(1)
                    ))
    
    for m in matches:
        roll_no = m[0].strip()
        # Convert comma decimal separators to dots
        length_val = m[1].replace(',', '.').replace('\n', '').strip()
        weight_val = m[2].replace(',', '.').replace('\n', '').strip()
        
        try:
            rows.append({
                "Factory Source": "OCEAN LANKA",
                "File Name": file_name,
                "Delivery Sheet / Shipment ID": delivery_sheet,
                "Main Batch No": batch_no,
                "Color": colour_no,          # Our Colour No
                "Fabric Type": fabric_type,
                "Roll / R No": roll_no,
                "Lot Batch No": batch_no,    # Lot Batch No same as Main Batch No if not available separately
                "Net Weight (Kg)": float(weight_val),
                "Net Length (yd)": float(length_val)
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
                for page in pdf.pages:
                    full_text += (page.extract_text() or "") + "\n"
                
                if factory_type == "SOUTH ASIA":
                    all_extracted_data.extend(extract_south_asia(full_text, file.name))
                else:
                    all_extracted_data.extend(extract_ocean_lanka(full_text, file.name))

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
