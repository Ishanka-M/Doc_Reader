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

# --- 5. AI VERIFICATION & EXTRACTION LOGIC ---

def clean_json_string(json_str):
    """Cleans JSON string from markdown code blocks if present."""
    json_str = json_str.replace("```json", "").replace("```", "").strip()
    return json_str

def ai_verify_and_extract(text, file_name, factory_type, header_cache):
    """
    Combined Extraction and Verification function using Gemini AI.
    """
    
    # Custom Rules for Verification based on Factory
    if factory_type == "SOUTH ASIA":
        specific_instructions = """
        - Header Fields to verify: Shipment Id, Batch No, Color Name & No, Fabric Type.
        - Table Columns: Roll No (Strictly 7 digits), Lot Batch, Net Weight, Net Length.
        - Verification Rule: If 'Roll No' has OCR errors (e.g. letters instead of numbers), fix it based on context.
        """
    else: # OCEAN LANKA
        specific_instructions = """
        - Header Fields to verify: Delivery Sheet No, Main Batch, Color, Fabric Type.
        - Table Columns: Roll No, Net_Weight, Net_Length.
        - Verification Rule: Ensure Net Weight and Length are valid numbers. Convert 'O' to '0' if mistyped.
        """

    prompt = f"""
    ROLE: You are a Senior Quality Assurance Auditor for a Textile Factory.
    TASK: Extract data from the provided Packing List text AND verify its accuracy simultaneously.

    INSTRUCTIONS:
    1. **EXTRACT**: Identify the Headers and the Table Rows containing Roll details.
    2. **VERIFY & FIX**: 
       - Check for OCR errors (e.g., 'l' vs '1', 'O' vs '0', 'S' vs '5').
       - Ensure 'Net Weight' and 'Net Length' are pure numbers (floats).
       - If a Header is missing on this page, return null (we will use cache).
    
    SPECIFIC FACTORY RULES:
    {specific_instructions}

    INPUT TEXT:
    '''{text}'''
    
    OUTPUT FORMAT (Strict JSON):
    {{
        "header": {{
            "shipment_id": "value or null",
            "batch_no": "value or null",
            "color": "value or null",
            "fabric_type": "value or null"
        }},
        "rows": [
            {{ 
                "roll_no": "verified value", 
                "lot_batch": "verified value", 
                "weight": 0.00, 
                "length": 0.00,
                "status": "verified"
            }}
        ]
    }}
    """

    ai_res = get_ai_response(prompt)
    rows = []
    
    if ai_res:
        try:
            cleaned_json = clean_json_string(ai_res)
            data = json.loads(cleaned_json)
            
            # --- HEADER CACHING LOGIC ---
            h_data = data.get("header", {})
            
            # Update cache only if AI found a valid value (not null)
            if h_data.get("shipment_id") and str(h_data.get("shipment_id")).lower() != "null": 
                header_cache['s_id'] = h_data.get("shipment_id")
            if h_data.get("batch_no") and str(h_data.get("batch_no")).lower() != "null": 
                header_cache['b_no'] = h_data.get("batch_no")
            if h_data.get("color") and str(h_data.get("color")).lower() != "null": 
                header_cache['col'] = h_data.get("color")
            if h_data.get("fabric_type") and str(h_data.get("fabric_type")).lower() != "null": 
                header_cache['ft'] = h_data.get("fabric_type")

            # Use cached values if current page header is missing
            final_s_id = header_cache.get('s_id', "N/A")
            final_b_no = header_cache.get('b_no', "N/A")
            final_col = header_cache.get('col', "N/A")
            final_ft = header_cache.get('ft', "N/A")

            # --- ROW PROCESSING ---
            for item in data.get("rows", []):
                # Skip empty or invalid rows
                if not item.get("roll_no"):
                    continue

                rows.append({
                    "Factory": factory_type,
                    "File": file_name,
                    "Delivery/Shipment ID": final_s_id, 
                    "Main Batch": final_b_no,
                    "Color": final_col, 
                    "Fabric Type": final_ft, 
                    "Roll No": item.get("roll_no"),
                    "Lot Batch": item.get("lot_batch", final_b_no), 
                    "Net Weight (Kg)": float(item.get("weight", 0)), 
                    "Net Length (yd)": float(item.get("length", 0)),
                    "Verification Status": "AI Verified ✅"
                })

        except json.JSONDecodeError:
            pass # AI output failed parsing
        except Exception as e:
            pass # General error

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

    with st.status("Gemini AI Verified Processing...", expanded=True) as status:
        for idx, file in enumerate(uploaded_files):
            percent_complete = (idx + 1) / total_files
            progress_bar.progress(percent_complete)
            status_text.text(f"Verifying File {idx+1} of {total_files}: {file.name}")
            
            # Reset Header Cache for each NEW file
            header_cache = {} 

            with pdfplumber.open(file) as pdf:
                # Iterate through ALL pages
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if not page_text: continue
                    
                    # --- CALLING THE AI VERIFICATION FUNCTION ---
                    page_rows, header_cache = ai_verify_and_extract(page_text, file.name, factory_type, header_cache)
                    
                    all_data.extend(page_rows)
                    time.sleep(0.5) # Prevent Rate Limiting
        
        status.update(label="AI Verification Completed!", state="complete", expanded=False)
        status_text.empty()
        progress_bar.empty()

    if all_data:
        # --- SUCCESS UI ---
        col_s1, col_s2, col_s3 = st.columns([2, 1, 2])
        with col_s2:
            if lottie_success:
                st_lottie(lottie_success, height=180, key="success_check", loop=False)
        
        st.toast("Verification Successful!", icon='✅')
        time.sleep(1)

        df = pd.DataFrame(all_data)
        
        # --- RESULT DISPLAY ---
        st.markdown("### 📊 Shipment Wise AI Verification")
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
        st.markdown("### 📝 Full AI Verified Data Preview")
        st.dataframe(df, use_container_width=True)

        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Verified Excel Report",
            data=output.getvalue(),
            file_name=f"AI_Verified_Report_{factory_type}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    else:
        st.warning("දත්ත හඳුනාගත නොහැකි විය. කරුණාකර PDF ගොනුව පැහැදිලි දැයි පරීක්ෂා කරන්න.")

# --- 8. FOOTER ---
st.markdown("<br><br><hr><center style='opacity: 0.6;'>Developed by <b>Ishanka Madusanka</b> | 2026 AI Edition</center>", unsafe_allow_html=True)
