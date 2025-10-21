import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import uuid

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Sara Patient Database", layout="wide")

# ---------- DARK MODE ----------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

def toggle_dark_mode():
    st.session_state.dark_mode = not st.session_state.dark_mode

if st.session_state.dark_mode:
    st.markdown("""
        <style>
            body, .stApp { background-color: #0E1117; color: white; }
            .card {
                background-color: #1E1E1E;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 15px;
                box-shadow: 0 0 10px rgba(255,255,255,0.1);
            }
            .visit-card {
                background-color: #141414;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 10px;
                border-left: 4px solid #00BFFF;
            }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
            .card {
                background-color: #F9F9F9;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 15px;
                box-shadow: 0 0 6px rgba(0,0,0,0.1);
            }
            .visit-card {
                background-color: #FFFFFF;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 10px;
                border-left: 4px solid #2196F3;
            }
        </style>
    """, unsafe_allow_html=True)

st.sidebar.button("🌗 Toggle Dark Mode", on_click=toggle_dark_mode)

# ---------- GOOGLE SHEETS AUTH ----------
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(st.secrets["sheet"]["sheet_name"])

# ---------- LOAD DATA ----------
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Ensure unique ID column exists
if "Patient ID" not in df.columns:
    df["Patient ID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]

# ---------- PAGE TITLE ----------
st.title("🩺 Sara Patient Database")

# ---------- URL STATE MANAGEMENT ----------
query_params = st.query_params
patient_id = query_params.get("id")

# ---------- PATIENT PROFILE PAGE ----------
if patient_id:
    patient_data = df[df["Patient ID"] == patient_id]

    if not patient_data.empty:
        patient = patient_data.iloc[0]
        st.header(f"👤 {patient['Full Name']}")
        st.caption(f"🆔 ID: {patient_id}")

        # ----- PERSONAL INFO CARD -----
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Personal Information")
        cols = st.columns(2)
        with cols[0]:
            st.markdown(f"**Date of Birth:** {patient.get('Date of Birth', 'N/A')}")
            st.markdown(f"**Age:** {patient.get('Age (in years)', 'N/A')}")
            st.markdown(f"**Sex:** {patient.get('Sex', 'N/A')}")
        with cols[1]:
            st.markdown(f"**Address:** {patient.get('Address', 'N/A')}")
            st.markdown(f"**Marital Status:** {patient.get('Marital Status', 'N/A')}")
            st.markdown(f"**Occupation:** {patient.get('Occupation', 'N/A')}")
        st.markdown('</div>', unsafe_allow_html=True)

        # ----- VISIT HISTORY -----
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🩹 Visit History")

        visits = df[df["Full Name"] == patient["Full Name"]].sort_values(by="Date of Visit", ascending=False)
        if visits.empty:
            st.info("No visits recorded yet.")
        else:
            for _, visit in visits.iterrows():
                st.markdown('<div class="visit-card">', unsafe_allow_html=True)
                st.markdown(f"**Visit Date:** {visit.get('Date of Visit', 'N/A')}")
                st.markdown(f"**Doctor:** {visit.get(\"Doctor's Name\", 'N/A')}")
                st.markdown(f"**Chief Complaint:** {visit.get('Cheif Compliant', 'N/A')}")
                st.markdown(f"**Diagnosis:** {visit.get('Final Diagnosis', 'N/A')}")
                st.markdown(f"**Medications Prescribed:** {visit.get('Medications Prescribed', 'N/A')}")
                st.markdown(f"**Follow-Up Date:** {visit.get('Follow-Up Date', 'N/A')}")
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ----- ADD NEW VISIT -----
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("➕ Add New Visit")

        with st.form(f"add_visit_{patient_id}"):
            visit_data = {}
            for col in df.columns:
                if col in ["Timestamp", "Patient ID"]:
                    continue

                key = f"{col}_{patient_id}"

                if "Date" in col:
                    visit_data[col] = st.date_input(col, datetime.date.today(), key=key)
                elif col.lower() in ["sex", "smoking status", "alcohol use", "substance use", "marital status", "visit type"]:
                    options = ["", "Male", "Female"] if col == "Sex" else ["Yes", "No"]
                    visit_data[col] = st.selectbox(col, options, key=key)
                else:
                    visit_data[col] = st.text_input(col, key=key)

            submitted = st.form_submit_button("✅ Add Visit")

            if submitted:
                visit_data["Patient ID"] = patient_id
                sheet.append_row([visit_data.get(col, "") for col in df.columns])
                st.success(f"New visit added for {patient['Full Name']}!")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("[🏠 Back to Home](./)")

# ---------- MAIN PAGE ----------
else:
    st.subheader("🔍 Search Patients")
    search = st.text_input("Search by Full Name")

    if search:
        filtered = df[df["Full Name"].str.contains(search, case=False, na=False)]
    else:
        filtered = df

    for _, row in filtered.iterrows():
        pid = row.get("Patient ID", "unknown")
        st.markdown(f"👤 [{row['Full Name']}](?id={pid}) (Age: {row.get('Age (in years)', 'N/A')})")

    # ---------- ADD NEW PATIENT ----------
    st.subheader("➕ Add New Patient")
    with st.expander("Add Patient Form"):
        with st.form("add_patient"):
            new_patient_data = {}
            for col in df.columns:
                if col in ["Timestamp", "Patient ID"]:
                    continue

                key = f"new_{col}"

                if "Date" in col:
                    new_patient_data[col] = st.date_input(col, datetime.date.today(), key=key)
                elif col.lower() in ["sex", "smoking status", "alcohol use", "substance use", "marital status", "visit type"]:
                    options = ["", "Male", "Female"] if col == "Sex" else ["Yes", "No"]
                    new_patient_data[col] = st.selectbox(col, options, key=key)
                else:
                    new_patient_data[col] = st.text_input(col, key=key)

            submitted = st.form_submit_button("✅ Add Patient")

            if submitted:
                new_patient_data["Patient ID"] = str(uuid.uuid4())[:8]
                sheet.append_row([new_patient_data.get(col, "") for col in df.columns])
                st.success("✅ New patient added successfully!")
