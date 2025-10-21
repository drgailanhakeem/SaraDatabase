import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime

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
            body, .stApp {
                background-color: #0E1117;
                color: white;
            }
            .stTextInput, .stSelectbox, .stDateInput, .stTextArea {
                background-color: #1E1E1E !important;
                color: white !important;
            }
            .stButton>button {
                background-color: #4F8BF9 !important;
                color: white !important;
                border: none;
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

# ---------- PAGE TITLE ----------
st.title("🩺 Sara Patient Database")

# ---------- URL STATE MANAGEMENT ----------
query_params = st.query_params
patient_name = query_params.get("patient")

# ---------- PATIENT PROFILE PAGE ----------
if patient_name:
    st.header(f"👤 Patient: {patient_name}")
    patient_data = df[df["Full Name"] == patient_name]

    if not patient_data.empty:
        st.write("### Patient Details")
        st.dataframe(patient_data)

        # Add Visit Section
        st.subheader("➕ Add New Visit")
        with st.form(f"add_visit_{patient_name}"):
            visit_data = {}
            for col in df.columns:
                # Skip columns auto-filled by Google Form
                if col in ["Timestamp"]:
                    continue

                key = f"{col}_{patient_name}"

                if "Date" in col:
                    visit_data[col] = st.date_input(col, datetime.date.today(), key=key)
                elif col.lower() in ["sex", "smoking status", "alcohol use", "substance use", "marital status", "visit type"]:
                    options = ["", "Male", "Female"] if col == "Sex" else ["Yes", "No"]
                    visit_data[col] = st.selectbox(col, options, key=key)
                else:
                    visit_data[col] = st.text_input(col, key=key)

            submitted = st.form_submit_button("✅ Add Visit")

            if submitted:
                sheet.append_row([visit_data.get(col, "") for col in df.columns])
                st.success(f"New visit added for {patient_name}!")

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
        name = row["Full Name"]
        st.markdown(f"👤 [{name}](?patient={name}) (Age: {row.get('Age (in years)', 'N/A')})")

    # ---------- ADD NEW PATIENT ----------
    st.subheader("➕ Add New Patient")
    with st.expander("Add Patient Form"):
        with st.form("add_patient"):
            new_patient_data = {}
            for col in df.columns:
                if col in ["Timestamp"]:
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
                sheet.append_row([new_patient_data.get(col, "") for col in df.columns])
                st.success("✅ New patient added successfully!")
