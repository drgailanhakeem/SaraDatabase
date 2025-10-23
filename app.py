import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

# ---- CONFIG ----
st.set_page_config(page_title="Patient Database", layout="wide")
st.markdown("""
    <style>
        .patient-card {
            background-color: #ffffff;
            border-radius: 20px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 3px 12px rgba(0,0,0,0.08);
            transition: all 0.2s ease;
        }
        .patient-card:hover {
            box-shadow: 0 6px 20px rgba(0,0,0,0.12);
            transform: translateY(-3px);
        }
        .patient-header {
            font-size: 1.25rem;
            font-weight: 600;
            color: #111827;
            margin-bottom: 0.25rem;
        }
        .patient-sub {
            font-size: 0.95rem;
            color: #6b7280;
        }
        .metric {
            font-size: 0.9rem;
            color: #374151;
            margin-right: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# ---- GOOGLE SHEETS CONNECTION ----
try:
    # Load credentials
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)

    # Load spreadsheet
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"
    spreadsheet = client.open_by_url(SHEET_URL)
    worksheet = spreadsheet.sheet1
    data = worksheet.get_all_records()

    df = pd.DataFrame(data)

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.stop()

# ---- CLEAN COLUMN NAMES ----
df.columns = [col.strip() for col in df.columns]

# ---- SIDEBAR FILTER ----
st.sidebar.title("Filters")
doctor_filter = st.sidebar.text_input("Filter by Doctor's Name")
search_name = st.sidebar.text_input("Search by Patient Name")

filtered_df = df.copy()
if doctor_filter:
    filtered_df = filtered_df[filtered_df["Doctor's Name"].str.contains(doctor_filter, case=False, na=False)]
if search_name:
    filtered_df = filtered_df[filtered_df["Full Name"].str.contains(search_name, case=False, na=False)]

st.title("🩺 Patient Profiles")
st.caption("Clean and modern profile cards with key patient data")

if filtered_df.empty:
    st.info("No matching patients found.")
else:
    for _, row in filtered_df.iterrows():
        full_name = row.get("Full Name", "N/A")
        pid = row.get("Patient ID", "N/A")
        age = row.get("Age (in years)", "N/A")
        sex = row.get("Sex", "N/A")
        weight = row.get("Weight", "N/A")
        fbg = row.get("Lab Results", "N/A")  # adjust if FBG is stored separately
        hba1c = row.get("Lab Results", "N/A")  # same column
        meds = row.get("Medications Prescribed", "None")
        working_dx = row.get("Working Diagnosis", "N/A")
        final_dx = row.get("Final Diagnosis", "N/A")
        notes = row.get("Doctor's Notes / Impression", "")

        st.markdown(f"""
        <div class="patient-card">
            <div class="patient-header">{full_name}</div>
            <div class="patient-sub">ID: {pid} • {sex} • Age: {age}</div>

            <div style="margin-top:0.8rem;">
                <span class="metric">⚖️ Weight: {weight}</span>
                <span class="metric">🧪 FBG: {fbg}</span>
                <span class="metric">🩸 HbA1c: {hba1c}</span>
            </div>

            <div style="margin-top:0.8rem;">
                💊 <b>Medications:</b> {meds}
            </div>

            <div style="margin-top:0.6rem;color:#6b7280;">
                📋 <b>Working Dx:</b> {working_dx}
            </div>
            <div style="margin-top:0.25rem;color:#6b7280;">
                📌 <b>Final Dx:</b> {final_dx}
            </div>

            <div style="margin-top:0.6rem;color:#475569;font-size:0.95rem;">
                {notes}
            </div>
        </div>
        """, unsafe_allow_html=True)
