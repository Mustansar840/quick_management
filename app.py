import streamlit as st
import pandas as pd
from datetime import datetime
import time
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
SHEET_NAME = "Car_book"

# --- GOOGLE SHEETS CONNECTION (Secrets JSON Method) ---
def get_sheet(tab_name):
    try:
        # Secrets se data uthana (Direct JSON method)
        key_content = st.secrets["myserviceaccount"]["json_key"]
        creds_dict = json.loads(key_content)
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).worksheet(tab_name)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

# --- HELPER: GET LAST WALLET AMOUNT (Auto-Fill Logic) ---
def get_last_wallet(driver_id, sheet_data):
    # Data Row 6 se start hota hai. Reverse check karenge taake latest entry mile.
    for row in reversed(sheet_data[5:]): 
        # Column B (index 1) ID hai, Column G (index 6) End ID Amount hai
        if len(row) > 6 and str(row[1]).strip() == str(driver_id).strip():
            try:
                val = str(row[6]).replace(',', '').strip()
                if val:
                    return float(val)
            except:
                continue
    return 0.0

# --- HELPER: GET TOTALS FOR BANNER ---
def get_totals(sheet_data):
    stats = {"9296": 0, "7772": 0} # Parwaiz, Usman IDs
    for row in sheet_data[5:]: # Row 6 se data
        # Column B (1) = ID, Column N (13) = Total, Column O (14) = Status
        if len(row) > 14:
            d_id = str(row[1]).strip()
            status = str(row[14])
            if d_id in stats and "Done" in status:
                try:
                    val = float(str(row[13]).replace(',', ''))
                    stats[d_id] += int(val)
                except: pass
    return stats

# --- HELPER: NEXT ROW ---
def get_next_row(sheet):
    col_values = sheet.col_values(2)
    if len(col_values) < 6: return 6
    for i in range(5, len(col_values)):
        if not col_values[i].strip(): return i + 1
    return len(col_values) + 1

# --- PRO HACKER CSS (DESIGN RESTORED) ---
st.set_page_config(page_title="Fleet Hacker Pro", layout="wide")
st.markdown("""
    <style>
    /* Base Theme */
    .stApp { background-color: #050505; color: #00ff41; font-family: 'Courier New', monospace; }
    
    /* Neon Pulse Animation */
    @keyframes pulse {
        0% { box-shadow: 0 0 10px #00ff41; }
        50% { box-shadow: 0 0 25px #00ff41; }
        100% { box-shadow: 0 0 10px #00ff41; }
    }

    /* Top Progress Banner */
    .top-banner {
        display: flex; justify-content: space-around; align-items: center;
        padding: 10px; background: #000; border: 1px solid #00ff41;
        border-radius: 15px; margin-bottom: 20px;
    }

    /* DYNAMIC INFO BOX */
    .info-box {
        width: 90%; max-width: 500px; padding: 20px;
        background-color: #000; border: 2px solid #00ff41;
        border-radius: 20px; margin: 20px auto;
        text-align: center; animation: pulse 3s infinite;
        font-size: 18px; font-weight: bold;
    }

    /* DIGITAL RECEIPT */
    .receipt-card {
        background: #111; border: 2px solid #00ff41;
        padding: 20px; border-radius: 15px; margin-top: 20px;
        text-align: left;
    }
    .receipt-header { background: #92D050; color: black; text-align: center; font-weight: bold; padding: 5px; }
    .receipt-total { background: #FFFF00; color: black; text-align: center; font-weight: bold; font-size: 24px; padding: 10px; margin-top: 10px; }

    /* Circle Identity Buttons */
    .stButton > button {
        border-radius: 50% !important; width: 100px !important; height: 100px !important;
        background-color: transparent !important; color: #00ff41 !important;
        border: 2px solid #00ff41 !important; font-weight: bold !important;
        font-size: 20px !important; transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #00ff41 !important; color: #000 !important;
        box-shadow: 0 0 20px #00ff41; transform: scale(1.1);
    }

    /* Input Styling */
    input { background-color: #000 !important; color: #00ff41 !important; 
            border: 1px solid #00ff41 !important; text-align: center !important; font-size: 22px !important;}
    
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem; text-align: center;}
    </style>
""", unsafe_allow_html=True)

