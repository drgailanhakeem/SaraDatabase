import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from urllib.parse import quote, unquote
from datetime import date

# --- Streamlit Page Config ---
st.set_page_config(page_title="Patient Database", layout="wide")
st.title("🩺 Patient Database")

# --- Connect to Google Sheets ---
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(credentials)

sheet_id = st.secrets["sheet"]["sheet_id"]
sheet_name = st.secrets["sheet"]["sheet_name"]
sheet = client.open_by_key(sheet_id).worksheet(sheet_name)

# --- Load data ---
df = pd.DataFrame(sheet.get_all_records())

# --- Get query parameter ---
query_params = st.query_params
selected_patient = query_params.get("patient", [None])[0]

# --- Helper: generate patient link ---
BASE_URL = "https://saradatabase.streamlit.app/"  # change if your domain differs
def get_patient_link(name):
    encoded_name = quote(name)
    return f"{BASE_URL}?patient={encoded_name}"

# --- Patient View ---
if selected_patient:
    selected_patient = unquote(selected_patient)
    st.markdown(f"### 🧍 Patient: {selected_patient}")

    # Filter data for this patient
    patient_data = df[df["Full Name"].str.strip().str.lower() == selected_patient.strip().lower()]

    if not patient_data.empty:
        # --- Display cards instead of table ---
        st.write("")
        st.markdown("#### 📋 Patient Visits")

        for i, row in patient_data.iterrows():
            with st.container():
                st.markdown(f"""
                <div style="padding:15px; margin-bottom:10px; border-radius:10px; background-color:#f9f9f9; box-shadow:0 2px 5px rgba(0,0,0,0.1)">
                    <b>Visit Date:</b> {row.get('Visit Date', 'N/A')}<br>
                    <b>Age:</b> {row.get('Age (Years)', 'N/A')}<br>
                    <b>Gender:</b> {row.get('Gender', 'N/A')}<br>
                    <b>Weight:</b> {row.get('Weight (kg)', 'N/A')} kg<br>
                    <b>Duration of Diabetes:</b> {row.get('Duration Of Diabetes Mellitus', 'N/A')} years<br>
                    <b>Medications:</b> 
                        {"Su" if row.get("Su") else ""} 
                        {"Met" if row.get("Met") else ""} 
                        {"DPP-4" if row.get("DPP-4") else ""} 
                        {"GLP-1" if row.get("GLP-1") else ""} 
                        {"SGLT2" if row.get("SGLT2") else ""}<br>
                    <b>Other:</b> {row.get('Other', '')}<br>
                    <b>Remarks:</b> {row.get('Remarks', '')}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("No records found for this patient.")

    st.markdown("---")
    st.markdown("### ➕ Add New Visit")

    # --- Add Visit Form ---
    with st.form("add_visit"):
        col1, col2 = st.columns(2)

        with col1:
            visit_date = st.date_input("Visit Date", value=date.today())
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            age = st.number_input("Age (Years)", min_value=0, max_value=120, step=1)
            weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
            duration = st.number_input("Duration Of Diabetes Mellitus (Years)", min_value=0, max_value=50, step=1)
        with col2:
            su = st.checkbox("Sulfonylurea (Su)")
            met = st.checkbox("Metformin (Met)")
            dpp4 = st.checkbox("DPP-4 Inhibitor")
            glp1 = st.checkbox("GLP-1 Agonist")
            sglt2 = st.checkbox("SGLT2 Inhibitor")
            other = st.text_input("Other Medications")

        remarks = st.text_area("Remarks")

        submitted = st.form_submit_button("Add Visit")

        if submitted:
            new_row = [
                selected_patient,
                str(visit_date),
                gender,
                age,
                weight,
                duration,
                "Yes" if su else "",
                "Yes" if met else "",
                "Yes" if dpp4 else "",
                "Yes" if glp1 else "",
                "Yes" if sglt2 else "",
                other,
                remarks,
            ]
            sheet.append_row(new_row)
            st.success("✅ Visit added successfully!")
            st.rerun()

# --- All Patients View ---
else:
    st.markdown("### 🧾 All Patients")

    # Search Bar
    search_query = st.text_input("Search by patient name").strip().lower()
    filtered_df = df[df["Full Name"].str.lower().str.contains(search_query)] if search_query else df

    for patient in sorted(filtered_df["Full Name"].dropna().unique()):
        link = get_patient_link(patient)
        with st.container():
            st.markdown(f"""
            <div style="padding:10px; margin-bottom:5px; border-radius:10px; background-color:#f7f9fa;">
                <b>{patient}</b> — <a href="{link}" target="_self">View Record</a>
            </div>
            """, unsafe_allow_html=True)
