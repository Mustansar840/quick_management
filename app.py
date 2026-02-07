import streamlit as st
import pandas as pd
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
SHEET_NAME = "Car_book"  # Aapki sheet ka naam

# --- GOOGLE SHEETS CONNECTION (Secrets Fix) ---
def get_sheet(tab_name):
    try:
        # Secrets se data uthana
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # PRIVATE KEY FIX: Agar key mein \n ghalat hai to usay theek karo
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).worksheet(tab_name)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

def get_next_row(sheet):
    """Row 6 se shuru kar ke pehli khali row dhoondega"""
    # Column B (ID#) ki values uthao
    col_values = sheet.col_values(2)
    
    # Row 6 (index 5) se check karna shuru karo
    # Agar column chota hai aur row 6 exist nahi karti, to 6 return karo
    if len(col_values) < 6:
        return 6
        
    # Loop chalao row 6 se aagay
    for i in range(5, len(col_values)):
        if not col_values[i].strip():  # Agar cell khali hai
            return i + 1
            
    # Agar beech mein koi khali nahi, to end mein add karo
    return len(col_values) + 1

# --- HACKER UI CSS ---
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

# --- APP LOGIC ---
driver_sheet = get_sheet("Driver Data")
data = driver_sheet.get_all_records()
# Driver info dictionary banana
driver_info = {}
for row in data:
    # Ensure keys match exactly with your sheet headers
    d_id = str(row.get('ID#', '') or row.get('ID', ''))
    name = row.get('Driver Name', '') or row.get('Name', '')
    car = str(row.get('Car#', '') or row.get('Car', ''))
    if d_id:
        driver_info[d_id] = {'name': name, 'car': car}

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
                
                # Check Pending Status
                m_sheet = get_sheet("Management")  # Tab name check
                # Management tab spelling "MANAGMENT" hai ya "Management" check kar lein
                # Code mein "Management" use ho raha hai.
                
                all_vals = m_sheet.get_all_values()
                pending_trip = None
                
                # Row 6 se search (index 5)
                # Column O (Status) is index 14
                for idx, r in enumerate(all_vals[5:], start=6):
                    if len(r) > 14:
                        # Column B is index 1
                        if str(r[1]) == d_id and "Pending" in str(r[14]):
                            pending_trip = {
                                "row": idx, 
                                "name": r[2], # Col C
                                "car": r[3],  # Col D
                                "start": r[5] # Col F (Start ID Amt)
                            }
                            break
                
                st.session_state.step = "END_PROMPT" if pending_trip else "START_BAL"
                if pending_trip: st.session_state.p_trip = pending_trip
                st.rerun()

# --- START TRIP ---
elif st.session_state.step == "START_BAL":
    st.markdown(f"### {driver_info[st.session_state.u_id]['name']}")
    val = st.number_input("START_ID_AMOUNT:", min_value=0.0, value=None)
    if val is not None: 
        st.session_state.s_bal = val
        st.session_state.step = "START_OIL"
        st.rerun()

elif st.session_state.step == "START_OIL":
    val = st.number_input("OIL_KM:", min_value=0, value=None)
    if val is not None:
        if st.button("START_TRIP 🚀"):
            m_sheet = get_sheet("Management")
            row_num = get_next_row(m_sheet)
            
            # Data Mapping according to
            # A=1, B=2, C=3, D=4, E=5, F=6, G=7, H=8, I=9, J=10, K=11, L=12, M=13, N=14, O=15
            
            # Row number calculation for Serial Number (Column A)
            sr_no = row_num - 5
            
            # Cells update range A to O
            # Hum cell by cell update karenge taake formatting kharab na ho
            m_sheet.update_cell(row_num, 1, sr_no) # A: Sr
            m_sheet.update_cell(row_num, 2, st.session_state.u_id) # B: ID
            m_sheet.update_cell(row_num, 3, driver_info[st.session_state.u_id]['name']) # C: Driver
            m_sheet.update_cell(row_num, 4, driver_info[st.session_state.u_id]['car']) # D: Car
            m_sheet.update_cell(row_num, 5, datetime.now().strftime("%m/%d/%Y")) # E: Date
            m_sheet.update_cell(row_num, 6, st.session_state.s_bal) # F: Start ID Amt
            m_sheet.update_cell(row_num, 8, val) # H: Oil (KM)
            m_sheet.update_cell(row_num, 9, datetime.now().strftime("%I:%M %p")) # I: Start Time
            m_sheet.update_cell(row_num, 15, "Pending ⏳") # O: Status
            
            st.success("TRIP STARTED @ ROW " + str(row_num))
            time.sleep(2)
            del st.session_state.step
            st.rerun()

# --- END TRIP ---
elif st.session_state.step == "END_PROMPT":
    st.markdown(f"### {st.session_state.p_trip['name']} (Active)")
    if st.button("END_TRIP 🏁"): 
        st.session_state.step = "E1"
        st.rerun()

elif st.session_state.step == "E1":
    val = st.number_input("END_ID_AMOUNT:", min_value=0.0, value=None)
    if val is not None: 
        st.session_state.ew = val
        st.session_state.step = "E2"
        st.rerun()

elif st.session_state.step == "E2":
    val = st.number_input("CASH_HAND:", min_value=0.0, value=None)
    if val is not None: 
        st.session_state.eh = val
        st.session_state.step = "E3"
        st.rerun()

elif st.session_state.step == "E3":
    val = st.number_input("MY_ACCOUNT:", min_value=0.0, value=None)
    if val is not None:
        if st.button("FINALIZE & SAVE ✅"):
            try:
                start = float(st.session_state.p_trip['start'])
            except:
                start = 0.0
                
            end_id_val = st.session_state.ew
            cash_hand = st.session_state.eh
            my_account = val
            
            # Calculation
            # ID Amount (Col K) = Start (F) - End (G)
            id_amount = start - end_id_val
            
            # Total (Col N) = Cash Hand (M) + My Account (L) - ID Amount (K)
            # Formula check: Total = (Hand + Bank) - (Start - End)
            total = cash_hand + my_account - id_amount
            
            m_sheet = get_sheet("Management")
            r = st.session_state.p_trip['row']
            
            # Update End Data
            m_sheet.update_cell(r, 7, end_id_val) # G: End ID Amt
            m_sheet.update_cell(r, 10, datetime.now().strftime("%I:%M %p")) # J: End Time
            m_sheet.update_cell(r, 11, id_amount) # K: ID Amt
            m_sheet.update_cell(r, 12, my_account) # L: My Account
            m_sheet.update_cell(r, 13, cash_hand) # M: My Hand
            m_sheet.update_cell(r, 14, total) # N: Total
            m_sheet.update_cell(r, 15, "Done ✔") # O: Status
            
            st.balloons()
            st.markdown(f"""
                <div style='border:1px solid #00ff41; padding:20px; text-align:left;'>
                    <h3 style='color:#fff; border-bottom:1px solid #00ff41;'>RECEIPT</h3>
                    <p>HAND: {cash_hand} | BANK: {my_account}</p>
                    <p>ID_AMT: {id_amount}</p>
                    <h2 style='color:#FFFF00;'>TOTAL: {total}</h2>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(5)
            del st.session_state.step
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
