import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- Google Sheets Setup ---
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(credentials)

# ✅ Use your actual sheet names
SHEET_PATIENTS = "Responses"
SHEET_VISITS = "Visits"

try:
    sheet_patients = client.open(SHEET_PATIENTS).sheet1
    sheet_visits = client.open(SHEET_VISITS).sheet1
except Exception as e:
    st.error(f"❌ Failed to load sheets: {e}")
    st.stop()

# --- Load Data ---
def load_data(sheet):
    records = sheet.get_all_records()
    return pd.DataFrame(records)

try:
    df_patients = load_data(sheet_patients)
    df_visits = load_data(sheet_visits)
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.stop()

st.success("✅ Connected successfully to Google Sheets!")

# Helper: Safe key generator
def safe_key(prefix, identifier):
    return f"{prefix}_{str(identifier).replace(' ', '_').replace('/', '_')}"

# Main Navigation
st.title("🩺 Sara Clinic Patient Management")

view = st.sidebar.radio("Navigation", ["All Patients", "Add New Patient"])

# -----------------------------------------------------------
# ADD NEW PATIENT
# -----------------------------------------------------------
if view == "Add New Patient":
    st.subheader("➕ Add New Patient")
    with st.form("add_patient_form"):
        name = st.text_input("Full Name")
        phone = st.text_input("Phone Number")
        age = st.number_input("Age", min_value=0, max_value=120)
        gender = st.selectbox("Gender", ["Male", "Female"])
        diagnosis = st.text_area("Diagnosis")
        submit = st.form_submit_button("Add Patient")

        if submit and name:
            new_patient = [name, phone, age, gender, diagnosis]
            sheet_patients.append_row(new_patient)
            st.success(f"✅ Patient {name} added successfully.")
            st.cache_data.clear()

# -----------------------------------------------------------
# ALL PATIENTS VIEW
# -----------------------------------------------------------
if view == "All Patients":
    st.subheader("📋 All Patients")
    search = st.text_input("Search by name or phone")
    filtered_patients = patients_df[
        patients_df["Full Name"].str.contains(search, case=False, na=False)
        | patients_df["Phone Number"].astype(str).str.contains(search, na=False)
    ] if search else patients_df

    for _, patient in filtered_patients.iterrows():
        with st.expander(f"{patient['Full Name']}"):
            st.write("### Patient Details")
            st.write(f"**Phone:** {patient['Phone Number']}")
            st.write(f"**Age:** {patient['Age']}")
            st.write(f"**Gender:** {patient['Gender']}")
            st.write(f"**Diagnosis:** {patient['Diagnosis']}")

            # Visit data for this patient
            patient_visits = visits_df[visits_df["Full Name"] == patient["Full Name"]]
            if not patient_visits.empty:
                st.write("### 🗂️ Visits")
                # Sort visits by date
                patient_visits["Visit Date"] = pd.to_datetime(patient_visits["Visit Date"], errors="coerce")
                patient_visits = patient_visits.sort_values("Visit Date", ascending=False)

                for _, visit in patient_visits.iterrows():
                    with st.expander(f"📅 Visit on {visit['Visit Date'].date()}"):
                        for col, val in visit.items():
                            st.write(f"**{col}:** {val}")

            # Add visit
            st.markdown("---")
            st.write("### ➕ Add Visit")
            with st.form(safe_key("visit_form", patient["Full Name"])):
                visit_date = st.date_input("Visit Date", datetime.today())
                notes = st.text_area("Notes")
                submit_visit = st.form_submit_button("Add Visit")

                if submit_visit:
                    new_visit = {
                        "Full Name": patient["Full Name"],
                        "Visit Date": str(visit_date),
                        "Notes": notes,
                    }
                    sheet_visits.append_row(list(new_visit.values()))
                    st.success("✅ Visit added successfully.")
                    st.cache_data.clear()

            # Delete patient
            delete_key = safe_key("delete", patient["Full Name"])
            if st.button("🗑️ Delete Patient", key=delete_key):
                sheet_patients.delete_rows(_ + 2)  # +2 accounts for header and 0-index
                st.warning(f"Deleted {patient['Full Name']}")
                st.cache_data.clear()
                st.rerun()
