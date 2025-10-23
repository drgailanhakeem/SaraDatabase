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

        .patient-card {
            background: white;
            border-radius: 14px;
            padding: 1.5rem;
            box-shadow: 0 3px 10px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
        }

        .patient-section {
            background: white;
            border-radius: 12px;
            padding: 1.2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            margin-top: 1.2rem;
        }

        .label {
            font-weight: 600;
            color: #444;
        }

        .value {
            color: #222;
            margin-bottom: 0.4rem;
        }

        a {
            text-decoration: none;
            color: #0078ff;
            font-weight: 600;
        }
        a:hover {
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

        # --- Navigation state ---
        if "selected_patient" not in st.session_state:
            st.session_state.selected_patient = None

        if st.session_state.selected_patient is None:
            # --- List view ---
            if not filtered.empty:
                for i, patient in filtered.iterrows():
                    name = patient.get("Full Name", "Unnamed Patient")
                    patient_id = patient.get("Patient ID", "N/A")

                    with st.container():
                        st.markdown(f"""
                        <div class="patient-card">
                            <div style="font-size:1.2rem; font-weight:600;">{name}</div>
                            <div style="color:#555;">🆔 {patient_id}</div>
                            <div style="margin-top:0.6rem;">
                                <a href="?patient={i}">View Details →</a>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("No matching records found.")
        else:
            # --- Detail view ---
            idx = st.session_state.selected_patient
            if 0 <= idx < len(patients_df):
                patient = patients_df.iloc[idx]

                st.markdown(f"### 👤 {patient.get('Full Name', 'Unnamed Patient')}")
                st.markdown("#### Patient Details")

                with st.container():
                    st.markdown('<div class="patient-section">', unsafe_allow_html=True)
                    for col in patients_df.columns:
                        value = patient.get(col, "")
                        if pd.isna(value) or value == "":
                            value = "—"
                        st.markdown(f"<div class='label'>{col}</div><div class='value'>{value}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                if st.button("← Back to List"):
                    st.session_state.selected_patient = None
            else:
                st.warning("Patient not found.")

        # --- Handle link clicks ---
        query_params = st.query_params
        if "patient" in query_params:
            try:
                st.session_state.selected_patient = int(query_params["patient"])
                st.experimental_rerun()
            except:
                st.session_state.selected_patient = None

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
