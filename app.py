import streamlit as st
import pandas as pd
from datetime import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
import json

# --- CONFIG BASED ON ---
SHEET_NAME = "Car_book" 

# --- GOOGLE SHEETS CONNECTION (Fixed) ---
def get_sheet(tab_name):
    try:
        # Get credentials from Streamlit secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Fix private key formatting - handle escaped newlines
        private_key = creds_dict["private_key"]
        # Remove any extra spaces and ensure proper formatting
        private_key = private_key.strip()
        
        # Replace escaped newlines if they exist
        if "\\n" in private_key:
            private_key = private_key.replace("\\n", "\n")
        elif "\\\\n" in private_key:
            private_key = private_key.replace("\\\\n", "\n")
        
        # Update the credentials dictionary
        creds_dict["private_key"] = private_key
        
        # Define the scope
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        
        # Create credentials using ServiceAccountCredentials
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        
        # Authorize gspread client
        client = gspread.authorize(credentials)
        
        # Open the spreadsheet
        spreadsheet = client.open(SHEET_NAME)
        
        # Get the specific worksheet
        return spreadsheet.worksheet(tab_name)
        
    except Exception as e:
        st.error(f"Cloud Connection Failed: {e}")
        st.error("Please check your Google Sheets API access and credentials.")
        st.stop()

def get_next_available_row(sheet):
    """Hamesha Row 6 se check shuru karega"""
    col_b = sheet.col_values(2)  # ID # Column
    if len(col_b) < 6:
        return 6
    return len(col_b) + 1

