import streamlit as st
import pandas as pd
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
SHEET_NAME = "Fleet Management" # Aapki Google Sheet ka naam bilkul sahi hona chahiye

# --- GOOGLE SHEETS CONNECTION (Secrets Edition) ---
def get_sheet(tab_name):
    # Streamlit Secrets se data uthana
    creds_dict = st.secrets["gcp_service_account"]
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Keyfile name ki bajaye dictionary (dict) use ho rahi hai
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    return client.open("Fleet Management").worksheet(tab_name)

# --- CSS HACKER LOOK (CENTERED) ---
st.set_page_config(page_title="Fleet Cloud Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00ff41; font-family: 'Courier New', monospace; }
    .hacker-modal {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        border: 2px solid #00ff41; padding: 40px; border-radius: 20px;
        box-shadow: 0 0 25px #00ff41; max-width: 500px; margin: 50px auto;
        background-color: #000; text-align: center;
    }
    .stButton > button {
        border-radius: 50% !important; width: 90px !important; height: 90px !important;
        background-color: transparent !important; color: #00ff41 !important;
        border: 2px solid #00ff41 !important; font-weight: bold !important; font-size: 18px !important;
    }
    input { background-color: #000 !important; color: #00ff41 !important; border: 1px solid #00ff41 !important; text-align: center !important; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- APP LOGIC ---
try:
    # Load Driver Data from Cloud
    driver_sheet = get_sheet("Driver Data")
    df_drivers = pd.DataFrame(driver_sheet.get_all_records())
    driver_info = {str(row['ID#']): {'name': row['Driver Name'], 'car': str(row['Car#'])} for _, row in df_drivers.iterrows()}
    ids = list(driver_info.keys())
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

st.markdown('<div class="hacker-modal">', unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "SELECT_ID"

# STEP 1: ID SELECTION
if st.session_state.step == "SELECT_ID":
    st.markdown("## > ACCESS_CLOUD_SYSTEM")
    cols = st.columns(2)
    for i, d_id in enumerate(ids):
        with cols[i % 2]:
            if st.button(d_id):
                st.session_state.u_id = d_id
                # Check Pending in Management Tab
                m_sheet = get_sheet("Management")
                all_data = m_sheet.get_all_values()
                pending_trip = None
                for idx, r in enumerate(all_data[5:], start=6): # Row 6 onward
                    if str(r[2]) == d_id and "Pending" in str(r[15]):
                        pending_trip = {"row": idx, "name": r[3], "car": r[4], "start": r[6]}
                        break
                
                if pending_trip:
                    st.session_state.p_trip = pending_trip
                    st.session_state.step = "END_WIZARD"
                else:
                    st.session_state.step = "START_BAL"
                st.rerun()

# --- START FLOW ---
elif st.session_state.step == "START_BAL":
    st.markdown(f"### USER: {driver_info[st.session_state.u_id]['name']}")
    val = st.number_input("START_AMOUNT:", min_value=0.0, value=None)
    if val: 
        st.session_state.s_bal = val
        st.session_state.step = "START_OIL"; st.rerun()

elif st.session_state.step == "START_OIL":
    val = st.number_input("OIL_KM:", min_value=0, value=None)
    if val:
        if st.button("INITIATE_🚀"):
            m_sheet = get_sheet("Management")
            new_row = ["", "", st.session_state.u_id, driver_info[st.session_state.u_id]['name'], 
                       driver_info[st.session_state.u_id]['car'], datetime.now().strftime("%m/%d/%Y"),
                       st.session_state.s_bal, "", val, datetime.now().strftime("%I:%M %p"), "", "", "", "", "", "Pending ⏳"]
            m_sheet.append_row(new_row, value_input_option='USER_ENTERED')
            st.success("CLOUD_LOG_SAVED")
            time.sleep(2); del st.session_state.step; st.rerun()

# --- END FLOW & RECEIPT ---
elif st.session_state.step == "END_WIZARD":
    st.markdown(f"### {st.session_state.p_trip['name']} Active")
    if st.button("TERMINATE_SESSION?"): st.session_state.step = "E1"; st.rerun()

elif st.session_state.step == "E1":
    val = st.number_input("END_WALLET:", min_value=0.0, value=None)
    if val: st.session_state.ew = val; st.session_state.step = "E2"; st.rerun()

elif st.session_state.step == "E2":
    val = st.number_input("CASH_HAND:", min_value=0.0, value=None)
    if val: st.session_state.eh = val; st.session_state.step = "E3"; st.rerun()

elif st.session_state.step == "E3":
    val = st.number_input("BANK_TRANSFER:", min_value=0.0, value=None)
    if val:
        if st.button("SAVE_FINAL ✅"):
            start = float(st.session_state.p_trip['start'])
            amt_id = start - st.session_state.ew
            total = st.session_state.eh + val - amt_id
            
            m_sheet = get_sheet("Management")
            r = st.session_state.p_trip['row']
            # Update specific cells
            m_sheet.update_cell(r, 8, st.session_state.ew) # End Amount
            m_sheet.update_cell(r, 11, datetime.now().strftime("%I:%M %p")) # End Time
            m_sheet.update_cell(r, 12, amt_id)
            m_sheet.update_cell(r, 13, val)
            m_sheet.update_cell(r, 14, st.session_state.eh)
            m_sheet.update_cell(r, 15, total)
            m_sheet.update_cell(r, 16, "Done ✔")
            
            st.balloons()
            st.markdown(f"""
                <div style="border:1px solid #00ff41; padding:15px; background:#111;">
                    <h3 style="background:#92D050; color:black;">RECEIPT</h3>
                    <p>HAND: {st.session_state.eh} | BANK: {val}</p>
                    <h2 style="background:#FFFF00; color:black;">TOTAL: {total}</h2>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(10); del st.session_state.step; st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

