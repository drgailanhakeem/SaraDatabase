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
        /* Background */
        [data-testid="stAppViewContainer"] {
            background-color: #f7f9fb;
        }
        [data-testid="stHeader"] {
            background: rgba(0,0,0,0);
        }

        /* Titles */
        .main-title {
            font-size: 2rem;
            font-weight: 700;
            color: #1f2937;
            padding-bottom: 0.3rem;
        }
        .sub-title {
            color: #6b7280;
            font-size: 1rem;
        }

        /* Card styling */
        .patient-card {
            background: white;
            border-radius: 16px;
            padding: 1.2rem 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: all 0.2s ease-in-out;
        }
        .patient-card:hover {
            box-shadow: 0 4px 14px rgba(0,0,0,0.08);
            transform: translateY(-2px);
        }
        .patient-name {
            font-weight: 600;
            font-size: 1.2rem;
            color: #111827;
        }
        .patient-meta {
            color: #4b5563;
            font-size: 0.9rem;
        }
        .metric {
            background: #f3f4f6;
            border-radius: 8px;
            padding: 0.4rem 0.6rem;
            margin-right: 0.4rem;
            display: inline-block;
            font-size: 0.85rem;
            color: #374151;
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

# --- Main Header ---
st.markdown('<div class="main-title">🧠 Patient Profiles</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Quick overview of all patient data from Google Sheets</div>', unsafe_allow_html=True)
st.markdown("---")

try:
    sheet = connect_to_google_sheet()
    patients_df = load_data(sheet)

    if patients_df.empty:
        st.warning("No patient records found in the Google Sheet.")
    else:
        st.success(f"✅ Loaded {len(patients_df)} patient records.")

        # --- Search ---
        search = st.text_input("🔍 Search by name, ID, or diagnosis")
        st.markdown("")

        if search:
            filtered = patients_df[
                patients_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            ]
        else:
            filtered = patients_df

        if filtered.empty:
            st.warning("No matching records found.")
        else:
            cols = st.columns(2)  # two cards per row
            for i, (_, row) in enumerate(filtered.iterrows()):
                with cols[i % 2]:
                    st.markdown(f"""
                        <div class="patient-card">
                            <div class="patient-name">{row.get('Patient Name', 'Unnamed')}</div>
                            <div class="patient-meta">📅 {row.get('Visit Date', 'N/A')} | 🧍 {row.get('Gender', 'N/A')}</div>
                            <div style="margin-top:0.8rem;">
                                <span class="metric">Age: {row.get('Age ( In Years )', 'N/A')}</span>
                                <span class="metric">Weight: {row.get('Weight', 'N/A')} kg</span>
                                <span class="metric">FBG: {row.get('Fasting Blood Glucose (FBG) before Pentat therapy ( mg/dL )', 'N/A')}</span>
                                <span class="metric">HbA1c: {row.get('HbA1c at the latest follow-up (%)', 'N/A')}</span>
                            </div>
                            <div style="margin-top:0.8rem;">
                                💊 <b>Treatment:</b> {', '.join([m for m in [row.get('Met',''), row.get('DPP-4',''), row.get('GLP-1',''), row.get('SGLT2','')] if m]) or 'None'}
                            </div>
                            <div style="margin-top:0.5rem; color:#6b7280;">
                                📋 <b>Diagnosis:</b> {row.get('Diagnosis', 'N/A')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
