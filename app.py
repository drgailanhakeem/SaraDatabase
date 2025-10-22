import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Sara Database", layout="wide")

# === Google Sheets setup ===
SHEET_ID = "1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"
SHEET_NAME_RESPONSES = "Responses"
SHEET_NAME_VISITS = "Visits"
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# === Authenticate ===
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)
sheet_file = client.open_by_key(SHEET_ID)

# === Load sheets ===
@st.cache_data(ttl=60)
def load_sheet(sheet_name):
    sheet = sheet_file.worksheet(sheet_name)
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip()
    return df

try:
    responses_df = load_sheet(SHEET_NAME_RESPONSES)
    visits_df = load_sheet(SHEET_NAME_VISITS)
except Exception as e:
    st.error(f"❌ Failed to load sheets: {e}")
    st.stop()

# === Expected Columns (same for both) ===
expected_columns = [
    "Timestamp","Full Name","Date of Birth","Age (in years)","Sex","Address",
    "Date of Visit","Time of Visit","Doctor's Name","Cheif Compliant","Duration of Compliant",
    "Onset","HPI","Associated Symptoms","Relevant Negatives","Past Medical Hx","Past Surgical Hx",
    "Allergies","Current Medications","Family Hx","Smoking Status","Alcohol Use","Substance Use",
    "Occupation","Marital Status","General","CVS","Respiratory","GIT","GUT","Neurology","Psychiatry",
    "Vital Signs","Height","Weight","General Apperance","Physical Examination Findings","Lab Tests Ordered",
    "Lab Results","Imaging Studies","Working Diagnosis","Differential Diagnosis","Final Diagnosis",
    "Medications Prescribed","Non-Pharmacologic Advice","Referrals","Follow-Up Date",
    "Doctor's Notes / Impression","Visit Type","Submitter Name","Patient ID"
]

# === Check structure ===
for df_name, df in {"Responses": responses_df, "Visits": visits_df}.items():
    missing = [c for c in expected_columns if c not in df.columns]
    if missing:
        st.error(f"❌ {df_name} sheet missing columns: {missing}")
        st.stop()

# === App UI ===
st.title("🩺 Sara Patient Database")

menu = st.sidebar.radio("Menu", ["View Patients", "Add Patient", "Add Visit"])

# --- View Patients ---
if menu == "View Patients":
    st.subheader("Patient Records (Responses Sheet)")
    st.dataframe(responses_df)

# --- Add Patient ---
elif menu == "Add Patient":
    st.subheader("➕ Add Patient")

    with st.form("add_patient_form"):
        form_data = {col: st.text_input(col) for col in expected_columns}
        submitted = st.form_submit_button("Submit")

        if submitted:
            sheet = sheet_file.worksheet(SHEET_NAME_RESPONSES)
            sheet.append_row([form_data.get(c, "") for c in expected_columns])
            st.success("✅ Patient added successfully!")
            st.cache_data.clear()

# --- Add Visit ---
elif menu == "Add Visit":
    st.subheader("🩺 Add Visit")

    with st.form("add_visit_form"):
        form_data = {col: st.text_input(col) for col in expected_columns}
        submitted = st.form_submit_button("Submit")

        if submitted:
            sheet = sheet_file.worksheet(SHEET_NAME_VISITS)
            sheet.append_row([form_data.get(c, "") for c in expected_columns])
            st.success("✅ Visit added successfully!")
            st.cache_data.clear()
