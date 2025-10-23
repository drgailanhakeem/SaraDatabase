import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ===== GOOGLE SHEET CONFIGURATION =====
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID = "1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"
RANGE_NAME = "Form Responses 1"

# ===== AUTHENTICATION =====
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(RANGE_NAME)
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ===== STREAMLIT CONFIG =====
st.set_page_config(page_title="Sara Patient Database", layout="wide")
st.markdown("""
    <style>
        body { font-family: 'Inter', sans-serif; }
        .patient-card {
            padding: 0.8rem 1rem;
            border-radius: 12px;
            background-color: #f8fafc;
            margin-bottom: 0.5rem;
            border: 1px solid #e2e8f0;
            transition: all 0.2s ease-in-out;
        }
        .patient-card:hover {
            background-color: #f1f5f9;
            border-color: #94a3b8;
        }
        .patient-header {
            font-size: 1.5rem;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 1rem;
        }
        .back-btn {
            color: #2563eb;
            font-weight: 500;
            text-decoration: none;
        }
        .back-btn:hover {
            text-decoration: underline;
        }
        .info-card {
            background-color: #f8fafc;
            padding: 1rem;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            margin-bottom: 0.8rem;
        }
        .info-label {
            font-weight: 600;
            color: #475569;
        }
        .info-value {
            color: #0f172a;
        }
    </style>
""", unsafe_allow_html=True)

# ===== STATE MANAGEMENT =====
if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = None

# ===== FUNCTIONS =====
def go_back():
    st.session_state.selected_patient = None

# ===== UI =====
st.title("🩺 Sara Database")

# Remove the first row if it accidentally contains column headers
if df.iloc[0].equals(pd.Series(df.columns)):
    df = df.iloc[1:].reset_index(drop=True)

# ========== HOMEPAGE ==========
if st.session_state.selected_patient is None:
    st.subheader("Patient List")

    for _, row in df.iterrows():
        name = row.get("Full Name", "").strip()
        if not name:
            continue
        button_label = f"👤 {name}"
        if st.button(button_label, use_container_width=True, key=name):
            st.session_state.selected_patient = row
            st.rerun()

# ========== DETAIL PAGE ==========
else:
    patient = st.session_state.selected_patient

    # Back button with working logic
    if st.button("← Back to all patients", use_container_width=False):
        go_back()
        st.rerun()

    st.markdown(
        f"<div class='patient-header'>{patient.get('Full Name', 'N/A')}</div>",
        unsafe_allow_html=True,
    )

    # Two-column compact layout
    col1, col2 = st.columns(2)
    items = list(patient.items())
    half = (len(items) + 1) // 2

    with col1:
        for k, v in items[:half]:
            st.markdown(
                f"<div class='info-card'><div class='info-label'>{k}</div><div class='info-value'>{v if v else 'N/A'}</div></div>",
                unsafe_allow_html=True,
            )

    with col2:
        for k, v in items[half:]:
            st.markdown(
                f"<div class='info-card'><div class='info-label'>{k}</div><div class='info-value'>{v if v else 'N/A'}</div></div>",
                unsafe_allow_html=True,
            )
