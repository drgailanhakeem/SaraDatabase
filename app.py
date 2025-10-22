import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials

# ===============================
# GOOGLE SHEET SETUP
# ===============================
st.set_page_config(page_title="Sara Database", layout="wide")

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials from Streamlit secrets
credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPE
)

client = gspread.authorize(credentials)

try:
    # Open both sheets by name
    sheet_patients = client.open("SaraDatabase").worksheet("Responses")
    sheet_visits = client.open("SaraDatabase").worksheet("Visits")

    # Load data
    patients_data = sheet_patients.get_all_records()
    visits_data = sheet_visits.get_all_records()

    patients_df = pd.DataFrame(patients_data)
    visits_df = pd.DataFrame(visits_data)

except Exception as e:
    st.error(f"❌ Failed to load sheets: {e}")
    st.stop()

# ===============================
# FUNCTIONS
# ===============================
def delete_patient(patient_id):
    try:
        rows = sheet_patients.get_all_records()
        new_rows = [r for r in rows if str(r.get("Patient ID")) != str(patient_id)]

        sheet_patients.clear()
        sheet_patients.append_row(list(patients_df.columns))
        for r in new_rows:
            sheet_patients.append_row(list(r.values()))

        # Delete visits too
        visit_rows = sheet_visits.get_all_records()
        new_visits = [r for r in visit_rows if str(r.get("Patient ID")) != str(patient_id)]

        sheet_visits.clear()
        sheet_visits.append_row(list(visits_df.columns))
        for r in new_visits:
            sheet_visits.append_row(list(r.values()))

        st.success(f"✅ Patient {patient_id} and all related visits deleted.")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to delete patient: {e}")

def add_visit(patient_id):
    with st.form(f"add_visit_form_{patient_id}"):
        visit_data = {}
        for col in visits_df.columns:
            if col == "Patient ID":
                visit_data[col] = patient_id
            elif "date" in col.lower():
                visit_data[col] = st.date_input(col, key=f"{patient_id}_{col}")
            elif "time" in col.lower():
                visit_data[col] = st.time_input(col, key=f"{patient_id}_{col}")
            else:
                visit_data[col] = st.text_input(col, key=f"{patient_id}_{col}")

        if st.form_submit_button("💾 Save Visit"):
            try:
                visit_data = {
                    k: str(v) if isinstance(v, (datetime, date)) else v
                    for k, v in visit_data.items()
                }
                sheet_visits.append_row(list(visit_data.values()))
                st.success("✅ Visit added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error adding visit: {e}")

# ===============================
# MAIN APP
# ===============================
st.title("🏥 Sara Patient Database")

search = st.text_input("🔍 Search Patient by Name or ID").strip().lower()

if not patients_df.empty:
    filtered_patients = (
        patients_df[
            patients_df.apply(
                lambda x: search in str(x["Patient ID"]).lower()
                or search in str(x["Name"]).lower(),
                axis=1,
            )
        ]
        if search
        else patients_df
    )

    for _, row in filtered_patients.iterrows():
        with st.expander(f"👤 {row['Name']} ({row['Patient ID']})", expanded=False):
            for col, val in row.items():
                st.markdown(f"**{col}:** {val}")

            delete_key = f"delete_{row['Patient ID']}"
            if st.button("🗑️ Delete Patient", key=delete_key):
                delete_patient(row["Patient ID"])

            # ADD VISIT TOGGLE
            if st.toggle(f"➕ Add Visit for {row['Name']}", key=f"toggle_add_visit_{row['Patient ID']}"):
                add_visit(row["Patient ID"])

            # Display visits for that patient
            patient_visits = visits_df[visits_df["Patient ID"] == row["Patient ID"]]
            if not patient_visits.empty:
                st.markdown("### 🩺 Visits")
                patient_visits = patient_visits.sort_values(
                    by=[c for c in patient_visits.columns if "date" in c.lower()][0],
                    ascending=False,
                )
                for i, v in patient_visits.iterrows():
                    with st.expander(f"📅 Visit on {v[0]}"):
                        for col, val in v.items():
                            st.markdown(f"**{col}:** {val}")

# ===============================
# ADD NEW PATIENT (TOGGLEABLE)
# ===============================
st.divider()
st.subheader("➕ Add New Patient")

if st.toggle("Show Add New Patient Form", value=False):
    with st.form("add_new_patient"):
        new_data = {}
        for col in patients_df.columns:
            if col == "Patient ID":
                new_data[col] = f"pt{len(patients_df)+1}"
            elif "date" in col.lower():
                new_data[col] = st.date_input(col, key=f"new_{col}")
            elif "time" in col.lower():
                new_data[col] = st.time_input(col, key=f"new_{col}")
            else:
                new_data[col] = st.text_input(col, key=f"new_{col}")

        if st.form_submit_button("✅ Add Patient"):
            try:
                new_data = {
                    k: str(v) if isinstance(v, (datetime, date)) else v
                    for k, v in new_data.items()
                }
                sheet_patients.append_row(list(new_data.values()))
                st.success("✅ New patient added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error adding patient: {e}")
else:
    st.info("Toggle the switch above to add a new patient.")
