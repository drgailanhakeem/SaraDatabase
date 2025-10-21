import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --------------------------
#  GOOGLE SHEET CONNECTION
# --------------------------
st.set_page_config(page_title="Sara Patient Database", layout="wide")

scope = ["https://www.googleapis.com/auth/spreadsheets"]
try:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(
        st.secrets["sheet"]["sheet_name"]
    )
    st.success("✅ Successfully connected to Google Sheet")
except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheet: {e}")
    st.stop()

# Load main patient data
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Create Visits sheet if not exist
try:
    visits_sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet("Visits")
except:
    ws = client.open_by_key(st.secrets["sheet"]["sheet_id"])
    ws.add_worksheet(title="Visits", rows=1000, cols=50)
    visits_sheet = ws.worksheet("Visits")

# --------------------------
#  PAGE NAVIGATION
# --------------------------
query_params = st.query_params
patient_id = query_params.get("id", [None])[0] if isinstance(query_params.get("id"), list) else query_params.get("id")

# --------------------------
#  HOMEPAGE (PATIENT LIST)
# --------------------------
if not patient_id:
    st.title("🩺 Sara Patient Database")

    search = st.text_input("🔍 Search by Full Name")
    if search:
        filtered = df[df["Full Name"].str.contains(search, case=False, na=False)]
    else:
        filtered = df

    if not filtered.empty:
        for _, row in filtered.iterrows():
            patient_uid = str(row["Timestamp"])
            patient_name = row["Full Name"]
            age = row.get("Age (in years)", "N/A")

            st.markdown(
                f"👤 [{patient_name} (Age: {age})](?id={patient_uid})"
            )
    else:
        st.warning("No patients found.")

    st.markdown("### ➕ Add New Patient")
    with st.form("add_patient"):
        cols = st.columns(2)
        with cols[0]:
            full_name = st.text_input("Full Name")
            dob = st.date_input("Date of Birth")
            sex = st.selectbox("Sex", ["Male", "Female"])
            address = st.text_input("Address")
        with cols[1]:
            age = st.number_input("Age (in years)", min_value=0, max_value=120)
            doctor = st.text_input("Doctor's Name")
            submitter = st.text_input("Submitter Name")

        submit_btn = st.form_submit_button("Add Patient")
        if submit_btn:
            new_row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                full_name,
                dob.strftime("%Y-%m-%d"),
                age,
                sex,
                address,
                "",
                "",
                doctor,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                submitter,
            ]
            sheet.append_row(new_row)
            st.success("✅ Patient added successfully! Please refresh the page.")
# --------------------------
#  PATIENT PROFILE PAGE
# --------------------------
else:
    st.title("🩺 Patient Profile")

    patient = df[df["Timestamp"].astype(str) == str(patient_id)]
    if patient.empty:
        st.error("❌ Patient not found in database.")
        st.stop()

    patient = patient.iloc[0]

    # --- General Info ---
    st.subheader("📋 General Information")
    cols = st.columns(2)
    with cols[0]:
        st.write(f"**Full Name:** {patient.get('Full Name', 'N/A')}")
        st.write(f"**Date of Birth:** {patient.get('Date of Birth', 'N/A')}")
        st.write(f"**Age:** {patient.get('Age (in years)', 'N/A')}")
        st.write(f"**Sex:** {patient.get('Sex', 'N/A')}")
    with cols[1]:
        st.write(f"**Address:** {patient.get('Address', 'N/A')}")
        st.write(f"**Occupation:** {patient.get('Occupation', 'N/A')}")
        st.write(f"**Marital Status:** {patient.get('Marital Status', 'N/A')}")
        st.write(f'**Doctor:** {patient.get("Doctor\'s Name", "N/A")}')
        st.write(f"**Submitter:** {patient.get('Submitter Name', 'N/A')}")

    # --- Clinical Information ---
    st.subheader("🧠 Clinical Information")
    st.write(f"**Chief Complaint:** {patient.get('Cheif Compliant', 'N/A')}")
    st.write(f"**Duration of Complaint:** {patient.get('Duration of Compliant', 'N/A')}")
    st.write(f"**Onset:** {patient.get('Onset', 'N/A')}")
    st.write(f"**HPI:** {patient.get('HPI', 'N/A')}")
    st.write(f"**Past Medical History:** {patient.get('Past Medical Hx', 'N/A')}")
    st.write(f"**Past Surgical History:** {patient.get('Past Surgical Hx', 'N/A')}")
    st.write(f"**Family History:** {patient.get('Family Hx', 'N/A')}")
    st.write(f"**Allergies:** {patient.get('Allergies', 'N/A')}")
    st.write(f"**Current Medications:** {patient.get('Current Medications', 'N/A')}")

    # --- Visit Information ---
    st.subheader("📅 Visit Summary")
    patient_visits = pd.DataFrame(visits_sheet.get_all_records())
    patient_visits = patient_visits[patient_visits["Patient ID"] == patient_id] if not patient_visits.empty else pd.DataFrame()

    if not patient_visits.empty:
        for _, visit in patient_visits.iterrows():
            st.markdown("---")
            st.write(f"**Visit Date:** {visit.get('Date of Visit', 'N/A')}")
            st.write(f"**Doctor:** {visit.get('Doctor', 'N/A')}")
            st.write(f"**Notes:** {visit.get('Doctor Notes', 'N/A')}")
    else:
        st.info("No previous visits recorded.")

    # --- Add Visit ---
    with st.expander("➕ Add New Visit", expanded=False):
        with st.form("add_visit"):
            date_visit = st.date_input("Date of Visit", datetime.today())
            doctor_name = st.text_input("Doctor")
            notes = st.text_area("Doctor Notes / Impression")
            submit_visit = st.form_submit_button("Save Visit")

            if submit_visit:
                new_visit = [patient_id, str(date_visit), doctor_name, notes]
                visits_sheet.append_row(new_visit)
                st.success("✅ Visit saved successfully!")
