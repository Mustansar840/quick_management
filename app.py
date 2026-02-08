import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIG ---
SHEET_NAME = "Car_book"

# --- FAST CONNECTION ---
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

# --- LOGIC: FETCH LAST AMOUNT ---
def get_last_wallet(driver_id, sheet_data):
    # Reverse search for speed
    for row in reversed(sheet_data[5:]): 
        if len(row) > 6 and str(row[1]).strip() == str(driver_id).strip():
            try:
                val = str(row[6]).replace(',', '').strip()
                if val: return float(val)
            except: continue
    return 0.0

# --- LOGIC: CALCULATE TOTALS ---
def get_totals(sheet_data, driver_ids):
    stats = {d_id: 0 for d_id in driver_ids}
    for row in sheet_data[5:]: 
        if len(row) > 14:
            d_id = str(row[1]).strip()
            status = str(row[14])
            if d_id in stats and "Done" in status:
                try:
                    val = float(str(row[13]).replace(',', ''))
                    stats[d_id] += int(val)
                except: pass
    return stats

# --- LOGIC: FIND EMPTY ROW ---
def get_next_row(sheet):
    col_values = sheet.col_values(2)
    if len(col_values) < 6: return 6
    for i in range(5, len(col_values)):
        if not col_values[i].strip(): return i + 1
    return len(col_values) + 1

