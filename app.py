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
                model_name='gemini-2.0-flash', 
                generation_config={"response_mime_type": "application/json"}
            )
            response = model.generate_content(prompt)
            return response.text
        except:
            continue
    return None

# --- 5. EXTRACTION LOGIC (UPDATED FOR MULTI-PAGE & GRID LAYOUT) ---
def extract_south_asia(text, file_name, header_cache):
    rows = []
    
    # --- 1. Header Extraction (Update Cache) ---
    ship_id_match = re.search(r"Shipment Id[\s\n\",:]+(\d+)", text, re.IGNORECASE)
    batch_main_match = re.search(r"Batch No[\s\n\",:]+(\d+)", text, re.IGNORECASE)
    
    # Regex improved to catch multi-line fabric/color descriptions
    color_match = re.search(r"Color Name & No[\s\n\",:]+(.*?)(?=\n|PO Season)", text, re.IGNORECASE)
    f_type_match = re.search(r"Fabric Type[\s\n\",:]+(.*?)(?=\n|Roll #|Location)", text, re.IGNORECASE | re.DOTALL)

    if ship_id_match: header_cache['s_id'] = ship_id_match.group(1)
    if batch_main_match: header_cache['b_no'] = batch_main_match.group(1)
    if color_match: header_cache['c_info'] = color_match.group(1).strip()
    if f_type_match: header_cache['f_info'] = f_type_match.group(1).strip().replace('\n', ' ')

    # Use cached values (Fallback for pages 2, 3...)
    s_id = header_cache.get('s_id', "N/A")
    b_no = header_cache.get('b_no', "N/A")
    c_info = header_cache.get('c_info', "N/A")
    f_info = header_cache.get('f_info', "N/A")

    # --- 2. Data Extraction (Grid Layout Support) ---
    # Regex Explanation:
    # (\d{7})       -> Roll No (Exactly 7 digits)
    # \s+           -> Space
    # ([A-Za-z0-9\-\*]+) -> Lot Batch (Digits, Letters, Dash, Asterisk - matching your image format e.g. 544691-*-*-9)
    # \s+           -> Space
    # (\d+\.\d+)    -> Net Weight
    # \s+           -> Space
    # (\d+\.\d+)    -> Net Length
    
    pattern = re.compile(r"(\d{7})\s+([A-Za-z0-9\-\*]+)\s+(\d+\.\d+)\s+(\d+\.\d+)")
    matches = pattern.findall(text)
    
    for m in matches:
        rows.append({
            "Factory": "SOUTH ASIA", "File": file_name,
            "Delivery/Shipment ID": s_id, 
            "Main Batch": b_no,
            "Color": c_info, 
            "Fabric Type": f_info, 
            "Roll No": m[0],
            "Lot Batch": m[1], 
            "Net Weight (Kg)": float(m[2]), 
            "Net Length (yd)": float(m[3])
        })
    return rows, header_cache

def extract_ocean_lanka_ai(raw_text, file_name, header_cache):
    prompt = f"Extract packing list details into JSON list (fields: Delivery_Sheet, Fabric_Type, Main_Batch, Color, Roll_No, Net_Weight, Net_Length) from page content: {raw_text}"
    ai_res = get_ai_response(prompt)
    rows = []
    if ai_res:
        try:
            data = json.loads(ai_res)
            if isinstance(data, dict) and "table" in data: data = data["table"]
            if not isinstance(data, list): data = [data]
            
            for item in data:
                # Update Cache if valid header data found
                if item.get("Delivery_Sheet") and str(item.get("Delivery_Sheet")).lower() != "null": 
                    header_cache['d_sheet'] = item.get("Delivery_Sheet")
                if item.get("Main_Batch") and str(item.get("Main_Batch")).lower() != "null": 
                    header_cache['m_batch'] = item.get("Main_Batch")
                if item.get("Color") and str(item.get("Color")).lower() != "null": 
                    header_cache['col'] = item.get("Color")
                if item.get("Fabric_Type") and str(item.get("Fabric_Type")).lower() != "null": 
                    header_cache['ft'] = item.get("Fabric_Type")

                rows.append({
                    "Factory": "OCEAN LANKA", "File": file_name,
                    "Delivery/Shipment ID": str(header_cache.get('d_sheet', "N/A")),
                    "Main Batch": header_cache.get('m_batch', "N/A"),
                    "Color": header_cache.get('col', "N/A"), 
                    "Fabric Type": header_cache.get('ft', "N/A"),
                    "Roll No": item.get("Roll_No"), 
                    "Lot Batch": header_cache.get('m_batch', "N/A"),
                    "Net Weight (Kg)": float(item.get("Net_Weight", 0)), 
                    "Net Length (yd)": float(item.get("Net_Length", 0))
                })
        except: pass
    return rows, header_cache

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

# --- 7. PROCESSING LOOP (MULTI-PAGE ENABLED) ---
if uploaded_files:
    all_data = []
    
    # Progress Bar UI
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_files = len(uploaded_files)

    with st.status("Gemini 3 Flash Processing (Deep Scan)...", expanded=True) as status:
        for idx, file in enumerate(uploaded_files):
            percent_complete = (idx + 1) / total_files
            progress_bar.progress(percent_complete)
            status_text.text(f"Processing File {idx+1} of {total_files}: {file.name}")
            
            # Reset Header Cache for each NEW file
            header_cache = {} 

            with pdfplumber.open(file) as pdf:
                # Iterate through ALL pages
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if not page_text: continue
                    
                    if factory_type == "SOUTH ASIA":
                        # Pass cache to function to remember headers from prev pages
                        page_rows, header_cache = extract_south_asia(page_text, file.name, header_cache)
                        all_data.extend(page_rows)
                    else:
                        # AI extraction with caching
                        page_rows, header_cache = extract_ocean_lanka_ai(page_text, file.name, header_cache)
                        all_data.extend(page_rows)
                        time.sleep(0.5) # Prevent Rate Limiting
        
        status.update(label="Extraction Completed Successfully!", state="complete", expanded=False)
        status_text.empty()
        progress_bar.empty()

    if all_data:
        # --- SUCCESS UI ---
        col_s1, col_s2, col_s3 = st.columns([2, 1, 2])
        with col_s2:
            if lottie_success:
                st_lottie(lottie_success, height=180, key="success_check", loop=False)
        
        st.toast("Success! Multi-page data verified.", icon='✅')
        time.sleep(1)

        df = pd.DataFrame(all_data)
        
        # --- RESULT DISPLAY ---
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
