import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ================== GOOGLE SHEETS CONNECTION ==================
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

st.set_page_config(page_title="Sara Patient Database", page_icon="🏥", layout="wide")

try:
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
    client = gspread.authorize(creds)

    # Open spreadsheet
    spreadsheet = client.open("SaraDatabase")
    sheet_names = [ws.title for ws in spreadsheet.worksheets()]

    if "Responses" not in sheet_names or "Visits" not in sheet_names:
        st.error(f"❌ 'Responses' or 'Visits' worksheet not found. Found: {sheet_names}")
        st.stop()

    sheet_responses = spreadsheet.worksheet("Responses")
    sheet_visits = spreadsheet.worksheet("Visits")

    responses_data = sheet_responses.get_all_records()
    visits_data = sheet_visits.get_all_records()

    patients_df = pd.DataFrame(responses_data)
    visits_df = pd.DataFrame(visits_data)

    # --- Normalize column names to prevent KeyErrors ---
    patients_df.columns = patients_df.columns.str.strip()
    visits_df.columns = visits_df.columns.str.strip()

    if patients_df.empty:
        st.warning("⚠️ The 'Responses' sheet is empty.")
    else:
        st.success("✅ Connected to Google Sheets successfully.")

except Exception as e:
    st.error(f"❌ Failed to load sheets: {e}")
    st.stop()

# ================== MAIN APP ==================
st.title("🏥 Sara Patient Database")

# Toggle for adding new patient
show_add_form = st.checkbox("➕ Add New Patient")

if show_add_form:
    st.subheader("Add New Patient")

    with st.form("add_patient_form"):
        full_name = st.text_input("Full Name")
        dob = st.date_input("Date of Birth")
        age = st.number_input("Age (in years)", min_value=0)
        sex = st.selectbox("Sex", ["Male", "Female"])
        address = st.text_input("Address")
        doctor_name = st.text_input("Doctor's Name")
        patient_id = st.text_input("Patient ID")

        submitted = st.form_submit_button("Save Patient")

        if submitted:
            try:
                new_row = [
                    pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
                    full_name,
                    str(dob),
                    age,
                    sex,
                    address,
                    "", "",  # Date/Time of Visit (empty)
                    doctor_name,
                    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
                    patient_id
                ]
                sheet_responses.append_row(new_row)
                st.success(f"✅ Added new patient: {full_name}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error adding patient: {e}")

# ================== PATIENT SEARCH ==================
st.subheader("🔍 Search Patient by Name or ID")
search = st.text_input("Search...").strip().lower()

if not patients_df.empty:
    filtered = (
        patients_df[
            patients_df.apply(
                lambda row: search in str(row.get("Full Name", "")).lower()
                or search in str(row.get("Patient ID", "")).lower(),
                axis=1,
            )
        ]
        if search
        else patients_df
    )

    for _, row in filtered.iterrows():
        with st.expander(f"👤 {row['Full Name']} ({row['Patient ID']})", expanded=False):
            st.markdown("### 🧾 Patient Details")
            for col, val in row.items():
                st.markdown(f"**{col}:** {val}")

            # --- Visits section ---
            if "Patient ID" in visits_df.columns:
                patient_visits = visits_df[visits_df["Patient ID"] == row["Patient ID"]]
            else:
                st.error("❌ 'Patient ID' column missing in Visits sheet.")
                patient_visits = pd.DataFrame()

            if not patient_visits.empty:
                st.markdown("### 🩺 Visits")
                sorted_visits = patient_visits.sort_values("Date of Visit", ascending=False)
                for _, visit in sorted_visits.iterrows():
                    with st.expander(f"📅 {visit['Date of Visit']} - {visit.get('Visit Type', 'Visit')}"):
                        for vcol, vval in visit.items():
                            st.markdown(f"**{vcol}:** {vval}")
            else:
                st.info("No visits recorded.")

            # --- Action buttons ---
            st.write("---")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("➕ Add Visit", key=f"add_visit_{row['Patient ID']}"):
                    st.session_state["selected_patient"] = row["Patient ID"]
                    st.session_state["show_add_visit_form"] = True
                    st.rerun()

            with col2:
                if st.button("🗑️ Delete Patient", key=f"delete_{row['Patient ID']}"):
                    try:
                        index_to_delete = patients_df[patients_df["Patient ID"] == row["Patient ID"]].index[0]
                        sheet_responses.delete_rows(index_to_delete + 2)  # +2 accounts for header row
                        st.success(f"✅ Deleted patient: {row['Full Name']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error deleting patient: {e}")