# --- APP LOGIC START ---

# 1. FETCH DATA
try:
    # Driver Data
    driver_sheet = get_sheet("Driver Data")
    d_data = driver_sheet.get_all_records()
    # Fix Car Number Logic: Ensure keys are strings
    driver_info = {}
    for r in d_data:
        # ID aur Car ko string mein convert kiya taake match ho jaye
        d_id = str(r.get('ID#', '') or r.get('ID', '')).strip()
        name = r.get('Driver Name', '') or r.get('Name', '')
        car = str(r.get('Car#', '') or r.get('Car', '')).strip()
        if d_id:
            driver_info[d_id] = {'name': name, 'car': car}
            
    # Management Data (For Totals & History)
    m_sheet = get_sheet("Management")
    all_vals = m_sheet.get_all_values()
    totals = get_totals(all_vals)
    
except Exception as e:
    st.error("Data Load Error. Check Google Sheet Columns.")
    st.stop()

# 2. TOP BANNER DISPLAY (Totals)
st.markdown(f"""
    <div class="top-banner">
        <div style="border:1px solid #00ff41; padding:10px; border-radius:50%; width:80px; height:80px; display:flex; flex-direction:column; align-items:center; justify-content:center; font-size:12px;">
            <span style="color:#92D050;">PARWAIZ</span>
            <b style="font-size:16px;">{totals['9296']}</b>
        </div>
        <div style="font-size:30px;">⚡</div>
        <div style="border:1px solid #00ff41; padding:10px; border-radius:50%; width:80px; height:80px; display:flex; flex-direction:column; align-items:center; justify-content:center; font-size:12px;">
            <span style="color:#92D050;">USMAN</span>
            <b style="font-size:16px;">{totals['7772']}</b>
        </div>
    </div>
""", unsafe_allow_html=True)

# 3. STATE MANAGEMENT
if 'step' not in st.session_state: st.session_state.step = "SELECT_ID"

# 4. INFO BOX (Status Banner)
if st.session_state.step == "SELECT_ID":
    st.markdown('<div class="info-box">> SYSTEM_READY<br>SELECT_IDENTITY...</div>', unsafe_allow_html=True)
elif "u_id" in st.session_state:
    u_name = driver_info[st.session_state.u_id]['name']
    u_car = driver_info[st.session_state.u_id]['car']
    status_msg = "BUSY_SESSION" if "END" in st.session_state.step else "READY_FOR_START"
    st.markdown(f'<div class="info-box">USER: {u_name} | CAR: {u_car}<br>STATUS: {status_msg}</div>', unsafe_allow_html=True)

# --- STEP 1: SELECT ID ---
if st.session_state.step == "SELECT_ID":
    cols = st.columns(3)
    keys = list(driver_info.keys())
    for i, d_id in enumerate(keys):
        with cols[i % 3]:
            if st.button(d_id):
                st.session_state.u_id = d_id
                
                # Check Pending Trip
                pending = None
                for idx, r in enumerate(all_vals[5:], start=6):
                    if len(r) > 14 and str(r[1]) == d_id and "Pending" in str(r[14]):
                        pending = {"row": idx, "name": r[2], "car": r[3], "start": r[5]}
                        break
                
                if pending:
                    st.session_state.p_trip = pending
                    st.session_state.step = "END_PROMPT"
                else:
                    # Logic #1: Fetch Last Wallet for Auto-Fill
                    last_wallet = get_last_wallet(d_id, all_vals)
                    st.session_state.suggested_start = last_wallet
                    st.session_state.step = "START_BAL"
                st.rerun()

