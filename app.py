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

# --- Ensure Unique ID Column ---
if "Patient ID" not in df.columns:
    df["Patient ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
    # Update sheet with new ID column
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

st.title("🩺 Sara Patient Database")

# --- Use modern query params ---
query_params = st.query_params
selected_patient_id = query_params.get("patient", [None])
if isinstance(selected_patient_id, list):
    selected_patient_id = selected_patient_id[0]

# --- PATIENT PROFILE PAGE ---
if selected_patient_id:
    patient_data = df[df["Patient ID"] == selected_patient_id]

    if not patient_data.empty:
        patient = patient_data.iloc[0]
        st.markdown(f"### 👤 {patient['Full Name']}")
        st.divider()

        # --- Modern card layout ---
        cols = st.columns(2)
        with cols[0]:
            st.markdown(f"**Age:** {patient.get('Age (in years)', 'N/A')}")
            st.markdown(f"**Sex:** {patient.get('Sex', 'N/A')}")
            st.markdown(f"**Address:** {patient.get('Address', 'N/A')}")
            st.markdown(f"**Occupation:** {patient.get('Occupation', 'N/A')}")
        with cols[1]:
            st.markdown(f"**Marital Status:** {patient.get('Marital Status', 'N/A')}")
            st.markdown(f"**Doctor:** {patient.get('Doctor\'s Name', 'N/A')}")
            st.markdown(f"**Date of Visit:** {patient.get('Date of Visit', 'N/A')}")
            st.markdown(f"**Chief Complaint:** {patient.get('Cheif Compliant', 'N/A')}")

        st.divider()
        st.subheader("🩹 Add New Visit")
        with st.form("add_visit_form"):
            visit_data = {}
            columns = sheet.row_values(1)
            for col in columns:
                if col in ["Timestamp", "Patient ID"]:
                    continue
                visit_data[col] = st.text_input(col)
            submitted = st.form_submit_button("Submit Visit")

            if submitted:
                new_row = [visit_data.get(col, "") for col in columns]
                new_row[columns.index("Patient ID")] = patient["Patient ID"]
                sheet.append_row(new_row)
                st.success("✅ Visit added successfully!")
                st.rerun()
    else:
        st.error("❌ Patient not found in database.")

# --- MAIN DASHBOARD PAGE ---
else:
    st.header("🔍 Search Patients")
    search_term = st.text_input("Search by Full Name")

    if search_term:
        filtered_df = df[df["Full Name"].str.contains(search_term, case=False, na=False)]
    else:
        filtered_df = df

    for _, row in filtered_df.iterrows():
        patient_link = f"?patient={row['Patient ID']}"
        st.markdown(
            f"""
            <div style="background-color:#f0f2f6;padding:15px;margin:10px 0;border-radius:10px">
                <strong>{row['Full Name']}</strong><br>
                Age: {row.get('Age (in years)', 'N/A')} | Sex: {row.get('Sex', 'N/A')}<br>
                <a href="{patient_link}" target="_self" style="color:#1e88e5;text-decoration:none;">View Profile</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("➕ Add New Patient")
    with st.expander("Add New Patient Form"):
        with st.form("add_patient_form"):
            new_patient = {}
            columns = sheet.row_values(1)
            for col in columns:
                if col in ["Timestamp", "Patient ID"]:
                    continue
                new_patient[col] = st.text_input(col)
            submitted = st.form_submit_button("Add Patient")

            if submitted:
                new_id = str(uuid.uuid4())[:8]
                new_patient["Patient ID"] = new_id
                new_row = [new_patient.get(col, "") for col in columns]
                sheet.append_row(new_row)
                st.success(f"✅ Patient added successfully! [Open Profile](?patient={new_id})")