# --- STATIC CSS (NO ANIMATION = FAST) ---
st.set_page_config(page_title="Fleet Fast", layout="wide")
st.markdown("""
    <style>
    /* Clean Fast Theme */
    .stApp { background-color: #000000; color: #00ff41; font-family: monospace; }
    
    /* Static Banner - No Flex Wrap lag for speed */
    .top-banner {
        display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;
        padding: 10px; border-bottom: 1px solid #00ff41; margin-bottom: 20px;
    }

    /* Simple Circles - No Hover/Pulse */
    .driver-circle {
        border: 1px solid #00ff41; padding: 5px; border-radius: 50%;
        width: 80px; height: 80px; display: flex; flex-direction: column;
        align-items: center; justify-content: center; text-align: center;
        background: #111;
    }

    /* Simple Info Box */
    .info-box {
        border: 1px solid #00ff41; padding: 10px; text-align: center;
        margin-bottom: 10px; font-weight: bold; background: #050505;
    }

    /* Receipt */
    .receipt-card {
        border: 1px dashed #00ff41; padding: 20px; font-family: monospace;
        margin-top: 10px; background: #000;
    }
    .receipt-row { display: flex; justify-content: space-between; margin-bottom: 5px; }

    /* Inputs & Buttons - Minimal */
    .stButton > button {
        width: 100%; border: 1px solid #00ff41; background: #000; color: #00ff41;
        font-weight: bold; padding: 10px;
    }
    .stButton > button:hover { background: #00ff41; color: #000; }
    
    input { background: #111 !important; color: #fff !important; border: 1px solid #333 !important; text-align: center; }
    
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --- LOAD DATA ---
try:
    driver_sheet = get_sheet("Driver Data")
    d_data = driver_sheet.get_all_records()
    driver_info = {}
    for r in d_data:
        d_id = str(r.get('ID#', '') or r.get('ID', '')).strip()
        name = r.get('Driver Name', '') or r.get('Name', '')
        car = str(r.get('Car#', '') or r.get('Car', '')).strip()
        if d_id: driver_info[d_id] = {'name': name, 'car': car}
            
    m_sheet = get_sheet("Management")
    all_vals = m_sheet.get_all_values()
    totals = get_totals(all_vals, list(driver_info.keys()))
except:
    st.error("Data Load Error"); st.stop()

# --- TOP DASHBOARD ---
circles = ""
for d_id, info in driver_info.items():
    t_val = totals.get(d_id, 0)
    if t_val > 0:
        circles += f"""
            <div class="driver-circle">
                <span style="font-size:10px; color:#aaa;">{info['name'].split()[0].upper()}</span>
                <b style="font-size:16px; color:#fff;">{t_val}</b>
            </div>"""

st.markdown(f'<div class="top-banner">{circles if circles else "NO ACTIVE DRIVERS"}</div>', unsafe_allow_html=True)

# --- APP FLOW ---
if 'step' not in st.session_state: st.session_state.step = "SELECT_ID"

# Status Bar
if "u_id" in st.session_state:
    u = driver_info[st.session_state.u_id]
    st.markdown(f'<div class="info-box">{u["name"]} | {u["car"]}</div>', unsafe_allow_html=True)

# STEP 1: SELECT ID
if st.session_state.step == "SELECT_ID":
    st.markdown("<h4 style='text-align:center'>SELECT DRIVER</h4>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, d_id in enumerate(driver_info.keys()):
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
                    # Logic: Auto-Fill Start Amount from Last Trip
                    last = get_last_wallet(d_id, all_vals)
                    st.session_state.auto_start = last
                    st.session_state.step = "START_TRIP"
                st.rerun()

# STEP 2: START TRIP (Fast Entry)
elif st.session_state.step == "START_TRIP":
    # Start ID Amount (Auto-filled)
    s_amt = st.number_input("START ID AMOUNT", value=float(st.session_state.auto_start))
    # Oil (Empty by default)
    oil = st.number_input("OIL (KM)", value=None, placeholder="0")

    if st.button("START SESSION 🚀"):
        oil_val = oil if oil else 0
        r = get_next_row(m_sheet)
        
        # Batch Update (Faster)
        row_data = [
            r-5, st.session_state.u_id, driver_info[st.session_state.u_id]['name'],
            driver_info[st.session_state.u_id]['car'], datetime.now().strftime("%m/%d/%Y"),
            s_amt, "", oil_val, datetime.now().strftime("%I:%M %p"), "", "", "", "", "", "Pending ⏳"
        ]
        # Range update is faster than cell by cell
        m_sheet.update(range_name=f"A{r}:O{r}", values=[row_data])
        
        st.success("Started!"); del st.session_state.step; st.rerun()

# STEP 3: END TRIP (Fast Entry)
elif st.session_state.step == "END_PROMPT":
    st.markdown(f"<div class='info-box'>TRIP ACTIVE</div>", unsafe_allow_html=True)
    if st.button("END SESSION"): st.session_state.step = "END_FORM"; st.rerun()

elif st.session_state.step == "END_FORM":
    # All inputs empty by default (value=None)
    e_amt = st.number_input("END ID AMOUNT", value=None, placeholder="Enter Amount")
    cash = st.number_input("CASH IN HAND", value=None, placeholder="Enter Amount")
    bank = st.number_input("BANK DEPOSIT", value=None, placeholder="Enter Amount")

    if st.button("SAVE & FINISH ✅"):
        # Handle empty inputs as 0
        e_val = e_amt if e_amt else 0.0
        c_val = cash if cash else 0.0
        b_val = bank if bank else 0.0
        
        start = float(st.session_state.p_trip['start'])
        id_cost = start - e_val
        total = c_val + b_val - id_cost
        
        r = st.session_state.p_trip['row']
        
        # Batch update for End Data (Columns G to O)
        # G(7), H(8-skip), I(9-skip), J(10), K(11), L(12), M(13), N(14), O(15)
        # Using update_cell is safer for disjointed cells, but we will do quick individual updates
        updates = [
            {'range': f'G{r}', 'values': [[e_val]]},
            {'range': f'J{r}', 'values': [[datetime.now().strftime("%I:%M %p")]]},
            {'range': f'K{r}', 'values': [[id_cost]]},
            {'range': f'L{r}', 'values': [[b_val]]},
            {'range': f'M{r}', 'values': [[c_val]]},
            {'range': f'N{r}', 'values': [[total]]},
            {'range': f'O{r}', 'values': [["Done ✔"]]}
        ]
        m_sheet.batch_update(updates)

        st.session_state.res = {"h": c_val, "b": b_val, "id": id_cost, "t": total}
        st.session_state.step = "RECEIPT"
        st.rerun()

elif st.session_state.step == "RECEIPT":
    res = st.session_state.res
    st.markdown(f"""
        <div class="receipt-card">
            <div style="text-align:center; border-bottom:1px dashed #00ff41; margin-bottom:10px;">RECEIPT</div>
            <div class="receipt-row"><span>Driver:</span><span>{driver_info[st.session_state.u_id]['name']}</span></div>
            <div class="receipt-row"><span>Hand:</span><span>{res['h']}</span></div>
            <div class="receipt-row"><span>Bank:</span><span>{res['b']}</span></div>
            <div class="receipt-row"><span>ID Cost:</span><span style="color:red">-{res['id']}</span></div>
            <div style="text-align:center; font-size:20px; font-weight:bold; margin-top:10px; background:#00ff41; color:black">TOTAL: {res['t']}</div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("NEW"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
