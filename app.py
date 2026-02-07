import streamlit as st
import pandas as pd
from datetime import datetime
import time
import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIG =================
SHEET_NAME = "Car_book"

# ================= GOOGLE SHEETS =================
def get_sheet(tab_name):
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).worksheet(tab_name)
    except Exception as e:
        st.error(f"Cloud Connection Failed: {e}")
        st.stop()

def get_next_available_row(sheet):
    col_b = sheet.col_values(2)
    return max(len(col_b) + 1, 6)

# ================= UI =================
st.set_page_config(page_title="Fleet Master Pro", layout="wide")
st.markdown("""
<style>
.stApp { background:#050505; color:#00ff41; font-family:Courier New; }
.stButton>button {
    border-radius:50%; width:90px; height:90px;
    background:transparent; color:#00ff41;
    border:2px solid #00ff41; font-size:18px;
}
input { background:#000; color:#00ff41; text-align:center; }
#MainMenu, footer, header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ================= DATA =================
driver_sheet = get_sheet("Driver Data")
df_drivers = pd.DataFrame(driver_sheet.get_all_records())
driver_info = {
    str(r["ID#"]): {"name": r["Driver Name"], "car": str(r["Car#"])}
    for _, r in df_drivers.iterrows()
}

st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)

if "step" not in st.session_state:
    st.session_state.step = "SELECT_ID"

# ================= STEP 1 =================
if st.session_state.step == "SELECT_ID":
    st.markdown("## > ACCESS_SYSTEM")
    cols = st.columns(2)
    for i, d_id in enumerate(driver_info):
        with cols[i % 2]:
            if st.button(d_id):
                st.session_state.u_id = d_id
                m_sheet = get_sheet("Management")
                rows = m_sheet.get_all_values()
                pending = None
                for idx, r in enumerate(rows[5:], start=6):
                    if len(r) > 14 and r[1] == d_id and "Pending" in r[14]:
                        pending = {"row": idx, "start": r[5], "name": r[2]}
                        break
                st.session_state.step = "END_PROMPT" if pending else "START_BAL"
                st.session_state.p_trip = pending
                st.rerun()

# ================= START =================
elif st.session_state.step == "START_BAL":
    st.markdown(driver_info[st.session_state.u_id]["name"])
    val = st.number_input("START_AMOUNT", min_value=0.0)
    if val:
        st.session_state.s_bal = val
        st.session_state.step = "START_OIL"
        st.rerun()

elif st.session_state.step == "START_OIL":
    val = st.number_input("OIL_KM", min_value=0)
    if val and st.button("INITIATE 🚀"):
        m_sheet = get_sheet("Management")
        r = get_next_available_row(m_sheet)
        m_sheet.insert_row([
            r-5,
            st.session_state.u_id,
            driver_info[st.session_state.u_id]["name"],
            driver_info[st.session_state.u_id]["car"],
            datetime.now().strftime("%m/%d/%Y"),
            st.session_state.s_bal,
            "",
            val,
            datetime.now().strftime("%I:%M %p"),
            "", "", "", "", "",
            "Pending ⏳"
        ], r)
        st.success("LOG SAVED")
        time.sleep(2)
        st.session_state.step = "SELECT_ID"
        st.rerun()

# ================= END =================
elif st.session_state.step == "END_PROMPT":
    st.markdown(f"### {st.session_state.p_trip['name']} ACTIVE")
    if st.button("TERMINATE 🏁"):
        st.session_state.step = "E1"
        st.rerun()

elif st.session_state.step == "E1":
    val = st.number_input("END_ID_AMOUNT", min_value=0.0)
    if val:
        st.session_state.ew = val
        st.session_state.step = "E2"
        st.rerun()

elif st.session_state.step == "E2":
    val = st.number_input("CASH_HAND", min_value=0.0)
    if val:
        st.session_state.eh = val
        st.session_state.step = "E3"
        st.rerun()

elif st.session_state.step == "E3":
    val = st.number_input("MY_ACCOUNT", min_value=0.0)
    if val and st.button("FINALIZE ✅"):
        start = float(st.session_state.p_trip["start"])
        amt_id = start - st.session_state.ew
        total = st.session_state.eh + val - amt_id
        m = get_sheet("Management")
        r = st.session_state.p_trip["row"]
        m.update(f"G{r}:O{r}", [[
            st.session_state.ew,
            datetime.now().strftime("%I:%M %p"),
            amt_id,
            val,
            st.session_state.eh,
            total,
            "Done ✔"
        ]])
        st.balloons()
        st.success(f"TOTAL: {total}")
        time.sleep(5)
        st.session_state.step = "SELECT_ID"
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
