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
    .stDataFrame {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px;
    }
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
    /* Metric Card Styling */
    [data-testid="stMetricValue"] {
        color: #4ecca3 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Animation loading
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
                    "Net Weight (Kg)": float(item.get("Net_Weight", 0)), 
                    "Net Length (yd)": float(item.get("Net_Length", 0))
                })
        except: pass
    return rows

# --- 5. SIDEBAR & FILE UPLOAD ---
with st.sidebar:
    if lottie_scanning:
        st_lottie(lottie_scanning, height=150, key="side_anim")
    st.header("Control Panel")
    factory_type = st.radio("Select Source Factory:", ["SOUTH ASIA", "OCEAN LANKA"])
    if st.button("Clear All Data"):
        st.rerun()

st.subheader(f"Upload {factory_type} Packing Lists (PDF)")
uploaded_files = st.file_uploader("Upload files", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")

# --- 6. PROCESSING & VERIFICATION ---
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
        status.update(label="Analysis Completed!", state="complete", expanded=False)

    if all_data:
        df = pd.DataFrame(all_data)
        
        # --- NEW: VERIFICATION DASHBOARD ---
        st.markdown("### 📊 Data Verification Dashboard")
        
        # Summary Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Rolls", len(df))
        m2.metric("Total Weight (Kg)", f"{df['Net Weight (Kg)'].sum():.2f}")
        m3.metric("Total Length (yd)", f"{df['Net Length (yd)'].sum():.2f}")
        
        # Data Integrity Check
        missing = df.isnull().sum().sum()
        if missing == 0:
            m4.success("✅ Integrity: 100%")
        else:
            m4.warning(f"⚠️ Missing Values: {missing}")

        # Batch-wise Summary Table
        with st.expander("🔍 View Batch-wise Summary (Cross-check with PDF)"):
            summary_df = df.groupby(['Main Batch', 'Color']).agg({
                'Roll No': 'count',
                'Net Weight (Kg)': 'sum',
                'Net Length (yd)': 'sum'
            }).rename(columns={'Roll No': 'Roll Count'})
            st.dataframe(summary_df, use_container_width=True)

        st.markdown("---")
        st.markdown("### 📝 Full Data Preview")
        st.dataframe(df, use_container_width=True)

        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Verified Excel Report",
            data=output.getvalue(),
            file_name=f"{factory_type}_Verified_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        st.balloons()
    else:
        st.warning("No data found. Please check your PDF or Factory selection.")

# --- 7. FOOTER ---
st.markdown("<br><br><hr><center style='opacity: 0.6;'>Developed by <b>Ishanka Madusanka</b> | Built for Efficiency 2026</center>", unsafe_allow_html=True)
