import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Sara Database", layout="wide")

# Google Sheets setup
SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE"
SHEET_NAME_PATIENTS = "Patients"
SHEET_NAME_VISITS = "Visits"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key("1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0")

def load_sheet(name):
    try:
        ws = sheet.worksheet(name)
        df = pd.DataFrame(ws.get_all_records())
        return df
    except Exception as e:
        st.error(f"❌ Failed to load {name}: {e}")
        return pd.DataFrame()

def save_to_sheet(name, df):
    ws = sheet.worksheet(name)
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist())

# Load both sheets
patients_df = load_sheet(SHEET_NAME_PATIENTS)
visits_df = load_sheet(SHEET_NAME_VISITS)

# Ensure columns exist
if "Patient ID" not in patients_df.columns:
    patients_df["Patient ID"] = range(1, len(patients_df) + 1)
if "Patient ID" not in visits_df.columns:
    visits_df["Patient ID"] = []
if "Visit Date" not in visits_df.columns:
    visits_df["Visit Date"] = []
if "Notes" not in visits_df.columns:
    visits_df["Notes"] = []

st.title("🩺 Sara Patient Database")

# Add new patient
st.header("➕ Add New Patient")
with st.form("add_patient_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full Name")
        age = st.number_input("Age", min_value=0, max_value=120, step=1)
    with col2:
        gender = st.selectbox("Gender", ["Male", "Female"])
        phone = st.text_input("Phone")
    add_btn = st.form_submit_button("Add Patient")

if add_btn:
    new_id = int(patients_df["Patient ID"].max()) + 1 if not patients_df.empty else 1
    new_patient = pd.DataFrame(
        [[new_id, name, age, gender, phone]],
        columns=["Patient ID", "Full Name", "Age", "Gender", "Phone"]
    )
    patients_df = pd.concat([patients_df, new_patient], ignore_index=True)
    save_to_sheet(SHEET_NAME_PATIENTS, patients_df)
    st.success(f"✅ Patient '{name}' added!")

# Show all patients
st.header("📋 Patient List")
for _, row in patients_df.iterrows():
    with st.expander(f"{row['Full Name']} (ID: {row['Patient ID']})"):
        st.write(f"**Age:** {row['Age']}")
        st.write(f"**Gender:** {row['Gender']}")
        st.write(f"**Phone:** {row['Phone']}")

        # Show visits
        patient_visits = visits_df[visits_df.get("Patient ID", None) == row["Patient ID"]] if "Patient ID" in visits_df.columns else pd.DataFrame()
        if not patient_visits.empty:
            st.subheader("Visits:")
            st.dataframe(patient_visits)
        else:
            st.info("No visits recorded.")

        # Add visit form
        with st.form(f"add_visit_form_{row['Patient ID']}_form"):
            visit_date = st.date_input("Visit Date")
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Add Visit")
        if submitted:
            new_visit = pd.DataFrame(
                [[row["Patient ID"], str(visit_date), notes]],
                columns=["Patient ID", "Visit Date", "Notes"]
            )
            visits_df = pd.concat([visits_df, new_visit], ignore_index=True)
            save_to_sheet(SHEET_NAME_VISITS, visits_df)
            st.success(f"Visit added for {row['Full Name']}")

        # Delete patient button
        if st.button(f"🗑️ Delete {row['Full Name']}", key=f"delete_{row['Patient ID']}_btn"):
            patients_df = patients_df[patients_df["Patient ID"] != row["Patient ID"]]
            visits_df = visits_df[visits_df["Patient ID"] != row["Patient ID"]]
            save_to_sheet(SHEET_NAME_PATIENTS, patients_df)
            save_to_sheet(SHEET_NAME_VISITS, visits_df)
            st.warning(f"Patient {row['Full Name']} deleted.")
            st.rerun()

st.success("✅ App loaded successfully")
