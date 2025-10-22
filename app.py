import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
from urllib.parse import quote, unquote

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sara Patient Database", layout="wide")

# --- AUTHENTICATION ---
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(st.secrets["sheet"]["sheet_name"])
    st.success("✅ Successfully connected to Google Sheet")
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

# --- ENSURE UNIQUE ID COLUMN ---
if "Patient ID" not in df.columns:
    df["Patient ID"] = [f"PT{i+1}" for i in range(len(df))]
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- QUERY PARAMETER HANDLER ---
query_params = st.query_params
patient_id = query_params.get("patient", [None])[0] if isinstance(query_params.get("patient"), list) else query_params.get("patient")

# --- DARK MODE TOGGLE ---
dark_mode = st.toggle("🌙 Dark Mode", value=False)
if dark_mode:
    st.markdown("""
        <style>
        body, .stApp {
            background-color: #121212 !important;
            color: white !important;
        }
        .stMarkdown, .stExpander, .stButton, .stSelectbox, .stTextInput, .stDataFrame {
            background-color: #1E1E1E !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

# ==============================
#  PATIENT PROFILE VIEW
# ==============================
if patient_id:
    patient_row = df[df["Patient ID"] == patient_id]
    if not patient_row.empty:
        patient = patient_row.iloc[0]

        st.title(f"👤 {patient.get('Full Name', 'Unknown Patient')}")
        st.markdown(f"**Patient ID:** {patient_id}")

        st.markdown("---")
        st.subheader("📋 Patient Information")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Date of Birth:** {patient.get('Date of Birth', '')}")
            st.markdown(f"**Age:** {patient.get('Age (in years)', '')}")
            st.markdown(f"**Sex:** {patient.get('Sex', '')}")
            st.markdown(f"**Address:** {patient.get('Address', '')}")
            st.markdown(f"**Marital Status:** {patient.get('Marital Status', '')}")
            st.markdown(f"**Occupation:** {patient.get('Occupation', '')}")
        with col2:
            st.markdown(f"**Smoking Status:** {patient.get('Smoking Status', '')}")
            st.markdown(f"**Alcohol Use:** {patient.get('Alcohol Use', '')}")
            st.markdown(f"**Substance Use:** {patient.get('Substance Use', '')}")
            st.markdown(f"**Family Hx:** {patient.get('Family Hx', '')}")
            st.markdown(f"**Past Medical Hx:** {patient.get('Past Medical Hx', '')}")
            st.markdown(f"**Past Surgical Hx:** {patient.get('Past Surgical Hx', '')}")

        st.markdown("---")
        st.subheader("🩺 Clinical Summary")
        st.markdown(f"**Date of Visit:** {patient.get('Date of Visit', '')}")
        st.markdown(f"**Doctor:** {patient.get('Doctor\'s Name', '')}")
        st.markdown(f"**Chief Complaint:** {patient.get('Cheif Compliant', '')}")
        st.markdown(f"**Working Diagnosis:** {patient.get('Working Diagnosis', '')}")
        st.markdown(f"**Final Diagnosis:** {patient.get('Final Diagnosis', '')}")
        st.markdown(f"**Medications Prescribed:** {patient.get('Medications Prescribed', '')}")
        st.markdown(f"**Follow-Up Date:** {patient.get('Follow-Up Date', '')}")
        st.markdown(f"**Doctor's Notes:** {patient.get('Doctor\'s Notes / Impression', '')}")

        with st.expander("➕ Add New Visit"):
            st.write("Fill in visit details for this patient:")
            visit_data = {}
            columns = list(df.columns)

            for i, col in enumerate(columns):
                key = f"visit_{i}"
                if col.lower() in ["timestamp"]:
                    visit_data[col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                elif "date" in col.lower():
                    visit_data[col] = st.date_input(col, key=key)
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
                else:
                    visit_data[col] = st.text_input(col, key=key)

            if st.button("💾 Add Visit"):
                try:
                    sheet.append_row(list(visit_data.values()))
                    st.success("New visit added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding visit: {e}")

    else:
        st.error("❌ Patient not found in database.")
    st.stop()

# ==============================
#  MAIN DASHBOARD VIEW
# ==============================

st.title("🩺 Sara Patient Database")

# --- SEARCH PATIENT ---
st.subheader("🔍 Search Patients")
search_query = st.text_input("Search by Full Name").strip().lower()

if search_query:
    filtered_df = df[df["Full Name"].str.lower().str.contains(search_query)]
else:
    filtered_df = df

# --- DISPLAY PATIENT LIST ---
if not filtered_df.empty:
    for _, row in filtered_df.iterrows():
        patient_id = row.get("Patient ID", "")
        link = f"?patient={quote(patient_id)}"
        st.markdown(f"👤 [{row['Full Name']} (Age: {row.get('Age (in years)', 'N/A')})]({link})")
else:
    st.info("No patients found.")

# --- ADD NEW PATIENT ---
with st.expander("➕ Add New Patient"):
    st.write("Fill in the patient details below:")
    new_data = {}
    columns = list(df.columns)

    for i, col in enumerate(columns):
        key = f"patient_{i}"
        if col.lower() in ["timestamp"]:
            new_data[col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif col.lower() == "patient id":
            new_data[col] = f"PT{len(df) + 1}"
        elif "date" in col.lower():
            new_data[col] = st.date_input(col, key=key)
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
        else:
            new_data[col] = st.text_input(col, key=key)

    if st.button("✅ Add Patient"):
        try:
            sheet.append_row(list(new_data.values()))
            st.success(f"New patient added successfully! [Open Profile](?patient={quote(new_data['Patient ID'])})")
            st.rerun()
        except Exception as e:
            st.error(f"Error adding patient: {e}")
