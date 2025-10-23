import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- Page Config ---
st.set_page_config(
    page_title="Patient Profiles",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
            color: #222;
            padding-bottom: 0.3rem;
        }
        .sub-title {
            color: #666;
            font-size: 1rem;
        }
        .stDataFrame {
            background: white;
            border-radius: 10px;
            padding: 10px;
            box-shadow: 0 0 8px rgba(0,0,0,0.08);
        }
        input[type="text"] {
            border-radius: 8px;
            border: 1px solid #ccc;
            padding: 0.5rem;
            width: 100%;
        }
        .stAlert {
            border-radius: 8px;
        }
        .patient-card {
            background-color: white;
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .patient-header {
            font-size: 1.5rem;
            font-weight: 700;
            color: #111;
        }
        .patient-sub {
            font-size: 1rem;
            color: #555;
            margin-bottom: 1rem;
        }
        .field-label {
            font-weight: 600;
            color: #374151;
        }
        .field-value {
            color: #111;
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

# --- Load Data ---
@st.cache_data(ttl=300)
def get_data():
    sheet = connect_to_google_sheet()
    df = load_data(sheet)
    return df

# --- Main ---
if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = None

def show_main_view():
    st.markdown('<div class="main-title">🧠 Patient Profiles Viewer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Click on a patient to view full details</div>', unsafe_allow_html=True)
    st.markdown("---")

    try:
        patients_df = get_data()

        if patients_df.empty:
            st.warning("No patient records found in the Google Sheet.")
            return

        st.success(f"✅ Loaded {len(patients_df)} patient records successfully.")
        search = st.text_input("🔍 Search by Name, ID, or Diagnosis")

        if search:
            filtered = patients_df[
                patients_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            ]
        else:
            filtered = patients_df

        if not filtered.empty:
            for i, row in filtered.iterrows():
                name = row.get("Full Name", "Unknown")
                pid = row.get("Patient ID", "N/A")
                dx = row.get("Final Diagnosis", "N/A")

                if st.button(f"🧍 {name} — {dx}", key=f"patient_{i}"):
                    st.session_state.selected_patient = row.to_dict()
                    st.rerun()
        else:
            st.warning("No matching records found.")

    except Exception as e:
        st.error(f"❌ Error loading data: {e}")

def show_patient_profile(patient):
    st.markdown(f'<div class="main-title">{patient.get("Full Name", "Unnamed Patient")}</div>', unsafe_allow_html=True)
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Patient ID:** {patient.get('Patient ID', 'N/A')}")
        st.markdown(f"**Sex:** {patient.get('Sex', 'N/A')}")
        st.markdown(f"**Age:** {patient.get('Age (in years)', 'N/A')}")
        st.markdown(f"**Address:** {patient.get('Address', 'N/A')}")
        st.markdown(f"**Date of Visit:** {patient.get('Date of Visit', 'N/A')}")
        st.markdown(f"**Doctor's Name:** {patient.get(\"Doctor's Name\", 'N/A')}")
    with col2:
        st.markdown(f"**Chief Complaint:** {patient.get('Cheif Compliant', 'N/A')}")
        st.markdown(f"**Duration:** {patient.get('Duration of Compliant', 'N/A')}")
        st.markdown(f"**Working Diagnosis:** {patient.get('Working Diagnosis', 'N/A')}")
        st.markdown(f"**Final Diagnosis:** {patient.get('Final Diagnosis', 'N/A')}")
        st.markdown(f"**Medications Prescribed:** {patient.get('Medications Prescribed', 'N/A')}")

    st.markdown("### 🩺 Clinical Notes")
    st.markdown(f"{patient.get(\"Doctor's Notes / Impression\", 'N/A')}")

    st.markdown("### 🧾 Lab & Imaging")
    st.markdown(f"- **Lab Tests Ordered:** {patient.get('Lab Tests Ordered', 'N/A')}")
    st.markdown(f"- **Lab Results:** {patient.get('Lab Results', 'N/A')}")
    st.markdown(f"- **Imaging Studies:** {patient.get('Imaging Studies', 'N/A')}")

    st.markdown("### 💬 Other Info")
    st.markdown(f"- **Occupation:** {patient.get('Occupation', 'N/A')}")
    st.markdown(f"- **Marital Status:** {patient.get('Marital Status', 'N/A')}")
    st.markdown(f"- **Smoking Status:** {patient.get('Smoking Status', 'N/A')}")
    st.markdown(f"- **Alcohol Use:** {patient.get('Alcohol Use', 'N/A')}")

    st.markdown("---")
    if st.button("⬅️ Back to Patient List"):
        st.session_state.selected_patient = None
        st.rerun()

# --- Router ---
if st.session_state.selected_patient:
    show_patient_profile(st.session_state.selected_patient)
else:
    show_main_view()
