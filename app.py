import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIG ---
SHEET_NAME = "Car_book"

# --- CACHED CONNECTION (SPEED BOOSTER) ---
@st.cache_resource
def get_client():
    try:
        key_content = st.secrets["myserviceaccount"]["json_key"]
        creds_dict = json.loads(key_content)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Login Error: {e}")
        st.stop()

def get_sheet(client, tab_name):
    return client.open(SHEET_NAME).worksheet(tab_name)

# --- DATA LOADER (UPDATED FOR CAR NUMBER) ---
@st.cache_data(ttl=5) # 5 Second cache for speed + freshness
def load_all_data():
    client = get_client()
    
    # 1. Driver Data
    d_sheet = get_sheet(client, "Driver Data")
    d_records = d_sheet.get_all_records()
    
    drivers = {}
    for r in d_records:
        # ID Column Check
        d_id = str(r.get('ID#') or r.get('ID') or r.get('id') or '').strip()
        
        # Name Column Check
        name = str(r.get('Driver Name') or r.get('Name') or r.get('name') or '').strip()
        
        # --- CAR NUMBER FIX ---
        # Aapki sheet mein "Car Number" hai, hum sab check kar lenge
        car = str(r.get('Car Number') or r.get('Car#') or r.get('Car') or r.get('Vehicle') or '').strip()
        
        if d_id:
            drivers[d_id] = {'name': name, 'car': car}
            
    # 2. Management Data
    m_sheet = get_sheet(client, "Management")
    m_data = m_sheet.get_all_values()
    
    return drivers, m_data

# --- LOGIC FUNCTIONS ---
def get_last_wallet(driver_id, m_data):
    # Reverse loop for latest entry
    for row in reversed(m_data[5:]): 
        if len(row) > 6 and str(row[1]).strip() == str(driver_id).strip():
            try:
                val = str(row[6]).replace(',', '').strip() # Col G (End ID Amount)
                if val: return val
            except: continue
    return "0"

def get_totals(m_data, driver_ids):
    stats = {d_id: 0 for d_id in driver_ids}
    for row in m_data[5:]: 
        if len(row) > 14:
            d_id = str(row[1]).strip()
            status = str(row[14])
            if d_id in stats and "Done" in status:
                try:
                    val = float(str(row[13]).replace(',', ''))
                    stats[d_id] += int(val)
                except: pass
    return stats

def get_next_row_index(m_data):
    current_len = len(m_data)
    for i in range(5, current_len):
        if not m_data[i][1].strip(): # If ID column is empty
            return i + 1
    return current_len + 1