# --- STEP 2: START TRIP ---
elif st.session_state.step == "START_BAL":
    # Auto-fill logic here
    def_val = st.session_state.get('suggested_start', 0.0)
    val = st.number_input("START ID AMOUNT:", min_value=0.0, value=float(def_val))
    
    if st.button("NEXT >>"):
        st.session_state.s_bal = val
        st.session_state.step = "START_OIL"
        st.rerun()

elif st.session_state.step == "START_OIL":
    val = st.number_input("OIL (KM):", min_value=0)
    if st.button("INITIATE TRIP 🚀"):
        if val > 0:
            row_num = get_next_row(m_sheet)
            # Update cells (A-O)
            m_sheet.update_cell(row_num, 1, row_num - 5)
            m_sheet.update_cell(row_num, 2, st.session_state.u_id)
            m_sheet.update_cell(row_num, 3, driver_info[st.session_state.u_id]['name'])
            m_sheet.update_cell(row_num, 4, driver_info[st.session_state.u_id]['car'])
            m_sheet.update_cell(row_num, 5, datetime.now().strftime("%m/%d/%Y"))
            m_sheet.update_cell(row_num, 6, st.session_state.s_bal)
            m_sheet.update_cell(row_num, 8, val)
            m_sheet.update_cell(row_num, 9, datetime.now().strftime("%I:%M %p"))
            m_sheet.update_cell(row_num, 15, "Pending ⏳")
            
            st.success("SESSION STARTED")
            time.sleep(1)
            del st.session_state.step
            st.rerun()

# --- STEP 3: END TRIP ---
elif st.session_state.step == "END_PROMPT":
    if st.button("END SESSION 🏁"): st.session_state.step = "E1"; st.rerun()

elif st.session_state.step == "E1":
    val = st.number_input("END ID AMOUNT:", min_value=0.0)
    if st.button("NEXT >>"): st.session_state.ew = val; st.session_state.step = "E2"; st.rerun()

elif st.session_state.step == "E2":
    val = st.number_input("CASH IN HAND:", min_value=0.0)
    if st.button("NEXT >>"): st.session_state.eh = val; st.session_state.step = "E3"; st.rerun()

elif st.session_state.step == "E3":
    val = st.number_input("MY ACCOUNT DEPOSIT:", min_value=0.0)
    if st.button("FINALIZE & SAVE ✅"):
        start = float(st.session_state.p_trip['start'])
        end_id = st.session_state.ew
        cash = st.session_state.eh
        bank = val
        
        id_amt = start - end_id
        total = cash + bank - id_amt
        
        r = st.session_state.p_trip['row']
        # Update sheet
        m_sheet.update_cell(r, 7, end_id)
        m_sheet.update_cell(r, 10, datetime.now().strftime("%I:%M %p"))
        m_sheet.update_cell(r, 11, id_amt)
        m_sheet.update_cell(r, 12, bank)
        m_sheet.update_cell(r, 13, cash)
        m_sheet.update_cell(r, 14, total)
        m_sheet.update_cell(r, 15, "Done ✔")
        
        # Receipt Data for display
        st.session_state.res = {"hand": cash, "bank": bank, "id_amt": id_amt, "total": total}
        st.session_state.step = "RECEIPT"
        st.rerun()

elif st.session_state.step == "RECEIPT":
    res = st.session_state.res
    st.balloons()
    st.markdown(f"""
        <div class="receipt-card">
            <div class="receipt-header">DIGITAL RECEIPT</div>
            <p>> CASH HAND: <b>{res['hand']}</b></p>
            <p>> BANK DEP: <b>{res['bank']}</b></p>
            <p>> ID COST: <b>{res['id_amt']}</b></p>
            <div class="receipt-total">TOTAL: {res['total']}</div>
            <p style="text-align:center; color:#BDD7EE; margin-top:10px;">Cloud Status: Saved ✔</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("START NEW SESSION"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
