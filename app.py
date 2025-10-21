import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid

# ===========================
# PAGE CONFIG
# ===========================
st.set_page_config(page_title="Sara Patient Database", page_icon="🩺", layout="wide")

# ===========================
# GOOGLE SHEET CONNECTION
# ===========================
try:
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(st.secrets["sheet"]["sheet_name"])
    visits_sheet_name = "Visits"
    try:
        visits_sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(visits_sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        visits_sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).add_worksheet(title=visits_sheet_name, rows="100", cols="10")
        visits_sheet.append_row(["Patient ID", "Visit Date", "Doctor's Name", "Notes"])

    data = sheet.get_all_records()
    visits_data = visits_sheet.get_all_records()

    df = pd.DataFrame(data)
    visits_df = pd.DataFrame(visits_data)

    st.success("✅ Successfully connected to Google Sheet")

except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheet: {e}")
    st.stop()

# ===========================
# UTILITY FUNCTIONS
# ===========================
def get_patient_by_id(patient_id):
    if "Patient ID" in df.columns:
        patient_row = df[df["Patient ID"] == patient_id]
        if not patient_row.empty:
            return patient_row.iloc[0].to_dict()
    return None

def add_patient_to_sheet(patient_data):
    sheet.append_row(list(patient_data.values()))

def add_visit_to_sheet(visit_data):
    visits_sheet.append_row(list(visit_data.values()))

# ===========================
# MAIN INTERFACE
# ===========================
query_params = st.query_params
patient_id = query_params.get("patient", [None])[0]

if not patient_id:
    st.title("🩺 Sara Patient Database")

    st.header("🔍 Search Patients")
    search_query = st.text_input("Search by Full Name")

    if not df.empty:
        filtered_patients = df[df["Full Name"].str.contains(search_query, case=False, na=False)] if search_query else df
        for _, row in filtered_patients.iterrows():
            patient_link = f"?patient={row['Patient ID']}" if "Patient ID" in row else "#"
            st.markdown(f"👤 [{row['Full Name']} (Age: {row.get('Age (in years)', 'N/A')})]({patient_link})")
    else:
        st.warning("No patients found in the database.")

    # Add New Patient (Expandable)
    with st.expander("➕ Add New Patient"):
        st.subheader("Add New Patient")
        patient_data = {}
        columns = sheet.row_values(1)

        for col in columns:
            if col == "Timestamp":
                patient_data[col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif col == "Patient ID":
                patient_data[col] = str(uuid.uuid4())[:8]
            elif col.lower() in ["sex", "smoking status", "alcohol use", "substance use", "marital status", "occupation"]:
                patient_data[col] = st.selectbox(col, ["", "Yes", "No", "Male", "Female", "Single", "Married"], index=0)
            elif "Date" in col:
                patient_data[col] = st.date_input(col).strftime("%Y-%m-%d")
            else:
                patient_data[col] = st.text_input(col)

        if st.button("💾 Save Patient"):
            add_patient_to_sheet(patient_data)
            st.success("✅ New patient added successfully!")
            st.rerun()

else:
    patient = get_patient_by_id(patient_id)
    if not patient:
        st.error("❌ Patient not found in database.")
        st.stop()

    st.title(f"👤 {patient['Full Name']}")
    st.markdown(f"**Age:** {patient.get('Age (in years)', 'N/A')}  |  **Sex:** {patient.get('Sex', 'N/A')}  |  **ID:** {patient_id}")

    # ===========================
    # PATIENT DATA DISPLAY (Grouped Cards)
    # ===========================
    st.divider()
    st.subheader("📋 General Information")
    cols = st.columns(2)
    with cols[0]:
        st.write(f"**Address:** {patient.get('Address', 'N/A')}")
        st.write(f"**Occupation:** {patient.get('Occupation', 'N/A')}")
        st.write(f"**Marital Status:** {patient.get('Marital Status', 'N/A')}")
    with cols[1]:
        st.write(f"**Date of Birth:** {patient.get('Date of Birth', 'N/A')}")
        st.write(f"**Doctor:** {patient.get(\"Doctor's Name\", 'N/A')}")
        st.write(f"**Submitter:** {patient.get('Submitter Name', 'N/A')}")

    st.subheader("🧠 Clinical Summary")
    st.write(f"**Chief Complaint:** {patient.get('Cheif Compliant', 'N/A')}")
    st.write(f"**Duration:** {patient.get('Duration of Compliant', 'N/A')}")
    st.write(f"**HPI:** {patient.get('HPI', 'N/A')}")
    st.write(f"**Past Medical Hx:** {patient.get('Past Medical Hx', 'N/A')}")
    st.write(f"**Family Hx:** {patient.get('Family Hx', 'N/A')}")
    st.write(f"**Working Diagnosis:** {patient.get('Working Diagnosis', 'N/A')}")
    st.write(f"**Final Diagnosis:** {patient.get('Final Diagnosis', 'N/A')}")

    st.subheader("💊 Medications & Advice")
    st.write(f"**Medications Prescribed:** {patient.get('Medications Prescribed', 'N/A')}")
    st.write(f"**Non-Pharmacologic Advice:** {patient.get('Non-Pharmacologic Advice', 'N/A')}")

    # ===========================
    # ADD NEW VISIT (Toggle)
    # ===========================
    with st.expander("🩹 Add New Visit"):
        visit_data = {}
        visit_data["Patient ID"] = patient_id
        visit_data["Visit Date"] = st.date_input("Visit Date", datetime.today()).strftime("%Y-%m-%d")
        visit_data["Doctor's Name"] = st.text_input("Doctor's Name", patient.get("Doctor's Name", ""))
        visit_data["Notes"] = st.text_area("Visit Notes")

        if st.button("💾 Save Visit"):
            add_visit_to_sheet(visit_data)
            st.success("✅ Visit added successfully!")
            st.rerun()

    # ===========================
    # DISPLAY VISITS
    # ===========================
    st.divider()
    st.subheader("📅 Patient Visits")
    patient_visits = visits_df[visits_df["Patient ID"] == patient_id] if "Patient ID" in visits_df else pd.DataFrame()
    if not patient_visits.empty:
        for _, visit in patient_visits.iterrows():
            with st.container(border=True):
                st.markdown(f"**🗓️ Date:** {visit['Visit Date']}")
                st.markdown(f"**👨‍⚕️ Doctor:** {visit.get(\"Doctor's Name\", 'N/A')}")
                st.markdown(f"**📝 Notes:** {visit.get('Notes', 'N/A')}")
    else:
        st.info("No visits found for this patient.")
