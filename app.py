import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
import google.generativeai as genai
import json
import requests
import time
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
    .shipment-card {
        background-color: rgba(78, 204, 163, 0.1);
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #4ecca3;
        margin-bottom: 20px;
    }
    [data-testid="stMetricValue"] {
        color: #4ecca3 !important;
    }
    /* Progress Bar Color */
    .stProgress > div > div > div > div {
        background-color: #4ecca3;
    }
    </style>
    """, unsafe_allow_html=True)

# Animation loading function
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None

# Load Animations
lottie_scanning = load_lottieurl("https://lottie.host/7e60655d-3652-4752-9f6e-71c1b1207907/68VjI2Fv6B.json")
lottie_success = load_lottieurl("https://lottie.host/31201777-743a-4460-9118-20815152866c/D6K7F9j9D9.json")

# --- 2. RESET FUNCTION ---
def reset_system():
    st.cache_data.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. HEADER SECTION ---
LOGO_URL = "https://raw.githubusercontent.com/Ishanka-M/Doc_Reader/main/logo.png"

col1, col2 = st.columns([1, 6])
with col1:
    try: st.image(LOGO_URL, width=120)
    except: st.write("📂")
with col2:
    st.markdown("<h1 style='color: #4ecca3;'>Textile Packing List Extractor Pro</h1>", unsafe_allow_html=True)
    st.markdown("Advanced Multi-Shipment AI Verification | 2026 Edition")

st.markdown("---")

# --- 4. API KEY ROTATION LOGIC ---
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

# --- 5. EXTRACTION LOGIC ---
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
    prompt = f"Extract packing list details into JSON list (fields: Delivery_Sheet, Fabric_Type, Main_Batch, Color, Roll_No, Net_Weight, Net_Length) from: {raw_text}"
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
                    "Delivery/Shipment ID": str(item.get("Delivery_Sheet", "N/A")),
                    "Main Batch": item.get("Main_Batch"),
                    "Color": item.get("Color"), "Fabric Type": item.get("Fabric_Type"),
                    "Roll No": item.get("Roll_No"), "Lot Batch": item.get("Main_Batch"),
                    "Net Weight (Kg)": float(item.get("Net_Weight", 0)), 
                    "Net Length (yd)": float(item.get("Net_Length", 0))
                })
        except: pass
    return rows

# --- 6. SIDEBAR & FILE UPLOAD ---
with st.sidebar:
    if lottie_scanning:
        st_lottie(lottie_scanning, height=150, key="side_anim")
    st.header("Control Panel")
    factory_type = st.radio("Select Source Factory:", ["SOUTH ASIA", "OCEAN LANKA"])
    
    st.markdown("---")
    if st.button("🔄 Clear & Reset System", use_container_width=True):
        reset_system()

if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

st.subheader(f"Upload {factory_type} Packing Lists (PDF)")
uploaded_files = st.file_uploader("Upload files", type=["pdf"], accept_multiple_files=True, 
                                  key=f"up_{st.session_state.uploader_key}", label_visibility="collapsed")

# --- 7. PROCESSING WITH PROGRESS BAR & SUCCESS ANIMATION ---
if uploaded_files:
    all_data = []
    
    # Progress Bar UI
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_files = len(uploaded_files)

    with st.status("Gemini 3 Flash Processing...", expanded=True) as status:
        for idx, file in enumerate(uploaded_files):
            # Update Progress
            percent_complete = (idx + 1) / total_files
            progress_bar.progress(percent_complete)
            status_text.text(f"Processing File {idx+1} of {total_files}: {file.name}")
            
            with pdfplumber.open(file) as pdf:
                full_text = "\n".join([p.extract_text() or "" for p in pdf.pages])
                if factory_type == "SOUTH ASIA":
                    all_data.extend(extract_south_asia(full_text, file.name))
                else:
                    all_data.extend(extract_ocean_lanka_ai(full_text, file.name))
        
        status.update(label="Analysis Completed Successfully!", state="complete", expanded=False)
        status_text.empty()
        progress_bar.empty()

    if all_data:
        # --- SUCCESS ANIMATION & TOAST ---
        col_s1, col_s2, col_s3 = st.columns([2, 1, 2])
        with col_s2:
            if lottie_success:
                st_lottie(lottie_success, height=180, key="success_check", loop=False)
        
        st.toast("Success! Data extracted and verified.", icon='✅')
        time.sleep(1) # Animation එක බැලීමට සුළු වෙලාවක් ලබා දීම

        df = pd.DataFrame(all_data)
        
        st.markdown("### 📊 Shipment Wise Verification")
        shipment_ids = df['Delivery/Shipment ID'].unique()
        
        for s_id in shipment_ids:
            ship_df = df[df['Delivery/Shipment ID'] == s_id]
            st.markdown(f"""
                <div class='shipment-card'>
                    <h3 style='margin:0; color: #4ecca3;'>📦 Shipment ID: {s_id}</h3>
                    <p style='margin:0; opacity: 0.8;'>Files: {", ".join(ship_df['File'].unique())}</p>
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Rolls", len(ship_df))
            c2.metric("Total Weight (Kg)", f"{ship_df['Net Weight (Kg)'].sum():.2f}")
            c3.metric("Total Length (yd)", f"{ship_df['Net Length (yd)'].sum():.2f}")
            
            with st.expander(f"🔍 View Batch Summary for {s_id}"):
                summary = ship_df.groupby(['Main Batch', 'Color']).agg({
                    'Roll No': 'count',
                    'Net Weight (Kg)': 'sum',
                    'Net Length (yd)': 'sum'
                }).rename(columns={'Roll No': 'Roll Count'})
                st.dataframe(summary, use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📝 Full Raw Data Preview")
        st.dataframe(df, use_container_width=True)

        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Verified Excel Report",
            data=output.getvalue(),
            file_name=f"Verified_Report_{factory_type}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    else:
        st.warning("දත්ත හඳුනාගත නොහැකි විය. කරුණාකර නිවැරදි Factory එක තෝරා ඇත්දැයි බලන්න.")

# --- 8. FOOTER ---
st.markdown("<br><br><hr><center style='opacity: 0.6;'>Developed by <b>Ishanka Madusanka</b> | 2026 AI Edition</center>", unsafe_allow_html=True)
