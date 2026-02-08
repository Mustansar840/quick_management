import streamlit as st
import pandas as pd
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
SHEET_NAME = "Car_book"

# --- GOOGLE SHEETS CONNECTION ---
def get_sheet(tab_name):
    try:
        # Secrets se dictionary format mein data uthana
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # KEY FIX: \n ko sahi newline mein convert karna
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).worksheet(tab_name)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

# --- HELPER: ROW 6 LOGIC ---
def get_next_row(sheet):
    col_values = sheet.col_values(2)
    if len(col_values) < 6: return 6
    for i in range(5, len(col_values)):
        if not col_values[i].strip(): return i + 1
    return len(col_values) + 1

# --- HACKER UI ---
st.set_page_config(page_title="Fleet Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00ff41; font-family: 'Courier New', monospace; }
    .hacker-modal {
        border: 2px solid #00ff41; padding: 20px; border-radius: 20px;
        box-shadow: 0 0 25px #00ff41; max-width: 500px; margin: 20px auto;
        background-color: #000; text-align: center;
    }
    .stButton > button {
        border-radius: 50% !important; width: 90px !important; height: 90px !important;
        background-color: transparent !important; color: #00ff41 !important;
        border: 2px solid #00ff41 !important; font-weight: bold !important; font-size: 18px !important;
    }
    input { background-color: #000 !important; color: #00ff41 !important; border: 1px solid #00ff41 !important; text-align: center !important; font-size: 22px !important;}
    </style>
""", unsafe_allow_html=True)

# --- APP START ---
driver_sheet = get_sheet("Driver Data")
data = driver_sheet.get_all_records()
driver_info = {}
for row in data:
    d_id = str(row.get('ID#', '') or row.get('ID', ''))
    if d_id:
        driver_info[d_id] = {'name': row.get('Driver Name', ''), 'car': str(row.get('Car#', ''))}

st.markdown('<div class="hacker-modal">', unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "SELECT_ID"

# STEP 1: SELECT ID
if st.session_state.step == "SELECT_ID":
    st.markdown("## > SYSTEM_ACCESS")
    cols = st.columns(2)
    for i, d_id in enumerate(driver_info.keys()):
        with cols[i % 2]:
            if st.button(d_id):
                st.session_state.u_id = d_id
                m_sheet = get_sheet("Management")
                all_vals = m_sheet.get_all_values()
                pending_trip = None
                for idx, r in enumerate(all_vals[5:], start=6):
                    if len(r) > 14 and str(r[1]) == d_id and "Pending" in str(r[14]):
                        pending_trip = {"row": idx, "name": r[2], "car": r[3], "start": r[5]}
                        break
                st.session_state.step = "END_PROMPT" if pending_trip else "START_BAL"
                if pending_trip: st.session_state.p_trip = pending_trip
                st.rerun()

# STEP 2: START TRIP
elif st.session_state.step == "START_BAL":
    st.markdown(f"### {driver_info[st.session_state.u_id]['name']}")
    val = st.number_input("START_ID_AMOUNT:", min_value=0.0, value=None)
    if val is not None: 
        st.session_state.s_bal = val
        st.session_state.step = "START_OIL"
        st.rerun()

elif st.session_state.step == "START_OIL":
    val = st.number_input("OIL_KM:", min_value=0, value=None)
    if val is not None and st.button("START 🚀"):
        m_sheet = get_sheet("Management")
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
        st.success(f"STARTED @ ROW {row_num}")
        time.sleep(2); del st.session_state.step; st.rerun()

# STEP 3: END TRIP
elif st.session_state.step == "END_PROMPT":
    st.markdown(f"### {st.session_state.p_trip['name']} (Active)")
    if st.button("END_TRIP 🏁"): st.session_state.step = "E1"; st.rerun()

elif st.session_state.step == "E1":
    val = st.number_input("END_ID_AMOUNT:", min_value=0.0, value=None)
    if val is not None: st.session_state.ew = val; st.session_state.step = "E2"; st.rerun()

elif st.session_state.step == "E2":
    val = st.number_input("CASH_HAND:", min_value=0.0, value=None)
    if val is not None: st.session_state.eh = val; st.session_state.step = "E3"; st.rerun()

elif st.session_state.step == "E3":
    val = st.number_input("MY_ACCOUNT:", min_value=0.0, value=None)
    if val is not None and st.button("SAVE ✅"):
        start = float(st.session_state.p_trip['start'])
        end_id, cash, bank = st.session_state.ew, st.session_state.eh, val
        id_amt = start - end_id
        total = cash + bank - id_amt
        r = st.session_state.p_trip['row']
        m_sheet = get_sheet("Management")
        m_sheet.update_cell(r, 7, end_id)
        m_sheet.update_cell(r, 10, datetime.now().strftime("%I:%M %p"))
        m_sheet.update_cell(r, 11, id_amt)
        m_sheet.update_cell(r, 12, bank)
        m_sheet.update_cell(r, 13, cash)
        m_sheet.update_cell(r, 14, total)
        m_sheet.update_cell(r, 15, "Done ✔")
        st.balloons()
        st.markdown(f"<h2 style='color:#FFFF00; text-align:center;'>TOTAL: {total}</h2>", unsafe_allow_html=True)
        time.sleep(5); del st.session_state.step; st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
