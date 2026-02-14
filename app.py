import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
import google.generativeai as genai
import json
import requests
from streamlit_lottie import st_lottie

# --- 1. පද්ධතියේ මූලික සැකසුම් ---
st.set_page_config(page_title="Textile AI Extractor Pro 2026", layout="wide")

# --- CUSTOM CSS (Premium UI) ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(-45deg, #1a1a2e, #16213e, #0f3460, #1a1a2e);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: white;
    }
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    /* Glassmorphism card effect for dataframe */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px;
    }
    /* Button Styles */
    div.stButton > button:first-child {
        background-color: #4ecca3;
        color: #1a1a2e;
        border-radius: 25px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        transition: 0.3s;
    }
    div.stButton > button:first-child:hover {
        transform: scale(1.05);
        box-shadow: 0px 0px 15px #4ecca3;
    }
    </style>
    """, unsafe_allow_html=True)

# Animation loading with error handling
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None

lottie_scanning = load_lottieurl("https://lottie.host/7e60655d-3652-4752-9f6e-71c1b1207907/68VjI2Fv6B.json")

# --- 2. HEADER SECTION ---
LOGO_URL = "https://raw.githubusercontent.com/Ishanka-M/Doc_Reader/main/logo.png"

col1, col2 = st.columns([1, 6])
with col1:
    try: st.image(LOGO_URL, width=120)
    except: st.write("📂")
with col2:
    st.markdown("<h1 style='color: #4ecca3;'>Textile Packing List Extractor Pro</h1>", unsafe_allow_html=True)
    st.markdown("Automated AI Data Extraction | Gemini 3 Flash v2026")

st.markdown("---")

# --- 3. API KEY ROTATION LOGIC ---
API_KEYS = st.secrets.get("GEMINI_KEYS", [])

def get_ai_response(prompt):
    for key in API_KEYS:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name='gemini-3-flash-preview',
                generation_config={"response_mime_type": "application/json"}
            )
            response = model.generate_content(prompt)
            return response.text
        except:
            continue
    return None

# --- 4. EXTRACTION LOGIC ---
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
            "Factory": "SOUTH ASIA", "File": file_name,
            "Delivery/Shipment ID": s_id, "Main Batch": b_no,
            "Color": c_info, "Fabric Type": f_info, "Roll No": m[0],
            "Lot Batch": m[1], "Net Weight (Kg)": float(m[2]), "Net Length (yd)": float(m[3])
        })
    return rows

def extract_ocean_lanka_ai(raw_text, file_name):
    prompt = f"""
    Extract data from this Ocean Lanka Packing List. Return ONLY a JSON list of objects.
    Fields: Delivery_Sheet, Fabric_Type, Main_Batch, Color, Roll_No, Net_Weight, Net_Length.
    Text: {raw_text}
    """
    ai_res = get_ai_response(prompt)
    rows = []
    if ai_res:
        try:
            data = json.loads(ai_res)
            if isinstance(data, dict) and "table" in data: data = data["table"]
            if not isinstance(data, list): data = [data]
            for item in data:
                rows.append({
                    "Factory": "OCEAN LANKA", "File": file_name,
                    "Delivery/Shipment ID": item.get("Delivery_Sheet"),
                    "Main Batch": item.get("Main_Batch"),
                    "Color": item.get("Color"), "Fabric Type": item.get("Fabric_Type"),
                    "Roll No": item.get("Roll_No"), "Lot Batch": item.get("Main_Batch"),
                    "Net Weight (Kg)": item.get("Net_Weight"), "Net Length (yd)": item.get("Net_Length")
                })
        except: pass
    return rows

# --- 5. SIDEBAR & FILE UPLOAD ---
with st.sidebar:
    if lottie_scanning:
        st_lottie(lottie_scanning, height=150, key="side_anim")
    else:
        st.info("AI Analysis Mode: Active")
    
    st.header("Control Panel")
    factory_type = st.radio("Select Source Factory:", ["SOUTH ASIA", "OCEAN LANKA"])
    
    if st.button("Clear All Data"):
        st.rerun()

st.subheader(f"Upload {factory_type} Packing Lists (PDF)")
uploaded_files = st.file_uploader("Upload files", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")

# --- 6. PROCESSING ---
if uploaded_files:
    all_data = []
    with st.status("Gemini 3 Flash Processing...", expanded=True) as status:
        for file in uploaded_files:
            with pdfplumber.open(file) as pdf:
                full_text = "\n".join([p.extract_text() or "" for p in pdf.pages])
                if factory_type == "SOUTH ASIA":
                    all_data.extend(extract_south_asia(full_text, file.name))
                else:
                    all_data.extend(extract_ocean_lanka_ai(full_text, file.name))
        status.update(label="Analysis Completed Successfully!", state="complete", expanded=False)

    if all_data:
        st.balloons()
        df = pd.DataFrame(all_data)
        st.markdown("### Extracted Data Results")
        st.dataframe(df, use_container_width=True)

        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Structured Excel Report",
            data=output.getvalue(),
            file_name=f"{factory_type}_Report_2026.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    else:
        st.warning("No data found in the uploaded documents. Please check the factory selection.")

# --- 7. FOOTER ---
st.markdown("<br><br><hr><center style='opacity: 0.6;'>Developed by <b>Ishanka Madusanka</b> | Built for Efficiency 2026</center>", unsafe_allow_html=True)
