import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time

# ===============================
# Google Sheets Setup
# ===============================
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPE
    )
    client = gspread.authorize(creds)

    sheet_responses = client.open("SaraDatabase").worksheet("Responses")
    sheet_visits = client.open("Sara Patient Database").worksheet("Visits")

except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheets: {e}")
    st.stop()

# ===============================
# Load Data
# ===============================
def load_data():
    try:
        patients = sheet_responses.get_all_records()
        visits = sheet_visits.get_all_records()
        df_patients = pd.DataFrame(patients)
        df_visits = pd.DataFrame(visits)
        return df_patients, df_visits
    except Exception as e:
        st.error(f"❌ Failed to load sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

patients_df, visits_df = load_data()

if patients_df.empty:
    st.warning("⚠️ The 'Responses' sheet is empty.")
if visits_df.empty:
    st.warning("⚠️ The 'Visits' sheet is empty.")

# ===============================
# App UI
# ===============================
st.title("🏥 Sara Patient Database")

# --- Toggleable Add New Patient Form ---
with st.expander("➕ Add New Patient", expanded=False):
    with st.form("add_patient_form"):
        full_name = st.text_input("Full Name")
        dob = st.date_input("Date of Birth", min_value=date(1900, 1, 1), max_value=date.today())
        sex = st.selectbox("Sex", ["Male", "Female", "Other"])
        address = st.text_input("Address")
        date_of_visit = st.date_input("Date of Visit", date.today())
        time_of_visit = st.time_input("Time of Visit", datetime.now().time())
        doctor_name = st.text_input("Doctor's Name")
        chief_complaint = st.text_area("Chief Complaint")
        duration_complaint = st.text_input("Duration of Complaint")
        submitter_name = st.text_input("Submitter Name")

        submitted = st.form_submit_button("✅ Add Patient")
        if submitted:
            try:
                new_patient = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Full Name": full_name,
                    "Date of Birth": dob.strftime("%Y-%m-%d"),
                    "Sex": sex,
                    "Address": address,
                    "Date of Visit": date_of_visit.strftime("%Y-%m-%d"),
                    "Time of Visit": time_of_visit.strftime("%H:%M:%S"),
                    "Doctor's Name": doctor_name,
                    "Cheif Compliant": chief_complaint,
                    "Duration of Compliant": duration_complaint,
                    "Submitter Name": submitter_name,
                    "Patient ID": f"PT{len(patients_df) + 1:04d}"
                }
                sheet_responses.append_row(list(new_patient.values()))
                st.success("✅ Patient added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding patient: {e}")

# ===============================
# Display Patient List
# ===============================
st.subheader("🩺 Patient List")

search = st.text_input("🔍 Search Patient by Name or ID")

if not patients_df.empty:
    if search:
        patients_df = patients_df[
            patients_df["Full Name"].str.contains(search, case=False, na=False)
            | patients_df["Patient ID"].astype(str).str.contains(search, na=False)
        ]

    for _, row in patients_df.iterrows():
        with st.expander(f"👤 {row.get('Full Name', 'Unknown')} ({row.get('Patient ID', 'N/A')})", expanded=False):
            st.markdown("### 🧾 Patient Information")
            for col, val in row.items():
                st.write(f"**{col}:** {val if val else 'N/A'}")

            st.markdown("### 🩺 Visits")

            patient_visits = visits_df[visits_df["Patient ID"] == row.get("Patient ID")]
            if not patient_visits.empty:
                for _, visit in patient_visits.sort_values("Date of Visit", ascending=False).iterrows():
                    with st.expander(f"📅 {visit.get('Date of Visit', 'Unknown')} — {visit.get('Visit Type', 'N/A')}", expanded=False):
                        for vcol, vval in visit.items():
                            st.write(f"**{vcol}:** {vval if vval else 'N/A'}")
            else:
                st.info("No visits recorded for this patient.")

            # Add new visit
            with st.expander("➕ Add Visit", expanded=False):
                with st.form(f"add_visit_form_{row['Patient ID']}"):
                    visit_date = st.date_input("Date of Visit", date.today(), key=f"vd_{row['Patient ID']}")
                    visit_type = st.selectbox("Visit Type", ["Initial", "Follow-up", "Emergency"], key=f"vt_{row['Patient ID']}")
                    doctor_name_visit = st.text_input("Doctor's Name", key=f"dn_{row['Patient ID']}")
                    diagnosis = st.text_input("Diagnosis", key=f"diag_{row['Patient ID']}")
                    notes = st.text_area("Doctor's Notes", key=f"notes_{row['Patient ID']}")

                    submit_visit = st.form_submit_button("✅ Add Visit")
                    if submit_visit:
                        try:
                            new_visit = {
                                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Patient ID": row.get("Patient ID"),
                                "Full Name": row.get("Full Name"),
                                "Date of Visit": visit_date.strftime("%Y-%m-%d"),
                                "Visit Type": visit_type,
                                "Doctor's Name": doctor_name_visit,
                                "Final Diagnosis": diagnosis,
                                "Doctor's Notes / Impression": notes,
                            }
                            sheet_visits.append_row(list(new_visit.values()))
                            st.success("✅ Visit added successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding visit: {e}")

            # Delete patient
            delete_key = f"delete_{row['Patient ID']}"
            if st.button("🗑️ Delete Patient", key=delete_key):
                try:
                    all_records = sheet_responses.get_all_records()
                    updated_records = [r for r in all_records if r.get("Patient ID") != row.get("Patient ID")]
                    sheet_responses.clear()
                    if updated_records:
                        sheet_responses.append_row(list(updated_records[0].keys()))
                        for r in updated_records:
                            sheet_responses.append_row(list(r.values()))
                    st.warning(f"❌ Deleted {row['Full Name']}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting patient: {e}")
