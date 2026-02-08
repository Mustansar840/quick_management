import streamlit as st
import pandas as pd
from datetime import datetime
import time
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
SHEET_NAME = "Car_book"

# --- CONNECTION FUNCTION (Simple Wala) ---
def get_sheet(tab_name):
    try:
        # Ye line Secrets se wo poora text utha kar key bana legi
        key_content = st.secrets["myserviceaccount"]["json_key"]
        creds_dict = json.loads(key_content)
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).worksheet(tab_name)
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

# --- ROW 6 LOGIC (Pehli Khali Row Dhoondna) ---
def get_next_row(sheet):
    # Column B (ID) ko check karo
    col_values = sheet.col_values(2)
    
    # Agar sheet khali hai to Row 6 se shuru karo
    if len(col_values) < 6: 
        return 6
        
    # Row 6 se aagay check karo kahan khali jagah hai
    for i in range(5, len(col_values)):
        if not col_values[i].strip():
            return i + 1
            
    # Agar beech mein jagah nahi mili to end mein
    return len(col_values) + 1

# --- DESIGN & LAYOUT ---
st.set_page_config(page_title="Fleet Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00ff41; font-family: 'Courier New', monospace; }
    .hacker-box { border: 2px solid #00ff41; padding: 20px; border-radius: 10px; text-align: center; background: #000; margin: 20px auto; max-width: 600px; }
    input { background-color: #111 !important; color: #00ff41 !important; border: 1px solid #00ff41 !important; }
    </style>
""", unsafe_allow_html=True)

# --- APP LOGIC ---
driver_sheet = get_sheet("Driver Data")
data = driver_sheet.get_all_records()
driver_info = {str(row.get('ID#', '')): {'name': row.get('Driver Name', ''), 'car': str(row.get('Car#', ''))} for row in data if str(row.get('ID#', ''))}

st.markdown('<div class="hacker-box">', unsafe_allow_html=True)

if 'step' not in st.session_state: st.session_state.step = "SELECT_ID"

# STEP 1: SELECT ID
if st.session_state.step == "SELECT_ID":
    st.markdown("## SELECT DRIVER ID")
    cols = st.columns(3)
    for i, d_id in enumerate(driver_info.keys()):
        with cols[i % 3]:
            if st.button(d_id):
                st.session_state.u_id = d_id
                m_sheet = get_sheet("Management")
                # Row 6 se check karo agar koi trip Pending hai
                all_vals = m_sheet.get_all_values()
                pending = None
                for idx, r in enumerate(all_vals[5:], start=6):
                    if len(r) > 14 and str(r[1]) == d_id and "Pending" in str(r[14]):
                        pending = {"row": idx, "name": r[2], "car": r[3], "start": r[5]}
                        break
                
                st.session_state.p_trip = pending
                st.session_state.step = "END_MENU" if pending else "START_MENU"
                st.rerun()

# STEP 2: START NEW TRIP
elif st.session_state.step == "START_MENU":
    st.markdown(f"### NEW TRIP: {driver_info[st.session_state.u_id]['name']}")
    val = st.number_input("Start ID Amount:", min_value=0.0)
    if val > 0: st.session_state.s_bal = val; st.session_state.step = "START_OIL"; st.rerun()

elif st.session_state.step == "START_OIL":
    val = st.number_input("Oil (KM):", min_value=0)
    if val > 0 and st.button("START TRIP 🚀"):
        m_sheet = get_sheet("Management")
        r = get_next_row(m_sheet)
        
        # Row 6 (ya agli khali row) par data dalna
        m_sheet.update_cell(r, 1, r-5) # Sr
        m_sheet.update_cell(r, 2, st.session_state.u_id) # ID
        m_sheet.update_cell(r, 3, driver_info[st.session_state.u_id]['name']) # Name
        m_sheet.update_cell(r, 4, driver_info[st.session_state.u_id]['car']) # Car
        m_sheet.update_cell(r, 5, datetime.now().strftime("%m/%d/%Y")) # Date
        m_sheet.update_cell(r, 6, st.session_state.s_bal) # Start Amount
        m_sheet.update_cell(r, 8, val) # Oil
        m_sheet.update_cell(r, 9, datetime.now().strftime("%I:%M %p")) # Time
        m_sheet.update_cell(r, 15, "Pending ⏳") # Status
        
        st.success(f"Trip Started at Row {r}")
        time.sleep(2); del st.session_state.step; st.rerun()

# STEP 3: END TRIP
elif st.session_state.step == "END_MENU":
    st.markdown(f"### ACTIVE TRIP: {st.session_state.p_trip['name']}")
    if st.button("END TRIP 🏁"): st.session_state.step = "E1"; st.rerun()

elif st.session_state.step == "E1":
    val = st.number_input("End ID Amount:", min_value=0.0)
    if val >= 0: st.session_state.ew = val; st.session_state.step = "E2"; st.rerun()

elif st.session_state.step == "E2":
    val = st.number_input("Cash in Hand:", min_value=0.0)
    if val >= 0: st.session_state.eh = val; st.session_state.step = "E3"; st.rerun()

elif st.session_state.step == "E3":
    val = st.number_input("My Account Deposit:", min_value=0.0)
    if val >= 0 and st.button("SAVE & FINISH ✅"):
        start = float(st.session_state.p_trip['start'])
        end_id = st.session_state.ew
        cash = st.session_state.eh
        bank = val
        
        id_amt = start - end_id
        total = cash + bank - id_amt
        
        m_sheet = get_sheet("Management")
        r = st.session_state.p_trip['row']
        
        m_sheet.update_cell(r, 7, end_id)
        m_sheet.update_cell(r, 10, datetime.now().strftime("%I:%M %p"))
        m_sheet.update_cell(r, 11, id_amt)
        m_sheet.update_cell(r, 12, bank)
        m_sheet.update_cell(r, 13, cash)
        m_sheet.update_cell(r, 14, total)
        m_sheet.update_cell(r, 15, "Done ✔")
        
        st.balloons()
        st.markdown(f"## TOTAL: {total}")
        time.sleep(4); del st.session_state.step; st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
