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
st.set_page_config(page_title="Textile AI Extractor Pro", layout="wide")

# --- CUSTOM CSS (Animations & Styling) ---
# මෙහි ඇති CSS මඟින් පසුබිම ලස්සනට වර්ණ මාරු කරයි (Gradient Animation)
st.markdown("""
    <style>
    /* පසුබිම සඳහා Animated Gradient */
    .stApp {
        background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
    }
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Buttons සඳහා Hover effects */
    div.stButton > button:first-child {
        background-color: #ffffff;
        color: #e73c7e;
        border-radius: 20px;
        border: 2px solid #e73c7e;
        transition: all 0.3s ease;
        font-weight: bold;
    }
    div.stButton > button:first-child:hover {
        background-color: #e73c7e;
        color: white;
        transform: scale(1.05);
    }
    
    /* Dataframe එකේ පෙනුම */
    [data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.8);
        border-radius: 10px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Lottie Load Function
def load_lottieurl(url: str):
    r = requests.get(url)
    return r.json() if r.status_code == 200 else None

lottie_scanning = load_lottieurl("https://lottie.host/7e60655d-3652-4752-9f6e-71c1b1207907/68VjI2Fv6B.json")

# --- HEADER SECTION ---
LOGO_URL = "https://raw.githubusercontent.com/Ishanka-M/Doc_Reader/main/logo.png"

col1, col2 = st.columns([1, 6])
with col1:
    try: st.image(LOGO_URL, width=120)
    except: st.write("Logo")
with col2:
    st.markdown("<h1 style='color: white;'>Bulk Textile Packing List Extractor</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: white;'><i>Experience the power of AI-driven Data Extraction</i></p>", unsafe_allow_html=True)

st.markdown("---")

# --- 2. API KEY ROTATION ---
API_KEYS = st.secrets.get("GEMINI_KEYS", [])

def get_ai_response(prompt):
    for key in API_KEYS:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-3-flash-preview', 
                                          generation_config={"response_mime_type": "application/json"})
            response = model.generate_content(prompt)
            return response.text
        except: continue
    return None

# --- 3. EXTRACTION FUNCTIONS ---
def extract_south_asia(text, file_name):
    rows = []
    # (පෙර Regex Logic එකම මෙහි භාවිතා වේ)
    pattern = re.compile(r"(\d{7})\s+([\d\-*]+)\s+(\d+\.\d+)\s+(\d+\.\d+)")
    matches = pattern.findall(text)
    for m in matches:
        rows.append({
            "Source": "SOUTH ASIA", "File": file_name,
            "R No": m[0], "Net Weight": float(m[2]), "Net Length": float(m[3])
        })
    return rows

def extract_ocean_lanka_ai(raw_text, file_name):
    prompt = f"Extract packing list table into JSON: {raw_text}"
    ai_res = get_ai_response(prompt)
    rows = []
    if ai_res:
        try:
            data = json.loads(ai_res)
            # JSON Parse Logic (පෙර පරිදිම)
            for item in data if isinstance(data, list) else data.get("table", []):
                item["Source"] = "OCEAN LANKA"
                item["File"] = file_name
                rows.append(item)
        except: pass
    return rows

# --- 4. MAIN UI ---
with st.sidebar:
    st_lottie(lottie_scanning, height=150)
    st.header("Settings")
    factory_type = st.radio("Factory", ["SOUTH ASIA", "OCEAN LANKA"])
    st.info("ඔබේ PDF ගොනු මෙතැනට Drag කරන්න.")

uploaded_files = st.file_uploader("", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    all_data = []
    with st.status("Analyzing Files...", expanded=True) as status:
        for file in uploaded_files:
            with pdfplumber.open(file) as pdf:
                full_text = "\n".join([p.extract_text() or "" for p in pdf.pages])
                if factory_type == "SOUTH ASIA":
                    all_data.extend(extract_south_asia(full_text, file.name))
                else:
                    all_data.extend(extract_ocean_lanka_ai(full_text, file.name))
        status.update(label="Extraction Complete!", state="complete")

    if all_data:
        st.balloons()
        df = pd.DataFrame(all_data)
        st.dataframe(df, use_container_width=True)

        # Excel Download Button
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button("📥 Download Excel Report", data=output.getvalue(),
                           file_name=f"Extracted_Data.xlsx", type="primary")

# --- FOOTER ---
st.markdown("<br><br><center style='color: white;'>Developed by <b>Ishanka Madusanka</b></center>", unsafe_allow_html=True)
