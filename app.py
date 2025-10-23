import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- Page Config ---
st.set_page_config(page_title="Patient Profiles", page_icon="🧠", layout="wide")

# --- Custom CSS ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: #f8f9fb;
    }
    [data-testid="stHeader"] {
        background: rgba(0,0,0,0);
    }

    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.3rem;
    }
    .sub-title {
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 1.2rem;
    }

    /* Patient detail grid */
    .patient-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 14px;
    }

    .info-card {
        background: white;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }

    .field-label {
        font-weight: 600;
        color: #334155;
        font-size: 0.9rem;
    }

    .field-value {
        color: #475569;
        font-size: 0.9rem;
    }

    .back-button {
        color: #2563eb;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.95rem;
    }
    .back-button:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

# --- Google Sheets setup ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/"
SHEET_NAME = "Responses"

def connect_to_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    client = gspread.authorize(credentials)
    return client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)

def load_data(sheet):
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df.columns = [c.strip() for c in df.columns]
    return df

# --- Load data ---
sheet = connect_to_google_sheet()
patients_df = load_data(sheet)

if patients_df.empty:
    st.warning("No patient records found in the Google Sheet.")
    st.stop()

# --- Page logic ---
if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = None

# --- Homepage ---
if st.session_state.selected_patient is None:
    st.markdown('<div class="main-title">🧠 Patient Profiles</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Click a patient to view their full record.</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Remove the first row if it's a header misread
    if patients_df.iloc[0]["Full Name"] == "Full Name":
        patients_df = patients_df.iloc[1:]

    # Clean names
    patients_df["Full Name"] = patients_df["Full Name"].fillna("Unnamed")

    # Show list of patients
    for i, row in patients_df.iterrows():
        name = row["Full Name"]
        if st.button(name, use_container_width=True):
            st.session_state.selected_patient = i
            st.rerun()

# --- Detail Page ---
else:
    patient = patients_df.iloc[st.session_state.selected_patient]

    st.markdown(f"<a class='back-button' href='#' onclick='window.location.reload()'>← Back to all patients</a>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='margin-top:0.5rem;color:#1e293b;'>{patient.get('Full Name','Unnamed')}</h2>")
    st.markdown("<hr>", unsafe_allow_html=True)

    # --- Display fields in grid layout ---
    st.markdown('<div class="patient-grid">', unsafe_allow_html=True)

    for col in patients_df.columns:
        value = str(patient.get(col, "")).strip()
        if value == "":
            value = "—"
        card_html = f"""
        <div class="info-card">
            <div class="field-label">{col}</div>
            <div class="field-value">{value}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
