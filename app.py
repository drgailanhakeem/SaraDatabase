import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import uuid

st.set_page_config(page_title="Sara Database", layout="wide")

# --- Authenticate with Google Sheets ---
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(
        st.secrets["sheet"]["sheet_name"]
    )
    st.success("✅ Successfully connected to Google Sheet")
except Exception as e:
    st.error("❌ Google Sheets authentication failed. Check your Streamlit Secrets.")
    st.stop()

# --- Load DataFrame ---
try:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error("❌ Failed to load data from Google Sheet.")
    st.stop()

# --- Ensure unique ID for patients ---
if "Patient ID" not in df.columns:
    df["Patient ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]

st.title("🩺 Sara Patient Database")

# --- Routing using new st.query_params API ---
query_params = st.query_params
selected_patient_id = query_params.get("patient", None)

if selected_patient_id:
    # Individual Patient Page
    patient_data = df[df["Patient ID"] == selected_patient_id]

    if not patient_data.empty:
        patient = patient_data.iloc[0]
        st.header(f"👤 {patient['Full Name']}")
        st.markdown(f"**Age:** {patient.get('Age', 'N/A')}")
        st.markdown(f"**Gender:** {patient.get('Gender', 'N/A')}")
        st.markdown(f"**Phone:** {patient.get('Phone Number', 'N/A')}")
        st.markdown(f"**Address:** {patient.get('Address', 'N/A')}")
        st.markdown(f"**Diagnosis:** {patient.get('Diagnosis', 'N/A')}")
        st.divider()

        # --- Add Visit Section ---
        st.subheader("📋 Add Visit")
        with st.form("add_visit_form"):
            visit_data = {}
            visit_data["Date"] = st.date_input("Visit Date")
            visit_data["Doctor"] = st.text_input("Doctor's Name")
            visit_data["Notes"] = st.text_area("Visit Notes")
            submitted = st.form_submit_button("Add Visit")

            if submitted:
                st.success("✅ Visit added successfully (simulation).")
    else:
        st.error("❌ Patient not found in database.")
else:
    # --- Main Page: Patient List + Add New Patient ---
    st.header("🔍 Search Patients")
    search_term = st.text_input("Search by Full Name")

    if search_term:
        filtered_df = df[df["Full Name"].str.contains(search_term, case=False, na=False)]
    else:
        filtered_df = df

    for _, row in filtered_df.iterrows():
        patient_link = f"?patient={row['Patient ID']}"
        with st.expander(f"👤 {row['Full Name']} (Age: {row.get('Age', 'N/A')})"):
            st.markdown(f"[Open Patient Profile]({patient_link})")

    st.divider()
    st.subheader("➕ Add New Patient")
    with st.form("add_patient_form"):
        new_patient = {}
        for col in ["Full Name", "Age", "Gender", "Phone Number", "Address", "Diagnosis"]:
            new_patient[col] = st.text_input(col)
        submitted = st.form_submit_button("Add Patient")

        if submitted:
            st.success("✅ New patient added successfully (simulation).")
