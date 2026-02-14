import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

# 1. පිටුවේ මූලික සැකසුම්
st.set_page_config(page_title="Textile Data Extractor", layout="wide")

# GitHub වෙතින් සෘජුවම Logo එක ලබාගන්නා Link එක
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
    # Uploader එකේ key එක වෙනස් කිරීමෙන් එය reset කළ හැක
    st.session_state.uploader_key += 1
    st.rerun()

# 4. PDF දත්ත කියවීමේ ශ්‍රිතය (Function)
def extract_pdf_data(uploaded_files):
    all_data = []
    for file in uploaded_files:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                # Header තොරතුරු ලබාගැනීම [cite: 9, 10, 12]
                shipment_id = re.search(r"Shipment Id\s*:\s*(\d+)", text).group(1) if re.search(r"Shipment Id\s*:\s*(\d+)", text) else "N/A"
                batch_no_main = re.search(r"Batch No\s*:\s*(\d+)", text).group(1) if re.search(r"Batch No\s*:\s*(\d+)", text) else "N/A"
                color = re.search(r"Color Name & No\s*:\s*(.*)", text).group(1) if re.search(r"Color Name & No\s*:\s*(.*)", text) else "N/A"
                f_type = re.search(r"Fabric Type\s*:\s*(.*)", text).group(1) if re.search(r"Fabric Type\s*:\s*(.*)", text) else "N/A"

                # වගුවේ දත්ත (Roll #, Lot Batch No, Kg, yd) ලබාගැනීම 
                pattern = re.compile(r"(\d{7})\s+([\d\-*]+)\s+(\d+\.\d+)\s+(\d+\.\d+)")
                matches = pattern.findall(text)
                
                for m in matches:
                    all_data.append({
                        "File Name": file.name,
                        "Shipment Id": shipment_id,
                        "Main Batch No": batch_no_main,
                        "Color Name & No": color.strip(),
                        "Fabric Type": f_type.strip(),
                        "Roll #": m[0],
                        "Lot Batch No": m[1],
                        "Kg": float(m[2]),
                        "yd": float(m[3])
                    })
    return pd.DataFrame(all_data)

# 5. පරිශීලක අතුරුමුහුණත (UI)
st.markdown("---")
uploaded_files = st.file_uploader(
    "PDF ගොනු මෙතැනට Drag & Drop කරන්න", 
    type=["pdf"], 
    accept_multiple_files=True, 
    key=f"uploader_{st.session_state.uploader_key}"
)

# බොත්තම් පෙළගැස්වීම
c1, c2, c3 = st.columns([1, 1, 8])
with c1:
    if st.button("Reset All"):
        reset_app()

# 6. දත්ත සැකසීම සහ Excel ලබාදීම
if uploaded_files:
    with st.spinner("දත්ත කියවමින් පවතී..."):
        df = extract_pdf_data(uploaded_files)
    
    if not df.empty:
        st.success(f"ගොනු {len(uploaded_files)} ක් සාර්ථකව කියවන ලදී.")
        
        # දත්ත වගුව පෙන්වීම
        st.dataframe(df, use_container_width=True)

        # Excel ගොනුව සකස් කිරීම
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        st.download_button(
            label="📥 Download Excel File",
            data=output.getvalue(),
            file_name="Extracted_Textile_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("මෙම PDF ගොනුවලින් දත්ත හඳුනාගත නොහැකි විය.")

# 7. පාදකය (Footer)
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.9em;'>"
    "Developed by <b>Ishanka Madusanka</b>"
    "</div>", 
    unsafe_allow_html=True
)
