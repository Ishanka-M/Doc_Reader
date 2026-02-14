import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
import google.generativeai as genai
import json

# --- 1. පිටුවේ මූලික සැකසුම් සහ LOGO ---
st.set_page_config(page_title="Textile Data Extractor Pro 2026", layout="wide")

LOGO_URL = "https://raw.githubusercontent.com/Ishanka-M/Doc_Reader/main/logo.png"

col1, col2 = st.columns([1, 6])
with col1:
    try:
        st.image(LOGO_URL, width=120)
    except:
        st.write("Logo Loading...")
with col2:
    st.title("Bulk Textile Packing List Extractor (Gemini 3 Powered)")

st.markdown("---")

# --- 2. API KEY ROTATION LOGIC ---
API_KEYS = st.secrets.get("GEMINI_KEYS", [])

def get_ai_response(prompt):
    """Gemini 3 Pro/Flash මාදිලි භාවිතයෙන් Keys මාරු කරමින් දත්ත ලබා ගනී"""
    for key in API_KEYS:
        try:
            genai.configure(api_key=key)
            
            # 2026 නවතම Gemini 3 Flash මාදිලිය භාවිතා කිරීම
            # මෙම මාදිලිය Agentic coding සහ Multimodal reasoning සඳහා ඉතා දියුණුයි
            model = genai.GenerativeModel(
                model_name='gemini-3-flash-preview',
                generation_config={
                    "response_mime_type": "application/json", # කෙලින්ම JSON ලබාගැනීමට
                }
            )
            
            # දත්ත නිස්සාරණය සඳහා Minimal thinking භාවිතා කිරීම (වේගය වැඩි කිරීමට)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # එක් Key එකක් Fail වුවහොත් ඊළඟ එකට මාරු වීම
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

# --- 4. OCEAN LANKA EXTRACTION (GEMINI 3 AI) ---
def extract_ocean_lanka_ai(raw_text, file_name):
    # Gemini 3 සඳහා Prompt එක (Thinking signatures වලට ගැලපෙන සේ)
    prompt = f"""
    Analyze the following Ocean Lanka Packing List text. 
    Return a JSON list of objects containing the following fields:
    - Delivery_Sheet: (e.g. T54090)
    - Fabric_Type: Full description
    - Main_Batch: Batch Number
    - Color: Combine 'Our Colour No.' and 'Heat Setting' into one string
    - Roll_No: R/No
    - Net_Weight: (Kg)
    - Net_Length: (yd)
    
    Raw Text: 
    {raw_text}
    """
    
    ai_res = get_ai_response(prompt)
    rows = []
    
    if ai_res:
        try:
            # Gemini 3 'application/json' MIME type එක භාවිතා කරන නිසා සෘජුවම parse කළ හැක
            data = json.loads(ai_res)
            # දත්ත ලැයිස්තුවක් නොවන්නේ නම් එය ලැයිස්තුවක් බවට පත් කිරීම
            if isinstance(data, dict) and "table" in data: data = data["table"]
            
            for item in data:
                rows.append({
                    "Factory Source": "OCEAN LANKA",
                    "File Name": file_name,
                    "Delivery Sheet / Shipment ID": item.get("Delivery_Sheet", "N/A"),
                    "Main Batch No": item.get("Main_Batch", "N/A"),
                    "Color": item.get("Color", "N/A"),
                    "Fabric Type": item.get("Fabric_Type", "N/A"),
                    "Roll / R No": item.get("Roll_No", "N/A"),
                    "Lot Batch No": item.get("Main_Batch", "N/A"),
                    "Net Weight (Kg)": item.get("Net_Weight", 0),
                    "Net Length (yd)": item.get("Net_Length", 0)
                })
        except Exception as e:
            st.error(f"Error parsing AI response: {e}")
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

if st.button("Reset All"):
    st.session_state.uploader_key += 1
    st.rerun()

# --- 6. PROCESSING & DOWNLOAD ---

if uploaded_files:
    all_data = []
    with st.spinner(f"Gemini 3 Flash මඟින් {factory_type} දත්ත විශ්ලේෂණය කරයි..."):
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
st.markdown("<div style='text-align: center; color: gray;'>Developed by <b>Ishanka Madusanka</b> | Powered by Gemini 3 Flash</div>", unsafe_allow_html=True)
