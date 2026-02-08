import streamlit as st
import pandas as pd
from datetime import datetime
import time
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
SHEET_NAME = "Car_book"

# --- GOOGLE SHEETS CONNECTION ---
def get_sheet(tab_name):
    try:
        key_content = st.secrets["myserviceaccount"]["json_key"]
        creds_dict = json.loads(key_content)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).worksheet(tab_name)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

# --- HELPER: GET LAST WALLET AMOUNT ---
def get_last_wallet(driver_id, sheet_data):
    for row in reversed(sheet_data[5:]): 
        if len(row) > 6 and str(row[1]).strip() == str(driver_id).strip():
            try:
                val = str(row[6]).replace(',', '').strip()
                if val: return float(val)
            except: continue
    return 0.0

# --- HELPER: GET TOTALS (DYNAMIC FIX) ---
def get_totals(sheet_data, driver_ids):
    # Ab ye function sirf 2 bando ka nahi, balkay sab IDs ka hisaab lagayega
    stats = {d_id: 0 for d_id in driver_ids} 
    
    for row in sheet_data[5:]: 
        if len(row) > 14:
            d_id = str(row[1]).strip()
            status = str(row[14])
            # Sirf agar ID hamari list mein hai aur status Done hai
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

# --- CSS STYLING ---
st.set_page_config(page_title="Fleet Hacker Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00ff41; font-family: 'Courier New', monospace; }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 10px #00ff41; }
        50% { box-shadow: 0 0 25px #00ff41; }
        100% { box-shadow: 0 0 10px #00ff41; }
    }

    /* Dynamic Top Banner */
    .top-banner {
        display: flex; flex-wrap: wrap; justify-content: center; gap: 20px;
        padding: 15px; background: #000; border: 1px solid #00ff41;
        border-radius: 15px; margin-bottom: 20px;
    }

    .driver-circle {
        border: 2px solid #00ff41; padding: 10px; border-radius: 50%;
        width: 90px; height: 90px; display: flex; flex-direction: column;
        align-items: center; justify-content: center; text-align: center;
        box-shadow: 0 0 10px #00ff41; background: #111;
    }

    .info-box {
        width: 90%; max-width: 500px; padding: 20px;
        background-color: #000; border: 2px solid #00ff41;
        border-radius: 20px; margin: 20px auto;
        text-align: center; animation: pulse 3s infinite;
        font-size: 18px; font-weight: bold;
    }

    .receipt-card {
        background: #111; border: 2px solid #00ff41;
        padding: 20px; border-radius: 15px; margin-top: 20px; text-align: left;
    }
    .receipt-header { background: #92D050; color: black; text-align: center; font-weight: bold; padding: 5px; }
    .receipt-total { background: #FFFF00; color: black; text-align: center; font-weight: bold; font-size: 24px; padding: 10px; margin-top: 10px; }

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
    input { background-color: #000 !important; color: #00ff41 !important; border: 1px solid #00ff41 !important; text-align: center !important; font-size: 22px !important;}
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem; text-align: center;}
    </style>
""", unsafe_allow_html=True)

# --- LOAD DATA ---
try:
    # 1. Load Drivers
    driver_sheet = get_sheet("Driver Data")
    d_data = driver_sheet.get_all_records()
    driver_info = {}
    for r in d_data:
        d_id = str(r.get('ID#', '') or r.get('ID', '')).strip()
        name = r.get('Driver Name', '') or r.get('Name', '')
        car = str(r.get('Car#', '') or r.get('Car', '')).strip()
        if d_id:
            driver_info[d_id] = {'name': name, 'car': car}
    
    # 2. Load Management for Totals
    m_sheet = get_sheet("Management")
    all_vals = m_sheet.get_all_values()
    
    # Calculate Totals for ALL drivers in the list
    all_ids = list(driver_info.keys())
    totals = get_totals(all_vals, all_ids)
    
except Exception as e:
    st.error("Data Error: Please check Google Sheet columns.")
    st.stop()

# --- TOP BANNER (DYNAMIC HTML GENERATION) ---
# Ye loop ab khud hi har driver ka circle banaye ga
html_circles = ""
for d_id, info in driver_info.items():
    # Name ko short karo agar lamba hai (First name only)
    short_name = info['name'].split()[0].upper()
    total_val = totals.get(d_id, 0)
    
    html_circles += f"""
        <div class="driver-circle">
            <span style="color:#92D050; font-size:10px;">{short_name}</span>
            <b style="font-size:18px; color:#fff;">{total_val}</b>
        </div>
    """

st.markdown(f"""
    <div class="top-banner">
        {html_circles}
    </div>
""", unsafe_allow_html=True)


# --- APP FLOW ---
if 'step' not in st.session_state: st.session_state.step = "SELECT_ID"

# Info Box
if st.session_state.step == "SELECT_ID":
    st.markdown('<div class="info-box">> SYSTEM_READY<br>SELECT_IDENTITY...</div>', unsafe_allow_html=True)
elif "u_id" in st.session_state:
    u_name = driver_info[st.session_state.u_id]['name']
    u_car = driver_info[st.session_state.u_id]['car']
    status_msg = "BUSY" if "END" in st.session_state.step else "READY"
    st.markdown(f'<div class="info-box">{u_name} | {u_car}<br>STATUS: {status_msg}</div>', unsafe_allow_html=True)

# Step 1: Buttons
if st.session_state.step == "SELECT_ID":
    cols = st.columns(3)
    keys = list(driver_info.keys())
    for i, d_id in enumerate(keys):
        with cols[i % 3]:
            if st.button(d_id):
                st.session_state.u_id = d_id
                
                # Check Pending
                pending = None
                for idx, r in enumerate(all_vals[5:], start=6):
                    if len(r) > 14 and str(r[1]) == d_id and "Pending" in str(r[14]):
                        pending = {"row": idx, "name": r[2], "car": r[3], "start": r[5]}
                        break
                
                if pending:
                    st.session_state.p_trip = pending
                    st.session_state.step = "END_PROMPT"
                else:
                    last_wallet = get_last_wallet(d_id, all_vals)
                    st.session_state.suggested_start = last_wallet
                    st.session_state.step = "START_BAL"
                st.rerun()

# Step 2: Start
elif st.session_state.step == "START_BAL":
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
            m_sheet.update_cell(row_num, 1, row_num - 5)
            m_sheet.update_cell(row_num, 2, st.session_state.u_id)
            m_sheet.update_cell(row_num, 3, driver_info[st.session_state.u_id]['name'])
            m_sheet.update_cell(row_num, 4, driver_info[st.session_state.u_id]['car'])
            m_sheet.update_cell(row_num, 5, datetime.now().strftime("%m/%d/%Y"))
            m_sheet.update_cell(row_num, 6, st.session_state.s_bal)
            m_sheet.update_cell(row_num, 8, val)
            m_sheet.update_cell(row_num, 9, datetime.now().strftime("%I:%M %p"))
            m_sheet.update_cell(row_num, 15, "Pending ⏳")
            st.success("STARTED")
            time.sleep(1); del st.session_state.step; st.rerun()

# Step 3: End
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
        end_id, cash, bank = st.session_state.ew, st.session_state.eh, val
        id_amt = start - end_id
        total = cash + bank - id_amt
        r = st.session_state.p_trip['row']
        
        m_sheet.update_cell(r, 7, end_id)
        m_sheet.update_cell(r, 10, datetime.now().strftime("%I:%M %p"))
        m_sheet.update_cell(r, 11, id_amt)
        m_sheet.update_cell(r, 12, bank)
        m_sheet.update_cell(r, 13, cash)
        m_sheet.update_cell(r, 14, total)
        m_sheet.update_cell(r, 15, "Done ✔")
        
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
