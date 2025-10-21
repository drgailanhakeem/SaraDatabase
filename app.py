# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import gspread
from datetime import date
import urllib.parse

# --- Google Sheets Setup ---
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)

# --- Read Sheet ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/edit?gid=905987173#gid=905987173"
sheet = client.open_by_url(SHEET_URL).sheet1
data = pd.DataFrame(sheet.get_all_records())

st.title("Patient Database")

# --- Ensure column exists ---
if "Full Name" not in data.columns:
    st.error("⚠️ Column 'Full Name' not found in your sheet. Please check your column names.")
    st.stop()

# --- Get patient from URL (if present) ---
query_params = st.query_params
if "patient" in query_params:
    selected_patient = urllib.parse.unquote(query_params["patient"][0])
else:
    patient_names = sorted(data["Full Name"].unique())
    selected_patient = st.selectbox("Select a patient:", patient_names)

    # Update the URL when a patient is selected
    encoded_name = urllib.parse.quote(selected_patient)
    st.query_params["patient"] = encoded_name

# --- Display patient data ---
st.subheader(f"Visits for {selected_patient}")
filtered = data[data["Full Name"] == selected_patient]
st.dataframe(filtered)

# --- Generate shareable link ---
encoded_patient = urllib.parse.quote(selected_patient)
link = f"{st.request.url_root}?patient={encoded_patient}"
st.markdown(f"🔗 **Direct link to this patient:** [{link}]({link})")

# --- Add New Visit ---
st.subheader("Add New Visit")

with st.form("new_visit_form"):
    visit_date = st.date_input("Visit Date", value=date.today())
    weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
    note = st.text_area("Notes (optional)")
    submitted = st.form_submit_button("Add Visit")

    if submitted:
        new_row = {
            "Full Name": selected_patient,
            "Visit Date": visit_date.strftime("%Y-%m-%d"),
            "Weight": weight,
            "Notes": note
        }

        # Fill missing columns to match sheet
        for col in data.columns:
            if col not in new_row:
                new_row[col] = ""

        sheet.append_row(list(new_row.values()))
        st.success("✅ Visit added successfully!")

        # Refresh data
        data = pd.DataFrame(sheet.get_all_records())
        filtered = data[data["Full Name"] == selected_patient]
        st.dataframe(filtered)
