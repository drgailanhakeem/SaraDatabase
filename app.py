import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# ============================
# 🔧 CONFIGURATION
# ============================
SHEET_NAME = "SaraDatabase"  # name of your spreadsheet
PATIENT_SHEET = "Responses"
VISIT_SHEET = "Visits"

st.set_page_config(page_title="Sara Patient Database", layout="wide")

# ============================
# 🧠 CONNECT TO GOOGLE SHEETS
# ============================
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(credentials)
    spreadsheet = client.open(SHEET_NAME)
    sheet_patients = spreadsheet.worksheet(PATIENT_SHEET)
    sheet_visits = spreadsheet.worksheet(VISIT_SHEET)
except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheets: {e}")
    st.stop()

# ============================
# 📄 LOAD DATA
# ============================
try:
    patients_df = pd.DataFrame(sheet_patients.get_all_records())
    visits_df = pd.DataFrame(sheet_visits.get_all_records())

    # 🧹 Clean and validate headers
    patients_df.columns = patients_df.columns.str.strip()
    visits_df.columns = visits_df.columns.str.strip()
    patients_df = patients_df.loc[:, patients_df.columns.notna()]
    visits_df = visits_df.loc[:, visits_df.columns.notna()]
    visits_df = visits_df.loc[:, visits_df.columns != '']

    # ✅ Ensure required column exists
    if "Patient ID" not in patients_df.columns or "Patient ID" not in visits_df.columns:
        st.error(
            f"⚠️ 'Patient ID' column missing.\n\n"
            f"Patients columns: {list(patients_df.columns)}\n"
            f"Visits columns: {list(visits_df.columns)}"
        )
        st.stop()

    if visits_df.empty:
        st.warning("⚠️ The 'Visits' sheet is empty.")
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.stop()

# ============================
# 🧭 SIDEBAR & TOGGLE
# ============================
st.sidebar.title("🏥 Sara Patient Database")
search = st.sidebar.text_input("🔍 Search Patient by Name or ID")

# Toggle for Add New Patient
if "show_form" not in st.session_state:
    st.session_state.show_form = False

if st.sidebar.button("➕ Add New Patient"):
    st.session_state.show_form = not st.session_state.show_form

# ============================
# 📋 DISPLAY PATIENTS
# ============================
if not patients_df.empty:
    filtered_df = patients_df.copy()

    if search:
        filtered_df = filtered_df[
            filtered_df["Full Name"].str.contains(search, case=False, na=False)
            | filtered_df["Patient ID"].astype(str).str.contains(search, case=False, na=False)
        ]

    for _, row in filtered_df.iterrows():
        with st.expander(f"👤 {row.get('Full Name', 'Unknown')} ({row.get('Patient ID', 'N/A')})", expanded=False):
            st.write("### 🧾 Patient Information")
            st.write(row.to_frame().T)

            # Show visits for this patient
            patient_visits = visits_df[visits_df["Patient ID"] == row.get("Patient ID")]
            if not patient_visits.empty:
                st.write("### 📅 Visits")
                st.dataframe(patient_visits)
            else:
                st.info("No visits found for this patient.")

else:
    st.info("No patients found in the database.")

# ============================
# 🧍 ADD NEW PATIENT FORM
# ============================
if st.session_state.show_form:
    st.subheader("➕ Add New Patient")
    with st.form("add_patient_form"):
        full_name = st.text_input("Full Name")
        age = st.number_input("Age (in years)", min_value=0, max_value=120, step=1)
        sex = st.selectbox("Sex", ["Male", "Female", "Other"])
        patient_id = st.text_input("Patient ID")

        submitted = st.form_submit_button("✅ Submit")
        if submitted:
            new_patient = {
                "Full Name": full_name,
                "Age (in years)": age,
                "Sex": sex,
                "Patient ID": patient_id
            }

            try:
                sheet_patients.append_row(list(new_patient.values()))
                st.success("✅ New patient added successfully!")
            except Exception as e:
                st.error(f"❌ Failed to add new patient: {e}")
