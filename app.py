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

        /* Dataframe styling */
        .stDataFrame {
            background: white;
            border-radius: 10px;
            padding: 10px;
            box-shadow: 0 0 8px rgba(0,0,0,0.08);
        }

        /* Search box */
        input[type="text"] {
            border-radius: 8px;
            border: 1px solid #ccc;
            padding: 0.5rem;
            width: 100%;
        }

        /* Success/Warning boxes */
        .stAlert {
            border-radius: 8px;
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

        if not filtered.empty:
            st.dataframe(filtered, use_container_width=True, hide_index=True)
        else:
            st.warning("No matching records found.")

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
