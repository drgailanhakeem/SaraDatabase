import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ===============================
# CONFIGURATION
# ===============================
SHEET_ID = "1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"
SHEET_NAME_RESPONSES = "Responses"
SHEET_NAME_VISITS = "Visits"

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

st.set_page_config(page_title="Sara Patient Database", layout="wide")

# ===============================
# GOOGLE SHEETS CONNECTION
# ===============================
try:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPE
    )
    client = gspread.authorize(creds)
    sheet_file = client.open_by_key(SHEET_ID)
    sheet_responses = sheet_file.worksheet(SHEET_NAME_RESPONSES)
    sheet_visits = sheet_file.worksheet(SHEET_NAME_VISITS)
except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheets: {e}")
    st.stop()

# ===============================
# EXPECTED COLUMNS
# ===============================
EXPECTED_COLUMNS = [
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

# ===============================
# LOAD DATA (Robust Cleaner)
# ===============================
def load_data(sheet):
    df = pd.DataFrame(sheet.get_all_records())
    # Clean column names
    df.columns = [str(c).strip().replace("  ", " ") for c in df.columns]

    # Add any missing expected columns
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Reorder columns consistently
    df = df[[c for c in EXPECTED_COLUMNS if c in df.columns]]
    return df

try:
    patients_df = load_data(sheet_responses)
    visits_df = load_data(sheet_visits)
except Exception as e:
    st.error(f"❌ Failed to load sheets: {e}")
    st.stop()

# Ensure Patient ID is string
patients_df["Patient ID"] = patients_df["Patient ID"].fillna("").astype(str)
visits_df["Patient ID"] = visits_df["Patient ID"].fillna("").astype(str)

# ===============================
# MAIN APP
# ===============================
st.title("🏥 Sara Patient Database")

# Search Bar
search = st.text_input("🔍 Search Patient by Name or ID").strip().lower()

if not patients_df.empty:
    filtered_patients = patients_df[
        patients_df.apply(
            lambda row: search in str(row["Full Name"]).lower() or search in str(row["Patient ID"]).lower(),
            axis=1,
        )
    ] if search else patients_df

    for i, row in filtered_patients.iterrows():
        unique_suffix = f"_{i}"  # unique per row to avoid duplicate keys

        with st.expander(f"👤 {row['Full Name']} ({row['Patient ID']})", expanded=False):
            st.markdown("### 🧾 Patient Information")
            for col, val in row.items():
                st.write(f"**{col}:** {val if val else 'N/A'}")

            # ===============================
            # VISITS SECTION
            # ===============================
            st.markdown("### 🩺 Visits")
            patient_visits = visits_df[visits_df["Patient ID"] == row["Patient ID"]]

            if not patient_visits.empty:
                for j, visit in patient_visits.sort_values("Date of Visit", ascending=False).iterrows():
                    with st.expander(f"📅 {visit['Date of Visit']} — {visit.get('Visit Type', 'N/A')}", expanded=False):
                        for vcol, vval in visit.items():
                            st.write(f"**{vcol}:** {vval if vval else 'N/A'}")
            else:
                st.info("No visits recorded for this patient.")

            st.divider()

            # ===============================
            # ADD VISIT FORM
            # ===============================
            with st.expander("➕ Add Visit", expanded=False):
                with st.form(f"add_visit_form_{row['Patient ID']}{unique_suffix}"):
                    visit_data = {}
                    for col in EXPECTED_COLUMNS:
                        visit_data[col] = st.text_input(col, key=f"{col}_{row['Patient ID']}{unique_suffix}")
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

            # ===============================
            # DELETE BUTTON
            # ===============================
            delete_key = f"delete_{row['Patient ID']}{unique_suffix}"
            if st.button("🗑️ Delete Patient", key=delete_key):
                try:
                    all_records = sheet_responses.get_all_records()
                    updated_records = [r for r in all_records if str(r.get("Patient ID")) != str(row["Patient ID"])]
                    sheet_responses.clear()
                    if updated_records:
                        sheet_responses.append_row(list(updated_records[0].keys()))
                        for r in updated_records:
                            sheet_responses.append_row(list(r.values()))
                    st.warning(f"❌ Deleted {row['Full Name']}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting patient: {e}")

else:
    st.warning("⚠️ No patient records found.")

# ===============================
# ADD NEW PATIENT
# ===============================
st.divider()
with st.expander("➕ Add New Patient", expanded=False):
    with st.form("add_patient_form"):
        patient_data = {}
        for col in EXPECTED_COLUMNS:
            patient_data[col] = st.text_input(col)
        submitted = st.form_submit_button("✅ Add Patient")
        if submitted:
            try:
                patient_data["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if not patient_data.get("Patient ID"):
                    patient_data["Patient ID"] = f"PT{len(patients_df)+1:04d}"
                sheet_responses.append_row([patient_data.get(c, "") for c in EXPECTED_COLUMNS])
                st.success(f"✅ Added new patient: {patient_data['Full Name']}")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding patient: {e}")
