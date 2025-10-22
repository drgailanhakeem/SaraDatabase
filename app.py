import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid

st.set_page_config(page_title="Sara Patient Database", layout="wide")

# ===== GOOGLE SHEETS CONNECTION =====
SHEET_NAME = "Sara Patient Database"
SHEET_ID = "1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"

# Google API connection
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(credentials)
sheet = client.open_by_key(SHEET_ID)

# ===== CONSTANT HEADERS =====
EXPECTED_COLUMNS = [
    "Timestamp", "Full Name", "Date of Birth", "Age (in years)", "Sex", "Address", "Date of Visit",
    "Time of Visit", "Doctor's Name", "Cheif Compliant", "Duration of Compliant", "Onset", "HPI",
    "Associated Symptoms", "Relevant Negatives", "Past Medical Hx", "Past Surgical Hx", "Allergies",
    "Current Medications", "Family Hx", "Smoking Status", "Alcohol Use", "Substance Use",
    "Occupation", "Marital Status", "General", "CVS", "Respiratory", "GIT", "GUT", "Neurology",
    "Psychiatry", "Vital Signs", "Height", "Weight", "General Apperance",
    "Physical Examination Findings", "Lab Tests Ordered", "Lab Results", "Imaging Studies",
    "Working Diagnosis", "Differential Diagnosis", "Final Diagnosis", "Medications Prescribed",
    "Non-Pharmacologic Advice", "Referrals", "Follow-Up Date", "Doctor's Notes / Impression",
    "Visit Type", "Submitter Name", "Patient ID"
]

# ===== LOAD SHEETS =====
try:
    sheet_responses = sheet.worksheet("Responses")
    sheet_visits = sheet.worksheet("Visits")

    df_responses = pd.DataFrame(sheet_responses.get_all_records())
    df_visits = pd.DataFrame(sheet_visits.get_all_records())

    # Ensure all expected columns exist
    for df in [df_responses, df_visits]:
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = ""

except Exception as e:
    st.error(f"❌ Failed to load sheets: {e}")
    st.stop()

# ===== SIDEBAR =====
st.sidebar.title("🩺 Sara Patient Database")
page = st.sidebar.radio("Navigate", ["View Patients", "Add Patient"])

# ===== ADD PATIENT PAGE =====
if page == "Add Patient":
    st.header("➕ Add New Patient")
    with st.form("add_patient_form"):
        new_data = {}
        for col in EXPECTED_COLUMNS:
            new_data[col] = st.text_input(col)
        submitted = st.form_submit_button("✅ Submit")
        if submitted:
            try:
                new_data["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_data["Patient ID"] = str(uuid.uuid4())[:8]
                sheet_responses.append_row([new_data.get(c, "") for c in EXPECTED_COLUMNS])
                st.success("✅ Patient added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding patient: {e}")

# ===== VIEW PATIENTS PAGE =====
elif page == "View Patients":
    st.header("📋 Patient List")
    search_query = st.text_input("Search by patient name or ID:")

    if not df_responses.empty:
        if search_query:
            filtered = df_responses[
                df_responses["Full Name"].str.contains(search_query, case=False, na=False)
                | df_responses["Patient ID"].astype(str).str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered = df_responses

        for _, row in filtered.iterrows():
            with st.expander(f"{row['Full Name']} (ID: {row['Patient ID']})"):
                st.write("**Demographics:**")
                st.write({
                    "Date of Birth": row["Date of Birth"],
                    "Age": row["Age (in years)"],
                    "Sex": row["Sex"],
                    "Address": row["Address"]
                })

                st.divider()

                # Visits section
                patient_visits = df_visits[df_visits["Patient ID"] == row["Patient ID"]]
                st.subheader("🩺 Visits")
                if not patient_visits.empty:
                    st.dataframe(patient_visits[["Date of Visit", "Time of Visit", "Doctor's Name", "Final Diagnosis"]])
                else:
                    st.info("No visits yet.")

                st.divider()

                # Add Visit Form
                st.subheader("➕ Add Visit")
                unique_form_key = f"add_visit_form_{row['Patient ID']}_{uuid.uuid4().hex[:6]}"
                with st.form(unique_form_key):
                    visit_data = {}
                    for col in EXPECTED_COLUMNS:
                        visit_data[col] = st.text_input(col, key=f"{col}_{row['Patient ID']}_{uuid.uuid4().hex[:4]}")
                    submit_visit = st.form_submit_button("✅ Add Visit")
                    if submit_visit:
                        try:
                            visit_data["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            visit_data["Patient ID"] = row["Patient ID"]
                            visit_data["Full Name"] = row["Full Name"]
                            sheet_visits.append_row([visit_data.get(c, "") for c in EXPECTED_COLUMNS])
                            st.success("✅ Visit added successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding visit: {e}")

                # Delete patient
                if st.button(f"🗑️ Delete Patient {row['Full Name']}", key=f"delete_{row['Patient ID']}"):
                    try:
                        idx = df_responses[df_responses["Patient ID"] == row["Patient ID"]].index
                        if not idx.empty:
                            sheet_responses.delete_rows(int(idx[0]) + 2)
                            st.warning("⚠️ Patient deleted!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting patient: {e}")

    else:
        st.info("No patient data found.")
