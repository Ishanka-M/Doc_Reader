import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

def extract_data_from_multiple_pdfs(uploaded_files):
    all_rows = []
    
    for uploaded_file in uploaded_files:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                # 1. Header තොරතුරු (Regex භාවිතයෙන්)
                shipment_id = re.search(r"Shipment Id\s*:\s*(\d+)", text).group(1) if re.search(r"Shipment Id\s*:\s*(\d+)", text) else "N/A"
                batch_no_main = re.search(r"Batch No\s*:\s*(\d+)", text).group(1) if re.search(r"Batch No\s*:\s*(\d+)", text) else "N/A"
                color_info = re.search(r"Color Name & No\s*:\s*(.*)", text).group(1) if re.search(r"Color Name & No\s*:\s*(.*)", text) else "N/A"
                fabric_type = re.search(r"Fabric Type\s*:\s*(.*)", text).group(1) if re.search(r"Fabric Type\s*:\s*(.*)", text) else "N/A"

                # 2. වගු වල දත්ත (Roll #, Lot Batch No, Kg, yd) කියවීම
                # PDF එකේ වගු පේළියක දත්ත කොටස් 4ක් ඇති රටාව හඳුනා ගනී
                pattern = re.compile(r"(\d{7})\s+([\d\-*]+)\s+(\d+\.\d+)\s+(\d+\.\d+)")
                
                lines = text.split('\n')
                for line in lines:
                    matches = pattern.findall(line)
                    for m in matches:
                        all_rows.append({
                            "File Name": uploaded_file.name,
                            "Shipment Id": shipment_id,
                            "Main Batch No": batch_no_main,
                            "Color Name & No": color_info.strip(),
                            "Fabric Type": fabric_type.strip(),
                            "Roll #": m[0],
                            "Lot Batch No": m[1],
                            "Kg": float(m[2]),
                            "yd": float(m[3])
                        })
                
    return pd.DataFrame(all_rows)

# Streamlit UI
st.set_page_config(page_title="Bulk Textile Data Extractor", layout="wide")
st.title("📑 Bulk Textile Packing List Extractor")
st.markdown("PDF ගොනු කිහිපයක් එකවර තෝරා (Drag & Drop) සියල්ලම එකම Excel එකකට ලබාගන්න.")

# ගොනු කිහිපයක් ගැනීමට accept_multiple_files=True භාවිතා කරයි
uploaded_files = st.file_uploader("PDF ගොනු මෙතැනට Upload කරන්න", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    with st.spinner('දත්ත කියවමින් පවතී...'):
        df = extract_data_from_multiple_pdfs(uploaded_files)
    
    if not df.empty:
        st.success(f"සාර්ථකයි! PDF ගොනු {len(uploaded_files)} කින් මුළු Roll {len(df)} ක දත්ත ලබාගන්නා ලදී.")
        
        # දත්ත ප්‍රදර්ශනය (සාරාංශයක් ලෙස)
        st.dataframe(df, use_container_width=True)
        
        # Excel ලෙස සකස් කිරීම
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='All Shipments')
        
        st.download_button(
            label="📥 Download Combined Excel File",
            data=output.getvalue(),
            file_name="Combined_Textile_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("කිසිදු දත්තයක් හඳුනා ගැනීමට නොහැකි විය.")
