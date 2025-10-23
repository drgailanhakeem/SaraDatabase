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
            margin-bottom: 1rem;
        }

        .patient-card {
            background: white;
            border-radius: 14px;
            padding: 1.2rem;
            box-shadow: 0 3px 10px rgba(0,0,0,0.05);
            margin-bottom: 0.8rem;
            transition: all 0.2s ease;
            cursor: pointer;
        }

        .patient-card:hover {
            box-shadow: 0 5px 14px rgba(0,0,0,0.08);
            transform: scale(1.01);
        }

        .patient-section {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin-top: 1.2rem;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 0.8rem 2rem;
        }

        .label {
            font-weight: 600;
            color: #444;
            font-size: 0.92rem;
        }

        .value {
            color: #111;
            font-size: 0.95rem;
            margin-bottom: 0.4rem;
        }

        .back-btn {
            margin-top: 1.5rem;
        }

        /* Buttons */
        button[kind="secondary"] {
            background: #f2f4f8;
            color: #222;
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
    df = df[df["Full Name"].str.lower() != "full name"]  # remove header row duplication
    df = df[df["Full Name"].notna() & (df["Full Name"].str.strip() != "")]
    return df

# --- Main UI ---
st.markdown('<div class="main-title">🧠 Patient Profiles Viewer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Click on a patient to view their full record</div>', unsafe_allow_html=True)
st.markdown("---")

try:
    sheet = connect_to_google_sheet()
    patients_df = load_data(sheet)

    if patients_df.empty:
        st.warning("No patient records found in the Google Sheet.")
    else:
        st.success(f"✅ Loaded {len(patients_df)} patient records successfully.")

        # --- State ---
        if "selected_patient" not in st.session_state:
            st.session_state.selected_patient = None

        # --- Search bar ---
        search = st.text_input("🔍 Search by Name, Diagnosis, or Keyword")

        if search:
            filtered = patients_df[
                patients_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            ]
        else:
            filtered = patients_df

        # --- Show list or detail ---
        if st.session_state.selected_patient is None:
            if not filtered.empty:
                for i, patient in filtered.iterrows():
                    name = patient.get("Full Name", "Unnamed Patient")
                    if not isinstance(name, str) or name.strip() == "":
                        continue
                    with st.container():
                        st.markdown(
                            f"<div class='patient-card'><b>{name}</b></div>",
                            unsafe_allow_html=True
                        )
                        if st.button("View Details →", key=f"btn_{i}"):
                            st.session_state.selected_patient = i
                            st.rerun()
            else:
                st.warning("No matching records found.")
        else:
            # --- Detail View ---
            patient = patients_df.iloc[st.session_state.selected_patient]
            st.markdown(f"### 👤 {patient.get('Full Name', 'Unnamed Patient')}")
            st.markdown("#### Patient Details")

            st.markdown('<div class="patient-section">', unsafe_allow_html=True)
            st.markdown('<div class="info-grid">', unsafe_allow_html=True)
            for col in patients_df.columns:
                value = patient.get(col, "")
                if pd.isna(value) or value == "":
                    value = "—"
                st.markdown(f"""
                    <div>
                        <div class='label'>{col}</div>
                        <div class='value'>{value}</div>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

            if st.button("← Back to List", key="back", help="Return to patient list"):
                st.session_state.selected_patient = None
                st.rerun()

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
