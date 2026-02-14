import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
import google.generativeai as genai
import json

# --- 1. CONFIGURATION ---
# මෙතැනට ඔබේ API Key එක ඇතුළත් කරන්න
GEMINI_API_KEY = "AIzaSyBrE3tUgItLKLWmNtSXZGavlCSlapPh5vQ" 
genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="Textile Data Extractor AI", layout="wide")

# --- 2. EXTRACTION LOGIC (SOUTH ASIA - REGEX) ---
def extract_south_asia(text, file_name):
    rows = []
    ship_id = re.search(r"Shipment Id[\s\n\",:]+(\d+)", text)
    batch_main = re.search(r"Batch No[\s\n\",:]+(\d+)", text)
    color = re.search(r"Color Name & No[\s\n\",:]+(.*?)\n", text)
    f_type = re.search(r"Fabric Type[\s\n\",:]+(.*?)\n", text)

    shipment_id = ship_id.group(1) if ship_id else "N/A"
    batch_no_main = batch_main.group(1) if batch_main else "N/A"
    color_info = color.group(1).strip().replace('"', '').replace(':', '').strip() if color else "N/A"
    fabric_type = f_type.group(1).strip().replace('"', '').replace(':', '').strip() if f_type else "N/A"

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

# --- 3. EXTRACTION LOGIC (OCEAN LANKA - GEMINI AI) ---
def extract_ocean_lanka_ai(raw_text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert data extractor. Extract data from this Ocean Lanka Packing List text.
    Return ONLY a valid JSON list of objects.
    
    Rules:
    1. "Delivery_Sheet": Find 'Delivery Sheet No.' (e.g., T54090).
    2. "Fabric_Type": Find 'Fabric Type' full description.
    3. "Main_Batch": Find 'Batch No' (e.g., PAB45980P).
    4. "Color": Combine 'Our Colour No.' AND 'Heat Setting' into one string.
    5. "Table": Extract each row with Roll No (R/No), Net Length, and Net Weight.
    
    Text to process:
    {raw_text}
    """
    
    try:
        response = model.generate_content(prompt)
        # JSON කොටස පමණක් පිරිසිදු කර ගැනීම
        content = response.text.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    except Exception as e:
        st.error(f"AI Error: {e}")
        return []

# --- 4. STREAMLIT UI ---
st.title("Bulk Textile Packing List Extractor (AI Powered)")
st.markdown("South Asia සහ Ocean Lanka Packing Lists සඳහා පමණි.")

if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

factory_type = st.sidebar.selectbox("ආයතනය තෝරන්න", ["SOUTH ASIA", "OCEAN LANKA"])

uploaded_files = st.file_uploader(
    f"{factory_type} PDF ගොනු upload කරන්න", 
    type=["pdf"], accept_multiple_files=True, 
    key=f"uploader_{st.session_state.uploader_key}"
)

if st.sidebar.button("Reset All"):
    st.session_state.uploader_key += 1
    st.rerun()

if uploaded_files:
    all_data = []
    progress_bar = st.progress(0)
    
    for idx, file in enumerate(uploaded_files):
        with pdfplumber.open(file) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"
            
            if factory_type == "SOUTH ASIA":
                all_data.extend(extract_south_asia(full_text, file.name))
            else:
                # Ocean Lanka සඳහා AI භාවිතා කිරීම
                with st.spinner(f"Analysing {file.name} with Gemini AI..."):
                    ai_results = extract_ocean_lanka_ai(full_text)
                    for item in ai_results:
                        # AI ලබාදෙන JSON එක වගුවට ගැලපෙන සේ සැකසීම
                        all_data.append({
                            "Factory Source": "OCEAN LANKA",
                            "File Name": file.name,
                            "Delivery Sheet / Shipment ID": item.get("Delivery_Sheet", "N/A"),
                            "Main Batch No": item.get("Main_Batch", "N/A"),
                            "Color": item.get("Color", "N/A"),
                            "Fabric Type": item.get("Fabric_Type", "N/A"),
                            "Roll / R No": item.get("Roll_No") or item.get("Table", {}).get("Roll_No") or "N/A",
                            "Lot Batch No": item.get("Main_Batch", "N/A"),
                            "Net Weight (Kg)": item.get("Net_Weight") or 0,
                            "Net Length (yd)": item.get("Net_Length") or 0
                        })
        progress_bar.progress((idx + 1) / len(uploaded_files))

    if all_data:
        df = pd.DataFrame(all_data)
        # දත්ත පිරිසිදු කිරීම (AI සමහරවිට Roll දත්ත වෙනස් ලෙස එවිය හැක)
        st.success("දත්ත සාර්ථකව උකහා ගන්නා ලදී!")
        st.dataframe(df, use_container_width=True)

        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Excel File",
            data=output.getvalue(),
            file_name=f"{factory_type}_Extracted_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
