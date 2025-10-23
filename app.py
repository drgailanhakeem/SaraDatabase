import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- Page Config ---
st.set_page_config(
    page_title="Patient Profiles",
    page_icon="🧠",
    layout="wide",
)

# --- Custom CSS ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background-color: #f8f9fb;
    }
    [data-testid="stHeader"] {
        background: rgba(0,0,0,0);
    }
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #555;
        font-size: 1rem;
        margin-bottom: 1rem;
    }
    .patient-card {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        margin-bottom: 0.8rem;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 1px solid transparent;
    }
    .patient-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-color: #e6e6e6;
        transform: translateY(-2px);
    }
    .patient-name {
        font-size: 1.1rem;
        font-weight: 600;
        color: #222;
        margin: 0;
    }
    .patient-section {
        background: white;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-top: 1.2rem;
    }
    .info-card {
        background: #fdfdfd;
        border: 1px solid #eee;
        border-radius: 10px;
        padding: 1rem;
        transition: all 0.2s ease;
    }
    .info-card:hover {
        background: #f9f9f9;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .info-label {
        font-size: 0.9rem;
        font-weight: 600;
        color: #444;
        margin-bottom: 0.2rem;
    }
    .info-value {
        font-size: 0.95rem;
        color: #000;
        margin-bottom: 0.4rem;
    }
    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 1rem 1.5rem;
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
    df = df[df["Full Name"].str.lower() != "full name"]  # remove header duplication
    df = df[df["Full Name"].notna() & (df["Full Name"].str.strip() != "")]
    return df

# --- Header ---
st.markdown('<div class="main-title">🧠 Patient Profiles Viewer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Click a patient name to view their record</div>', unsafe_allow_html=True)
st.markdown("---")

try:
    sheet = connect_to_google_sheet()
    patients_df = load_data(sheet)

    if patients_df.empty:
        st.warning("No patient records found.")
    else:
        # --- State ---
        if "selected_patient" not in st.session_state:
            st.session_state.selected_patient = None

        # --- Search bar ---
        search = st.text_input("🔍 Search by name or keyword")

        if search:
            filtered = patients_df[
                patients_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            ]
        else:
            filtered = patients_df

        # --- Homepage List ---
        if st.session_state.selected_patient is None:
            if filtered.empty:
                st.warning("No matching results.")
            else:
                for i, patient in filtered.iterrows():
                    name = patient.get("Full Name", "Unnamed Patient")
                    if not isinstance(name, str) or name.strip() == "":
                        continue
                    card_html = f"""
                    <div class="patient-card" id="card_{i}" onclick="window.location.href='?patient={i}'">
                        <p class="patient-name">{name}</p>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                # Capture query param for navigation
                query_params = st.query_params
                if "patient" in query_params:
                    try:
                        st.session_state.selected_patient = int(query_params["patient"])
                        st.rerun()
                    except:
                        pass

        # --- Patient Detail Page ---
        else:
            patient = patients_df.iloc[st.session_state.selected_patient]
            st.markdown(f"## 👤 {patient.get('Full Name', 'Unnamed Patient')}")

            st.markdown('<div class="patient-section">', unsafe_allow_html=True)
            st.markdown('<div class="info-grid">', unsafe_allow_html=True)
            for col in patients_df.columns:
                value = patient.get(col, "")
                if pd.isna(value) or str(value).strip() == "":
                    value = "—"
                st.markdown(f"""
                    <div class="info-card">
                        <div class="info-label">{col}</div>
                        <div class="info-value">{value}</div>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            if st.button("← Back to List", key="back"):
                st.session_state.selected_patient = None
                st.query_params.clear()
                st.rerun()

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
