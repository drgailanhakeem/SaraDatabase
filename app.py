import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# ===========================
# GOOGLE SHEET CONNECTION
# ===========================
SHEET_NAME = "Sara Patient Database"

st.set_page_config(page_title="Sara Patient Database", page_icon="🩺", layout="wide")

try:
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    st.success("✅ Successfully connected to Google Sheet")
except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheet: {e}")
    st.stop()

# Ensure ID column exists
if "ID" not in df.columns:
    if not df.empty:
        df.insert(0, "ID", range(1, len(df) + 1))
    else:
        df = pd.DataFrame(columns=["ID"])

# ===========================
# ROUTING LOGIC
# ===========================
query_params = st.query_params
page = query_params.get("page", ["home"])[0]
selected_id = query_params.get("id", [None])[0]

# ===========================
# HOME PAGE
# ===========================
if page == "home":
    st.title("🩺 Sara Patient Database")
    search = st.text_input("🔍 Search Patients", placeholder="Search by Full Name")

    filtered_df = df[df["Full Name"].str.contains(search, case=False, na=False)] if search else df

    for _, row in filtered_df.iterrows():
        patient_name = row.get("Full Name", "Unnamed")
        age = row.get("Age", "N/A")
        patient_id = row.get("ID")

        st.markdown(
            f"👤 [{patient_name} (Age: {age})](?page=patient&id={patient_id})"
        )

    st.markdown("### ➕ [Add New Patient](?page=add_patient)")

# ===========================
# ADD NEW PATIENT PAGE
# ===========================
elif page == "add_patient":
    st.title("➕ Add New Patient")

    with st.form("add_patient_form"):
        new_data = {}
        for col in df.columns:
            if col == "ID":
                continue
            new_data[col] = st.text_input(col)

        if st.form_submit_button("Save Patient"):
            new_id = df["ID"].max() + 1 if not df.empty else 1
            new_data["ID"] = new_id
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            sheet.append_row(list(new_data.values()))
            st.success(f"✅ Patient '{new_data.get('Full Name', '')}' added successfully!")
            st.rerun()

# ===========================
# PATIENT PROFILE PAGE
# ===========================
elif page == "patient" and selected_id:
    try:
        selected_id = int(selected_id)
        patient_data = df[df["ID"] == selected_id]

        if patient_data.empty:
            st.error("❌ Patient not found in database.")
        else:
            patient = patient_data.iloc[0]
            st.title(f"👤 {patient.get('Full Name', 'Unknown')} — Age: {patient.get('Age', 'N/A')}")

            # Grouped display
            with st.container():
                st.subheader("🧾 General Info")
                general_cols = ["Full Name", "Age", "Gender", "Phone", "Address"]
                for col in general_cols:
                    if col in patient:
                        st.markdown(f"**{col}:** {patient[col]}")

            with st.container():
                st.subheader("⚕️ Medical Info")
                medical_cols = ["Diagnosis", "Medications", "Allergies", "Doctor's Name"]
                for col in medical_cols:
                    if col in patient:
                        st.markdown(f"**{col}:** {patient[col]}")

            with st.container():
                st.subheader("🧪 Lab Results")
                lab_cols = [
                    "HbA1c", "FBG", "PPG", "Blood Pressure", "Weight", "Height",
                    "BMI", "Cholesterol", "Triglycerides"
                ]
                for col in lab_cols:
                    if col in patient:
                        st.markdown(f"**{col}:** {patient[col]}")

            # Visits Section (dummy placeholder)
            with st.container():
                st.subheader("📋 Visits History")
                st.info("Visit history display will be connected here later.")

            # Add New Visit Section
            with st.expander("➕ Add New Visit", expanded=False):
                with st.form("add_visit_form"):
                    visit_data = {}
                    visit_data["ID"] = selected_id
                    visit_data["Date"] = st.date_input("Visit Date")
                    visit_data["Doctor's Name"] = st.text_input("Doctor's Name")
                    visit_data["Notes"] = st.text_area("Visit Notes")

                    if st.form_submit_button("Save Visit"):
                        st.success("✅ Visit added successfully (future: save to Google Sheet).")

    except Exception as e:
        st.error(f"⚠️ Error displaying patient: {e}")

# ===========================
# DEFAULT / 404 PAGE
# ===========================
else:
    st.error("❌ Invalid page or missing data.")
