import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sara Patient Database", layout="wide")

# --- AUTHENTICATION ---
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(st.secrets["sheet"]["sheet_name"])
    st.success("✅ Connected to Google Sheet")
except Exception as e:
    st.error(f"❌ Google Sheets Connection Failed: {e}")
    st.stop()

# --- LOAD DATA ---
try:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.stop()

# Ensure patient IDs exist
if "Patient ID" not in df.columns:
    df.insert(0, "Patient ID", [f"pt{i+1}" for i in range(len(df))])

# --- ROUTING ---
params = st.query_params
patient_id = params.get("id", [None])[0] if isinstance(params.get("id"), list) else params.get("id")

# --- PATIENT PROFILE PAGE ---
if patient_id:
    st.title("👤 Patient Profile")

    patient = df[df["Patient ID"] == patient_id]
    if patient.empty:
        st.error("❌ Patient not found.")
        st.stop()

    patient = patient.iloc[0]
    st.header(f"{patient.get('Full Name', 'Unknown')} (ID: {patient_id})")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Sex:** {patient.get('Sex', '')}")
        st.markdown(f"**Age:** {patient.get('Age (in years)', '')}")
        st.markdown(f"**Date of Birth:** {patient.get('Date of Birth', '')}")
        st.markdown(f"**Address:** {patient.get('Address', '')}")
        st.markdown(f"**Marital Status:** {patient.get('Marital Status', '')}")
    with col2:
        st.markdown(f"**Date of Visit:** {patient.get('Date of Visit', '')}")
        st.markdown(f"**Doctor's Name:** {patient.get('Doctor\'s Name', '')}")
        st.markdown(f"**Working Diagnosis:** {patient.get('Working Diagnosis', '')}")
        st.markdown(f"**Final Diagnosis:** {patient.get('Final Diagnosis', '')}")
        st.markdown(f"**Doctor's Notes / Impression:** {patient.get('Doctor\'s Notes / Impression', '')}")

    # --- DELETE PATIENT ---
    if st.button("🗑️ Delete Patient"):
        try:
            row_index = df.index[df["Patient ID"] == patient_id][0] + 2
            sheet.delete_rows(row_index)
            st.success(f"✅ Deleted {patient.get('Full Name', 'patient')}")
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error deleting patient: {e}")

    # --- ADD VISIT SECTION ---
    st.divider()
    with st.expander("➕ Add Visit"):
        st.subheader("Add New Visit")
        visit_data = {}
        for col in df.columns:
            if col.lower() in ["timestamp", "patient id"]:
                continue
            key = f"visit_{col}"
            if "date" in col.lower():
                visit_data[col] = st.date_input(col, key=key)
            elif "time" in col.lower():
                visit_data[col] = st.time_input(col, key=key)
            elif "sex" in col.lower():
                visit_data[col] = st.selectbox(col, ["Male", "Female", "Other"], key=key)
            elif "smoking" in col.lower():
                visit_data[col] = st.selectbox(col, ["Never", "Former", "Current"], key=key)
            elif "alcohol" in col.lower():
                visit_data[col] = st.selectbox(col, ["No", "Occasionally", "Regularly"], key=key)
            elif "substance" in col.lower():
                visit_data[col] = st.selectbox(col, ["No", "Yes"], key=key)
            elif "marital" in col.lower():
                visit_data[col] = st.selectbox(col, ["Single", "Married", "Divorced", "Widowed"], key=key)
            elif "past medical history" in col.lower():
                visit_data[col] = st.selectbox(col, ["None", "Diabetes", "Hypertension", "Cardiac Disease", "Asthma", "Other"], key=key)
            else:
                visit_data[col] = st.text_input(col, key=key)

        if st.button("💾 Save Visit"):
            try:
                visit_data["Patient ID"] = patient_id
                visit_data = {k: str(v) for k, v in visit_data.items()}
                visits_sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet("Visits")
                visits_sheet.append_row(list(visit_data.values()))
                st.success("✅ Visit added successfully!")
            except Exception as e:
                st.error(f"❌ Error adding visit: {e}")

    st.divider()
    st.markdown("[⬅ Back to Home](?)")

# --- HOMEPAGE ---
else:
    st.title("🩺 Sara Patient Database")

    st.subheader("🔍 Search Patients")
    search_query = st.text_input("Search by Full Name").strip().lower()

    if search_query:
        filtered_df = df[df["Full Name"].str.lower().str.contains(search_query)]
    else:
        filtered_df = df

    if not filtered_df.empty:
        for _, row in filtered_df.iterrows():
            st.markdown(
                f"### [{row['Full Name']} (Age: {row.get('Age (in years)', 'N/A')})](?id={row['Patient ID']})"
            )
    else:
        st.info("No patients found.")

    # --- ADD NEW PATIENT ---
    with st.expander("➕ Add New Patient"):
        new_data = {}
        for col in df.columns:
            if col == "Patient ID":
                continue
            key = f"patient_{col}"
            if "date" in col.lower():
                new_data[col] = st.date_input(col, key=key)
            elif "time" in col.lower():
                new_data[col] = st.time_input(col, key=key)
            elif "sex" in col.lower():
                new_data[col] = st.selectbox(col, ["Male", "Female", "Other"], key=key)
            elif "smoking" in col.lower():
                new_data[col] = st.selectbox(col, ["Never", "Former", "Current"], key=key)
            elif "alcohol" in col.lower():
                new_data[col] = st.selectbox(col, ["No", "Occasionally", "Regularly"], key=key)
            elif "substance" in col.lower():
                new_data[col] = st.selectbox(col, ["No", "Yes"], key=key)
            elif "marital" in col.lower():
                new_data[col] = st.selectbox(col, ["Single", "Married", "Divorced", "Widowed"], key=key)
            elif "past medical history" in col.lower():
                new_data[col] = st.selectbox(col, ["None", "Diabetes", "Hypertension", "Cardiac Disease", "Asthma", "Other"], key=key)
            else:
                new_data[col] = st.text_input(col, key=key)

        if st.button("✅ Add Patient"):
            try:
                new_id = f"pt{len(df) + 1}"
                new_data["Patient ID"] = new_id
                new_data = {k: str(v) for k, v in new_data.items()}
                sheet.append_row(list(new_data.values()))
                st.success(f"✅ Added {new_data.get('Full Name', 'New Patient')} successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error adding patient: {e}")