# --- CSS HACKER LOOK ---
st.set_page_config(page_title="Fleet Master Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00ff41; font-family: 'Courier New', monospace; }
    .hacker-modal {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        border: 2px solid #00ff41; padding: 40px; border-radius: 20px;
        box-shadow: 0 0 25px #00ff41; max-width: 500px; margin: 30px auto;
        background-color: #000; text-align: center;
    }
    .stButton > button {
        border-radius: 50% !important; width: 90px !important; height: 90px !important;
        background-color: transparent !important; color: #00ff41 !important;
        border: 2px solid #00ff41 !important; font-weight: bold !important; font-size: 18px !important;
    }
    input { background-color: #000 !important; color: #00ff41 !important; border: 1px solid #00ff41 !important; text-align: center !important; font-size: 22px !important;}
    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- APP FLOW ---
try:
    driver_sheet = get_sheet("Driver Data")
    df_drivers = pd.DataFrame(driver_sheet.get_all_records())
    driver_info = {str(row['ID#']): {'name': row['Driver Name'], 'car': str(row['Car#'])} for _, row in df_drivers.iterrows()}
except Exception as e:
    st.error(f"Failed to load driver data: {e}")
    driver_info = {}

st.markdown('<div class="hacker-modal">', unsafe_allow_html=True)

if 'step' not in st.session_state: 
    st.session_state.step = "SELECT_ID"

# STEP 1: IDENTITY
if st.session_state.step == "SELECT_ID":
    st.markdown("## > ACCESS_CLOUD_SYSTEM")
    if not driver_info:
        st.error("No driver data loaded. Check your connection.")
    else:
        cols = st.columns(2)
        for i, d_id in enumerate(driver_info.keys()):
            with cols[i % 2]:
                if st.button(d_id):
                    st.session_state.u_id = d_id
                    try:
                        m_sheet = get_sheet("Management")
                        all_data = m_sheet.get_all_values()
                        pending_trip = None
                        # Scan from Row 6 downwards
                        for idx, r in enumerate(all_data[5:], start=6):
                            if len(r) > 14 and str(r[1]) == d_id and "Pending" in str(r[14]):
                                pending_trip = {"row": idx, "name": r[2], "car": r[3], "start": r[5]}
                                break
                        st.session_state.step = "END_PROMPT" if pending_trip else "START_BAL"
                        if pending_trip: 
                            st.session_state.p_trip = pending_trip
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error checking trips: {e}")

# --- START FLOW ---
elif st.session_state.step == "START_BAL":
    st.markdown(f"### {driver_info.get(st.session_state.u_id, {}).get('name', 'Unknown Driver')}")
    val = st.number_input("START_AMOUNT:", min_value=0.0, value=None, format="%.2f")
    if val is not None: 
        st.session_state.s_bal = val
        st.session_state.step = "START_OIL"
        st.rerun()

elif st.session_state.step == "START_OIL":
    val = st.number_input("OIL_KM:", min_value=0, value=None, step=1)
    if val is not None and st.button("INITIATE_🚀"):
        try:
            m_sheet = get_sheet("Management")
            r = get_next_available_row(m_sheet)  # Ensures Row 6+
            # Column Order: Sr(1), ID(2), Driver(3), Car(4), Date(5), Start(6), End(7), Oil(8), S_Time(9), E_Time(10), ID_Amt(11), Acc(12), Hand(13), Total(14), Status(15)
            new_row = [
                r-5, 
                st.session_state.u_id, 
                driver_info.get(st.session_state.u_id, {}).get('name', ''), 
                driver_info.get(st.session_state.u_id, {}).get('car', ''), 
                datetime.now().strftime("%m/%d/%Y"),
                st.session_state.s_bal, 
                "", 
                val, 
                datetime.now().strftime("%I:%M %p"), 
                "", 
                "", 
                "", 
                "", 
                "", 
                "Pending ⏳"
            ]
            m_sheet.insert_row(new_row, r, value_input_option='USER_ENTERED')
            st.success("CLOUD_LOG_SAVED")
            time.sleep(2)
            del st.session_state.step
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save data: {e}")

# --- END FLOW ---
elif st.session_state.step == "END_PROMPT":
    if 'p_trip' in st.session_state:
        st.markdown(f"### {st.session_state.p_trip.get('name', 'Unknown')} Active")
        if st.button("TERMINATE? 🏁"): 
            st.session_state.step = "E1"
            st.rerun()
    else:
        st.error("No pending trip found")
        del st.session_state.step
        st.rerun()

elif st.session_state.step == "E1":
    val = st.number_input("END_ID_AMOUNT:", min_value=0.0, value=None, format="%.2f")
    if val is not None: 
        st.session_state.ew = val
        st.session_state.step = "E2"
        st.rerun()

elif st.session_state.step == "E2":
    val = st.number_input("CASH_HAND:", min_value=0.0, value=None, format="%.2f")
    if val is not None: 
        st.session_state.eh = val
        st.session_state.step = "E3"
        st.rerun()

elif st.session_state.step == "E3":
    val = st.number_input("MY_ACCOUNT:", min_value=0.0, value=None, format="%.2f")
    if val is not None and st.button("FINALIZE ✅"):
        try:
            start = float(st.session_state.p_trip['start'])
            amt_id = start - st.session_state.ew
            total = st.session_state.eh + val - amt_id
            
            m_sheet = get_sheet("Management")
            r = st.session_state.p_trip['row']
            
            # Precise Updates
            m_sheet.update_cell(r, 7, st.session_state.ew)  # Col G: End ID Amount
            m_sheet.update_cell(r, 10, datetime.now().strftime("%I:%M %p"))  # Col J: End Time
            m_sheet.update_cell(r, 11, amt_id)  # Col K: ID Amount
            m_sheet.update_cell(r, 12, val)  # Col L: My Account
            m_sheet.update_cell(r, 13, st.session_state.eh)  # Col M: My Hand
            m_sheet.update_cell(r, 14, total)  # Col N: Total
            m_sheet.update_cell(r, 15, "Done ✔")  # Col O: Status
            
            st.balloons()
            st.markdown(f"<div style='border:1px solid #00ff41; padding:15px;'><h3>TOTAL: {total}</h3></div>", unsafe_allow_html=True)
            time.sleep(5)
            del st.session_state.step
            st.rerun()
        except Exception as e:
            st.error(f"Failed to update data: {e}")

st.markdown('</div>', unsafe_allow_html=True)
