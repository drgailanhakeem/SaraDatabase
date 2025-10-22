import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date

# ===============================
# STREAMLIT PAGE SETUP
# ===============================
st.set_page_config(page_title="Sara Patient Database", layout="wide")
st.title("🩺 Sara Patient Database")

# ===============================
# DARK MODE TOGGLE
# ===============================
dark_mode = st.toggle("🌙 Dark Mode", value=False)
if dark_mode:
    st.markdown("""
        <style>
        body, .stApp, .stDataFrame, .stSelectbox, .stTextInput, .stDateInput, .stTextArea, .stButton {
            background-color: #1E1E1E !important;
            color: white !important;
        }
        .stMarkdown, .stSubheader, .stHeader, .stDataFrame th, .stDataFrame td {
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

# ===============================
# GOOGLE SHEETS CONNECTION
# ===============================
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)

    SHEET_PATIENTS = "Responses"
    SHEET_VISITS = "Visits"

    sheet_patients = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(SHEET_PATIENTS)
    sheet_visits = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(SHEET_VISITS)

    st.success("✅ Connected to Google Sheets successfully")
except Exception as e:
    st.error(f"❌ Google Sheets connection failed: {e}")
    st.stop()

# ===============================
# LOAD DATA
# ===============================
def load_data(sheet):
    try:
        records = sheet.get_all_records()
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"❌ Failed to load sheet data: {e}")
        return pd.DataFrame()

df_patients = load_data(sheet_patients)
df_visits = load_data(sheet_visits)
patients_df = df_patients
visits_df = df_visits

# Assign unique patient IDs if missing
if "Patient ID" not in patients_df.columns:
    patients_df["Patient ID"] = [f"pt{i+1}" for i in range(len(patients_df))]

# ===============================
# SEARCH PATIENTS
# ===============================
st.subheader("🔍 Search Patients")
search = st.text_input("Search by Full Name").strip().lower()

filtered = patients_df[
    patients_df["Full Name"].str.lower().str.contains(search)
] if search else patients_df

# ===============================
# DETECT CURRENT BASE URL
# ===============================
# This ensures links are absolute for sharing
try:
    base_url = st.secrets["app_base_url"]
except KeyError:
    base_url = st.request.url.split("?")[0] if hasattr(st, "request") else "https://your-app-name.streamlit.app"

# ===============================
# PATIENT VIEW PAGE
# ===============================
query_params = st.query_params
patient_id = query_params.get("id", [None])[0] if "id" in query_params else None

if patient_id:
    patient = patients_df[patients_df["Patient ID"] == patient_id]
    if patient.empty:
        st.error("❌ Patient not found.")
        st.stop()
    row = patient.iloc[0]
    st.header(f"👤 {row['Full Name']} (ID: {row['Patient ID']})")

    # Show all patient info dynamically
    st.subheader("🧾 Patient Details")
    for col, val in row.items():
        st.markdown(f"**{col}:** {val}")

    # Visits
    st.subheader("🩹 Visits")
    visits = visits_df[visits_df["Patient ID"] == patient_id]
    if not visits.empty:
        # Sort by Date if possible
        if "Date of Visit" in visits.columns:
            visits = visits.sort_values(by="Date of Visit", ascending=False)
        for i, (_, v) in enumerate(visits.iterrows()):
            with st.expander(f"📅 Visit on {v.get('Date of Visit', 'Unknown')}"):
                for c, val in v.items():
                    st.markdown(f"**{c}:** {val}")
    else:
        st.info("No visits found.")

    # --- Add Visit ---
    st.subheader("➕ Add Visit")
    with st.form(f"add_visit_{patient_id}"):
        visit_data = {}
        for col in visits_df.columns:
            if col == "Patient ID":
                visit_data[col] = patient_id
            elif "date" in col.lower():
                visit_data[col] = st.date_input(col, key=f"visit_{col}_{patient_id}")
            else:
                visit_data[col] = st.text_input(col, key=f"visit_{col}_{patient_id}")
        if st.form_submit_button("💾 Save Visit"):
            try:
                visit_data = {k: str(v) if isinstance(v, (datetime, date)) else v for k, v in visit_data.items()}
                sheet_visits.append_row(list(visit_data.values()))
                st.success("✅ Visit added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding visit: {e}")

    # --- Delete Patient ---
    st.subheader("🗑️ Danger Zone")
    delete_key = f"delete_{patient_id}"
    if st.button("🗑️ Delete Patient", key=delete_key):
        try:
            # Delete from patients sheet
            all_values = sheet_patients.get_all_values()
            headers = all_values[0]
            patient_id_col = headers.index("Patient ID")
            for i, row_vals in enumerate(all_values[1:], start=2):
                if row_vals[patient_id_col] == patient_id:
                    sheet_patients.delete_rows(i)
                    break

            # Delete visits
            all_visits = sheet_visits.get_all_values()
            v_headers = all_visits[0]
            visit_pid_col = v_headers.index("Patient ID")
            rows_to_delete = [i for i, r in enumerate(all_visits[1:], start=2) if r[visit_pid_col] == patient_id]
            for i in reversed(rows_to_delete):
                sheet_visits.delete_rows(i)

            st.success("✅ Patient and all visits deleted.")
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error deleting patient: {e}")

    st.stop()

# ===============================
# MAIN PATIENT LIST
# ===============================
if not filtered.empty:
    for _, row in filtered.iterrows():
        pid = row["Patient ID"]
        patient_url = f"{base_url}?id={pid}"
        with st.expander(f"👤 [{row['Full Name']}]({patient_url})", expanded=False):
            for col, val in row.items():
                st.markdown(f"**{col}:** {val}")
else:
    st.info("No patients found.")

# ===============================
# ADD NEW PATIENT
# ===============================
st.subheader("➕ Add New Patient")
with st.form("add_new_patient"):
    new_data = {}
    for col in patients_df.columns:
        if col == "Patient ID":
            new_data[col] = f"pt{len(patients_df)+1}"
        elif "date" in col.lower():
            new_data[col] = st.date_input(col, key=f"new_{col}")
        elif "time" in col.lower():
            new_data[col] = st.time_input(col, key=f"new_{col}")
        else:
            new_data[col] = st.text_input(col, key=f"new_{col}")
    if st.form_submit_button("✅ Add Patient"):
        try:
            new_data = {k: str(v) if isinstance(v, (datetime, date)) else v for k, v in new_data.items()}
            sheet_patients.append_row(list(new_data.values()))
            st.success("New patient added successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error adding patient: {e}")
