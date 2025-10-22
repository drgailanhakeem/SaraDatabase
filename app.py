import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import uuid
from datetime import datetime

# --- GOOGLE SHEETS CONNECTION ---
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

# --- MAIN SHEETS ---
main_sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(st.secrets["sheet"]["sheet_name"])
visits_sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet("Visits")

# --- LOAD DATA ---
df = pd.DataFrame(main_sheet.get_all_records())
visits_df = pd.DataFrame(visits_sheet.get_all_records())

# --- HELPERS ---
def generate_patient_id():
    return f"pt_{uuid.uuid4().hex[:6]}"

def get_patient_by_id(patient_id):
    if "Patient ID" in df.columns:
        return df[df["Patient ID"] == patient_id]
    return pd.DataFrame()

def get_visits_for_patient(patient_id):
    if "Patient ID" in visits_df.columns:
        patient_visits = visits_df[visits_df["Patient ID"] == patient_id]
        if "Date of Visit" in patient_visits.columns:
            patient_visits["Date of Visit"] = pd.to_datetime(patient_visits["Date of Visit"], errors="coerce")
            patient_visits = patient_visits.sort_values("Date of Visit", ascending=False)
        return patient_visits
    return pd.DataFrame()

# --- APP TITLE ---
st.set_page_config(page_title="Sara Patient Database", layout="wide")
st.title("🩺 Sara Patient Database")

# --- QUERY PARAM ---
params = st.query_params
patient_id = params.get("id", [None])[0] if isinstance(params.get("id"), list) else params.get("id")

# ========================= PATIENT PROFILE PAGE =========================
if patient_id:
    patient = get_patient_by_id(patient_id)
    if patient.empty:
        st.error("❌ Patient not found.")
        st.stop()

    patient = patient.iloc[0]
    st.header(f"{patient.get('Full Name', 'Unknown')} (ID: {patient_id})")

    # --- DISPLAY ALL PATIENT INFO ---
    st.subheader("📋 Patient Information")
    cols = st.columns(2)
    for i, (col_name, value) in enumerate(patient.items()):
        if pd.isna(value) or str(value).strip() == "":
            continue
        with cols[i % 2]:
            st.markdown(f"**{col_name}:** {value}")

    st.divider()

    # --- DELETE PATIENT BUTTON ---
    if st.button("🗑️ Delete Patient", key=f"delete_{patient_id}"):
        try:
            row_index = df.index[df["Patient ID"] == patient_id][0] + 2
            main_sheet.delete_rows(row_index)
            st.success(f"✅ Deleted {patient.get('Full Name', 'patient')}")
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error deleting patient: {e}")

    # --- ADD VISIT EXPANDER ---
    st.divider()
    with st.expander("➕ Add New Visit"):
        st.subheader("Add Visit for this Patient")
        visit_data = {}
        for col in df.columns:
            if col.lower() in ["timestamp", "patient id"]:
                continue
            key = f"visit_{col}_{patient_id}"
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
                visit_data[col] = st.selectbox(
                    col, ["None", "Diabetes", "Hypertension", "Cardiac Disease", "Asthma", "Other"], key=key
                )
            else:
                visit_data[col] = st.text_input(col, key=key)

        if st.button("💾 Save Visit", key=f"save_visit_{patient_id}"):
            try:
                visit_data["Patient ID"] = patient_id
                visit_data = {k: str(v) for k, v in visit_data.items()}
                visits_sheet.append_row(list(visit_data.values()))
                st.success("✅ Visit added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error adding visit: {e}")

    # --- DISPLAY VISIT HISTORY ---
    st.divider()
    st.subheader("📅 Visit History")

    patient_visits = get_visits_for_patient(patient_id)
    if not patient_visits.empty:
        for i, (_, visit) in enumerate(patient_visits.iterrows()):
            date_str = str(visit.get("Date of Visit", "Unknown"))[:10]
            with st.expander(f"🩺 Visit on {date_str}", expanded=False):
                cols = st.columns(2)
                for j, (col_name, value) in enumerate(visit.items()):
                    if pd.isna(value) or str(value).strip() == "":
                        continue
                    with cols[j % 2]:
                        st.markdown(f"**{col_name}:** {value}")
    else:
        st.info("No visits recorded yet for this patient.")

    st.divider()
    st.markdown("[⬅ Back to Home](?)")

# ========================= HOMEPAGE =========================
else:
    st.subheader("🔍 Search Patients")
    search_query = st.text_input("Search by Full Name")

    if search_query:
        filtered_df = df[df["Full Name"].str.contains(search_query, case=False, na=False)]
    else:
        filtered_df = df

    if not filtered_df.empty:
        for _, row in filtered_df.iterrows():
            patient_link = f"?id={row['Patient ID']}"
            st.markdown(f"👤 [{row['Full Name']} (Age: {row.get('Age', 'N/A')})]({patient_link})")
    else:
        st.info("No patients found.")

    st.divider()

    # --- ADD NEW PATIENT ---
    with st.expander("➕ Add New Patient"):
        st.subheader("Add New Patient")
        new_data = {}
        for col in df.columns:
            if col.lower() in ["timestamp", "patient id"]:
                continue
            key = f"new_{col}"
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
                new_data[col] = st.selectbox(
                    col, ["None", "Diabetes", "Hypertension", "Cardiac Disease", "Asthma", "Other"], key=key
                )
            else:
                new_data[col] = st.text_input(col, key=key)

        if st.button("💾 Save New Patient", key="save_new_patient"):
            try:
                new_data["Patient ID"] = generate_patient_id()
                new_data = {k: str(v) for k, v in new_data.items()}
                main_sheet.append_row(list(new_data.values()))
                st.success(f"✅ New patient added successfully! (ID: {new_data['Patient ID']})")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error adding patient: {e}")
