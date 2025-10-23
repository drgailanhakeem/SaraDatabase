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

# --- Custom CSS for Modern Design ---
st.markdown("""
    <style>
        /* General app background */
        [data-testid="stAppViewContainer"] {
            background: #f8f9fb;
        }
        [data-testid="stHeader"] {
            background: rgba(0,0,0,0);
        }

        /* Titles */
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

        /* Profile Card */
        .profile-card {
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .profile-card h3 {
            margin: 0;
            color: #0078ff;
        }
        .profile-detail {
            margin-top: 0.5rem;
            color: #333;
        }

        /* Buttons */
        div.stButton > button {
            background-color: #0078ff;
            color: white;
            border-radius: 8px;
            padding: 0.4rem 1rem;
            border: none;
        }
        div.stButton > button:hover {
            background-color: #005fcc;
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

# --- Main UI ---
st.markdown('<div class="main-title">🧠 Patient Profiles Viewer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">View and search all patient data from Google Sheets in one place</div>', unsafe_allow_html=True)
st.markdown("---")

try:
    sheet = connect_to_google_sheet()
    patients_df = load_data(sheet)

    if patients_df.empty:
        st.warning("No patient records found in the Google Sheet.")
    else:
        st.success(f"✅ Loaded {len(patients_df)} patient records successfully.")
        
        # --- Search bar ---
        search = st.text_input("🔍 Search by Name, ID, or Diagnosis")
        st.markdown("")

        # --- Filter results ---
        if search:
            filtered = patients_df[
                patients_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            ]
        else:
            filtered = patients_df

        # --- Session state for selected patient ---
        if "selected_patient" not in st.session_state:
            st.session_state.selected_patient = None

        # --- If a patient is selected, show profile ---
        if st.session_state.selected_patient is not None:
            patient = st.session_state.selected_patient
            st.markdown("### 👤 Patient Profile")
            st.markdown("---")
            st.markdown(f"""
                <div class="profile-card">
                    <h3>{patient.get('Full Name', 'N/A')}</h3>
                    <div class="profile-detail"><strong>Age:</strong> {patient.get('Age (in years)', 'N/A')}</div>
                    <div class="profile-detail"><strong>Sex:</strong> {patient.get('Sex', 'N/A')}</div>
                    <div class="profile-detail"><strong>Date of Birth:</strong> {patient.get('Date of Birth', 'N/A')}</div>
                    <div class="profile-detail"><strong>Address:</strong> {patient.get('Address', 'N/A')}</div>
                    <div class="profile-detail"><strong>Date of Visit:</strong> {patient.get('Date of Visit', 'N/A')}</div>
                    <div class="profile-detail"><strong>Chief Complaint:</strong> {patient.get('Cheif Compliant', 'N/A')}</div>
                    <div class="profile-detail"><strong>Duration of Complaint:</strong> {patient.get('Duration of Compliant', 'N/A')}</div>
                    <div class="profile-detail"><strong>HPI:</strong> {patient.get('HPI', 'N/A')}</div>
                    <div class="profile-detail"><strong>Past Medical Hx:</strong> {patient.get('Past Medical Hx', 'N/A')}</div>
                    <div class="profile-detail"><strong>Family Hx:</strong> {patient.get('Family Hx', 'N/A')}</div>
                    <div class="profile-detail"><strong>Working Diagnosis:</strong> {patient.get('Working Diagnosis', 'N/A')}</div>
                    <div class="profile-detail"><strong>Final Diagnosis:</strong> {patient.get('Final Diagnosis', 'N/A')}</div>
                    <div class="profile-detail"><strong>Medications:</strong> {patient.get('Medications Prescribed', 'N/A')}</div>
                    <div class="profile-detail"><strong>Doctor's Notes:</strong> {patient.get("Doctor's Notes / Impression", 'N/A')}</div>
                </div>
            """, unsafe_allow_html=True)

            if st.button("⬅️ Back to All Patients"):
                st.session_state.selected_patient = None
                st.rerun()

        else:
            # --- Show patient list with clickable names ---
            st.markdown("### 👥 All Patients")
            st.markdown("---")

            if not filtered.empty:
                for _, row in filtered.iterrows():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button(row["Full Name"]):
                            st.session_state.selected_patient = row.to_dict()
                            st.rerun()
                    with col2:
                        st.markdown(f"**Age:** {row.get('Age (in years)', 'N/A')}  |  **Sex:** {row.get('Sex', 'N/A')}")
            else:
                st.warning("No matching records found.")

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