# --- FAST CSS ---
st.set_page_config(page_title="Fleet Fast", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #00ff41; font-family: monospace; }
    
    /* Top Circles */
    .top-banner { display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-bottom: 20px; }
    .driver-circle {
        border: 2px solid #00ff41; border-radius: 50%; width: 90px; height: 90px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        background: #111; color: #fff;
    }
    
    /* Active Red Status */
    .status-active { color: #ff4444; border: 1px solid #ff4444; padding: 10px; font-weight: bold; text-align: center; margin-bottom: 10px; }
    .status-ready { color: #00ff41; border: 1px solid #00ff41; padding: 10px; text-align: center; margin-bottom: 10px; }

    /* Input Fields - Empty & Clean */
    input { background: #111 !important; color: #fff !important; border: 1px solid #333 !important; text-align: center; font-size: 20px !important; }
    
    /* Buttons */
    .stButton > button {
        width: 100%; border: 1px solid #00ff41; background: #000; color: #00ff41;
        font-weight: bold; padding: 15px; font-size: 18px; cursor: pointer;
    }
    .stButton > button:hover { background: #00ff41; color: #000; }
    
    /* Info Helpers */
    .last-val-text { text-align: center; color: #888; font-size: 14px; margin-bottom: 5px; }
    
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --- MAIN APP ---

# 1. Load Data
try:
    driver_info, m_data = load_all_data()
    totals = get_totals(m_data, list(driver_info.keys()))
except Exception as e:
    st.error("Data loading failed. Refresh page."); st.stop()

# 2. Top Dashboard
circles_html = ""
for d_id, info in driver_info.items():
    t = totals.get(d_id, 0)
    if t > 0:
        circles_html += f"""
        <div class="driver-circle">
            <span style="font-size:10px; color:#aaa;">{info['name'].split()[0].upper()}</span>
            <b style="font-size:18px;">{t}</b>
        </div>"""
st.markdown(f'<div class="top-banner">{circles_html}</div>', unsafe_allow_html=True)

# --- SESSION HANDLING ---
if 'step' not in st.session_state: st.session_state.step = "SELECT_ID"

# 3. Steps
if st.session_state.step == "SELECT_ID":
    st.markdown("<h3 style='text-align:center'>SELECT DRIVER</h3>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, d_id in enumerate(driver_info.keys()):
        with cols[i % 3]:
            if st.button(d_id):
                st.session_state.u_id = d_id
                
                # Check Pending
                pending = None
                for idx, r in enumerate(m_data[5:], start=6):
                    if len(r) > 14 and str(r[1]) == d_id and "Pending" in str(r[14]):
                        pending = {"row": idx, "name": r[2], "car": r[3], "start": r[5]}
                        break
                
                if pending:
                    st.session_state.p_trip = pending
                    st.session_state.step = "END_PROMPT"
                else:
                    # Get Last Wallet Value (Just for hint)
                    st.session_state.last_closed = get_last_wallet(d_id, m_data)
                    st.session_state.step = "START_TRIP"
                st.rerun()

elif st.session_state.step == "START_TRIP":
    u = driver_info[st.session_state.u_id]
    
    # Display Info
    st.markdown(f"""
        <div class='status-ready'>
            STARTING NEW SESSION<br>
            USER: {u['name']} | CAR: {u['car']}
        </div>
    """, unsafe_allow_html=True)
    
    # Hint Text (Input Box Khali Hoga)
    st.markdown(f"<div class='last-val-text'>Last Closing Balance was: <b style='color:#fff'>{st.session_state.last_closed}</b></div>", unsafe_allow_html=True)
    
    # Inputs (Value = None -> Empty)
    s_amt = st.number_input("START ID AMOUNT", value=None, placeholder="Enter Start Amount")
    oil = st.number_input("OIL (KM)", value=None, placeholder="Enter Oil KM")

    if st.button("START SESSION 🚀"):
        if s_amt is not None:
            oil_val = oil if oil is not None else 0
            
            client = get_client()
            sheet = get_sheet(client, "Management")
            r_idx = get_next_row_index(m_data) 
            
            # Car number 'u['car']' ab sahi pass hoga
            row_data = [
                r_idx-5, st.session_state.u_id, u['name'], u['car'],
                datetime.now().strftime("%m/%d/%Y"), s_amt, "", oil_val,
                datetime.now().strftime("%I:%M %p"), "", "", "", "", "", "Pending ⏳"
            ]
            
            sheet.update(range_name=f"A{r_idx}:O{r_idx}", values=[row_data])
            
            st.cache_data.clear()
            st.success("Started!"); st.session_state.step = "SELECT_ID"; st.rerun()
        else:
            st.warning("Start Amount Required")

elif st.session_state.step == "END_PROMPT":
    trip = st.session_state.p_trip
    # RED ALERT FOR ACTIVE TRIP
    st.markdown(f"""
        <div class='status-active'>
            ⚠️ TRIP ACTIVE ⚠️<br>
            {trip['name']} ({trip['car']})
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("END SESSION 🏁"): st.session_state.step = "END_FORM"; st.rerun()

elif st.session_state.step == "END_FORM":
    u = driver_info[st.session_state.u_id]
    st.markdown(f"<div style='text-align:center; margin-bottom:10px;'>End Session for: <b>{u['name']}</b></div>", unsafe_allow_html=True)

    e_amt = st.number_input("END ID AMOUNT", value=None, placeholder="Enter End Amount")
    cash = st.number_input("CASH IN HAND", value=None, placeholder="Enter Cash")
    bank = st.number_input("BANK DEPOSIT", value=None, placeholder="Enter Bank")

    if st.button("SAVE & FINISH ✅"):
        if e_amt is not None and cash is not None and bank is not None:
            start = float(st.session_state.p_trip['start'])
            id_cost = start - e_amt
            total = cash + bank - id_cost
            
            client = get_client()
            sheet = get_sheet(client, "Management")
            r = st.session_state.p_trip['row']
            
            updates = [
                {'range': f'G{r}', 'values': [[e_amt]]},
                {'range': f'J{r}', 'values': [[datetime.now().strftime("%I:%M %p")]]},
                {'range': f'K{r}', 'values': [[id_cost]]},
                {'range': f'L{r}', 'values': [[bank]]},
                {'range': f'M{r}', 'values': [[cash]]},
                {'range': f'N{r}', 'values': [[total]]},
                {'range': f'O{r}', 'values': [["Done ✔"]]}
            ]
            sheet.batch_update(updates)
            
            st.session_state.res = {"h": cash, "b": bank, "id": id_cost, "t": total}
            st.cache_data.clear()
            st.session_state.step = "RECEIPT"
            st.rerun()
        else:
            st.warning("Please fill all fields")

elif st.session_state.step == "RECEIPT":
    res = st.session_state.res
    u = driver_info[st.session_state.u_id]
    st.markdown(f"""
        <div style='border:1px dashed #00ff41; padding:20px; font-family:monospace; background:#000; max-width:400px; margin:0 auto;'>
            <div style='text-align:center; border-bottom:1px dashed #00ff41; margin-bottom:10px;'>RECEIPT</div>
            <div style='display:flex; justify-content:space-between;'><span>Driver:</span><span>{u['name']}</span></div>
            <div style='display:flex; justify-content:space-between;'><span>Car:</span><span>{u['car']}</span></div>
            <hr style='border:0; border-top:1px dashed #333;'>
            <div style='display:flex; justify-content:space-between;'><span>Hand:</span><span>{res['h']}</span></div>
            <div style='display:flex; justify-content:space-between;'><span>Bank:</span><span>{res['b']}</span></div>
            <div style='display:flex; justify-content:space-between; color:#ff4444;'><span>ID Cost:</span><span>-{res['id']}</span></div>
            <div style='background:#00ff41; color:black; text-align:center; font-weight:bold; font-size:20px; margin-top:10px;'>TOTAL: {res['t']}</div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("NEW SESSION"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
