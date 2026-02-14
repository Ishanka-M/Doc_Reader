import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
import google.generativeai as genai
import json

# --- 1. පිටුවේ මූලික සැකසුම් සහ LOGO ---
st.set_page_config(page_title="Textile Data Extractor Pro", layout="wide")

# GitHub වෙතින් සෘජුවම Logo එක ලබාගන්නා Link එක
LOGO_URL = "https://raw.githubusercontent.com/Ishanka-M/Doc_Reader/main/logo.png"

col1, col2 = st.columns([1, 6])
with col1:
    try:
        st.image(LOGO_URL, width=120)
    except:
        st.write("Logo Loading...")
with col2:
    st.title("Bulk Textile Packing List Extractor")

st.markdown("---")

# --- 2. API KEY ROTATION LOGIC (Secrets වල Keys 7ක් ඇති බව උපකල්පනය කරයි) ---
API_KEYS = st.secrets.get("GEMINI_KEYS", [])

def get_ai_response(prompt):
    """Keys ලැයිස්තුව මාරු කරමින් සාර්ථක ප්‍රතිචාරයක් ලැබෙන තෙක් උත්සාහ කරයි"""
    for key in API_KEYS:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Limit එක ඉවර නම් ඊළඟ Key එකට මාරු වේ
            continue
    return None

# --- 3. SOUTH ASIA EXTRACTION (REGEX) ---
def extract_south_asia(text, file_name):
    rows = []
    ship_id = re.search(r"Shipment Id[\s\n\",:]+(\d+)", text)
    batch_main = re.search(r"Batch No[\s\n\",:]+(\d+)", text)
    color = re.search(r"Color Name & No[\s\n\",:]+(.*?)\n", text)
    f_type = re.search(r"Fabric Type[\s\n\",:]+(.*?)\n", text)

    s_id = ship_id.group(1) if ship_id else "N/A"
    b_no = batch_main.group(1) if batch_main else "N/A"
    c_info = color.group(1).strip() if color else "N/A"
    f_info = f_type.group(1).strip() if f_type else "N/A"

    pattern = re.compile(r"(\d{7})\s+([\d\-*]+)\s+(\d+\.\d+)\s+(\d+\.\d+)")
    matches = pattern.findall(text)
    for m in matches:
        rows.append({
            "Factory Source": "SOUTH ASIA",
            "File Name": file_name,
            "Delivery Sheet / Shipment ID": s_id,
            "Main Batch No": b_no,
            "Color": c_info,
            "Fabric Type": f_info,
            "Roll / R No": m[0],
            "Lot Batch No": m[1],
            "Net Weight (Kg)": float(m[2]),
            "Net Length (yd)": float(m[3])
        })
    return rows

# --- 4. OCEAN LANKA EXTRACTION (GEMINI AI) ---
def extract_ocean_lanka_ai(raw_text, file_name):
    prompt = f"""
    Extract data from this Ocean Lanka Packing List text. Return ONLY a valid JSON list.
    - Delivery_Sheet: Found near 'Delivery Sheet No.' (e.g. T54090)
    - Fabric_Type: Found near 'Fabric Type'
    - Main_Batch: Found near 'Batch No'
    - Color: COMBINE 'Our Colour No.' and 'Heat Setting' fields.
    - Table: Extract Roll No, Net Length, Net Weight.
    
    Text: {raw_text}
    """
    
    ai_res = get_ai_response(prompt)
    rows = []
    if ai_res:
        try:
            clean_json = ai_res.strip().replace("```json", "").replace("```", "")
            data = json.loads(clean_json)
            for item in data:
                rows.append({
                    "Factory Source": "OCEAN LANKA",
                    "File Name": file_name,
                    "Delivery Sheet / Shipment ID": item.get("Delivery_Sheet"),
                    "Main Batch No": item.get("Main_Batch"),
                    "Color": item.get("Color"),
                    "Fabric Type": item.get("Fabric_Type"),
                    "Roll / R No": item.get("Roll_No"),
                    "Lot Batch No": item.get("Main_Batch"),
                    "Net Weight (Kg)": item.get("Net_Weight"),
                    "Net Length (yd)": item.get("Net_Length")
                })
        except:
            pass
    return rows

# --- 5. UI - SELECT FACTORY & UPLOAD ---
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

factory_type = st.selectbox("ආයතනය තෝරන්න (Select Factory)", ["SOUTH ASIA", "OCEAN LANKA"])

uploaded_files = st.file_uploader(
    f"{factory_type} PDF ගොනු upload කරන්න", 
    type=["pdf"], accept_multiple_files=True, 
    key=f"uploader_{st.session_state.uploader_key}"
)

# Reset Button
if st.button("Reset All"):
    st.session_state.uploader_key += 1
    st.rerun()

# --- 6. PROCESSING & DOWNLOAD ---
if uploaded_files:
    all_data = []
    with st.spinner("දත්ත කියවමින් පවතී..."):
        for file in uploaded_files:
            with pdfplumber.open(file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += (page.extract_text() or "") + "\n"
                
                if factory_type == "SOUTH ASIA":
                    all_data.extend(extract_south_asia(full_text, file.name))
                else:
                    all_data.extend(extract_ocean_lanka_ai(full_text, file.name))

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
        st.error("දත්ත හඳුනා ගැනීමට නොහැකි විය. කරුණාකර නිවැරදි Factory එක තෝරා ඇත්දැයි බලන්න.")

# --- 7. FOOTER ---
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>Developed by <b>Ishanka Madusanka</b></div>", unsafe_allow_html=True)
