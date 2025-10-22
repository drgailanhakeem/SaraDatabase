import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date, time

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="Sara Patient Database", layout="wide")

# -------------------------
# Dark mode toggle (kept)
# -------------------------
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

# -------------------------
# Authenticate
# -------------------------
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(st.secrets["sheet"]["sheet_name"])

    # Ensure Visits sheet exists (create if not)
    visits_sheet_name = "Visits"
    try:
        visits_sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(visits_sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws_book = client.open_by_key(st.secrets["sheet"]["sheet_id"])
        visits_sheet = ws_book.add_worksheet(title=visits_sheet_name, rows="100", cols="20")
        visits_sheet.append_row(["Visit ID", "Patient ID", "Visit Date", "Doctor's Name", "Notes"])

    st.success("✅ Successfully connected to Google Sheet")
except Exception as e:
    st.error(f"❌ Google Sheets Connection Failed: {e}")
    st.stop()

# -------------------------
# Load cached data helper (minimize API calls)
# -------------------------
@st.cache_data(ttl=120)
def load_main_and_visits():
    main = pd.DataFrame(sheet.get_all_records())
    visits = pd.DataFrame(visits_sheet.get_all_records())
    return main, visits

try:
    df, visits_df = load_main_and_visits()
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.stop()

# -------------------------
# Utility: delete patient rows robustly
# -------------------------
def delete_patient(patient_id=None, full_name=None):
    """
    Deletes rows from main sheet and visits sheet matching patient_id (preferred) or full_name.
    Returns (deleted_main_rows_count, deleted_visits_rows_count)
    """
    deleted_main = 0
    deleted_visits = 0

    # --- Delete from main sheet ---
    # Get fresh snapshot of main sheet records
    main_rows = sheet.get_all_records()  # list of dicts
    # Collect sheet row numbers to delete (sheet rows are 1-indexed and row 1 is header)
    rows_to_delete = []
    for idx, row in enumerate(main_rows, start=2):  # start=2 because dict list excludes header
        try:
            if patient_id and "Patient ID" in row and str(row.get("Patient ID")) == str(patient_id):
                rows_to_delete.append(idx)
            elif (not patient_id) and full_name and str(row.get("Full Name", "")).strip() == str(full_name).strip():
                rows_to_delete.append(idx)
            elif patient_id and "Patient ID" not in row and full_name and str(row.get("Full Name", "")).strip() == str(full_name).strip():
                # fallback if no Patient ID column
                rows_to_delete.append(idx)
        except Exception:
            continue

    # Delete main rows in reverse order
    for r in sorted(rows_to_delete, reverse=True):
        try:
            sheet.delete_rows(r)
            deleted_main += 1
        except Exception:
            # continue on errors, but try to proceed
            continue

    # --- Delete from visits sheet ---
    visits_rows = visits_sheet.get_all_records()
    rows_to_delete_v = []
    for idx, row in enumerate(visits_rows, start=2):
        try:
            if patient_id and "Patient ID" in row and str(row.get("Patient ID")) == str(patient_id):
                rows_to_delete_v.append(idx)
            elif (not patient_id) and full_name and str(row.get("Patient ID", "")).strip() == str(full_name).strip():
                rows_to_delete_v.append(idx)
        except Exception:
            continue

    for r in sorted(rows_to_delete_v, reverse=True):
        try:
            visits_sheet.delete_rows(r)
            deleted_visits += 1
        except Exception:
            continue

    # Clear cached data so app reloads fresh
    st.cache_data.clear()
    return deleted_main, deleted_visits

# -------------------------
# UI: Title and search
# -------------------------
st.title("🩺 Sara Patient Database")
st.subheader("🔍 Search Patients")
search_query = st.text_input("Search by Full Name").strip().lower()

filtered_df = df[df["Full Name"].str.lower().str.contains(search_query)] if (search_query and not df.empty) else df

# -------------------------
# Display patients with delete
# -------------------------
if not filtered_df.empty:
    for i, row in filtered_df.iterrows():
        # Determine patient id (prefer "Patient ID" column if present)
        patient_id = row.get("Patient ID", f"pt{i+1}")
        full_name = row.get("Full Name", "")

        with st.expander(f"👤 {full_name} (ID: {patient_id})"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Patient ID:** {patient_id}")
                st.markdown(f"**Sex:** {row.get('Sex', '')}")
                st.markdown(f"**Address:** {row.get('Address', '')}")
                st.markdown(f"**Date of Birth:** {row.get('Date of Birth', '')}")
            with col2:
                st.markdown(f"**Date of Visit:** {row.get('Date of Visit', '')}")
                st.markdown(f"**Doctor's Name:** {row.get(\"Doctor's Name\", '')}")
                st.markdown(f"**Chief Complaint:** {row.get('Cheif Compliant', '')}")
                st.markdown(f"**Final Diagnosis:** {row.get('Final Diagnosis', '')}")
            st.markdown("---")
            # First click shows confirm; second click performs deletion
            if 'delete_clicked' not in st.session_state:
                st.session_state['delete_clicked'] = {}

            delete_key = f"delete_{i}"
            confirm_key = f"confirm_delete_{i}"

            if not st.session_state['delete_clicked'].get(delete_key, False):
                if st.button("🗑️ Delete Patient", key=delete_key):
                    st.session_state['delete_clicked'][delete_key] = True
                    st.experimental_rerun()
            else:
                st.warning(f"⚠️ Confirm: permanently delete all records for **{full_name}** (Patient ID: {patient_id})")
                if st.button("✅ Confirm Delete", key=confirm_key):
                    deleted_main, deleted_visits = delete_patient(patient_id=patient_id, full_name=full_name)
                    st.success(f"✅ Deleted {deleted_main} row(s) from main sheet and {deleted_visits} row(s) from Visits.")
                    # reset flag
                    st.session_state['delete_clicked'][delete_key] = False
                    st.experimental_rerun()
                if st.button("✖ Cancel", key=f"cancel_{i}"):
                    st.session_state['delete_clicked'][delete_key] = False
                    st.experimental_rerun()
else:
    st.info("No patients found.")

# -------------------------
# Add new patient (keeps same behavior you had)
# -------------------------
with st.expander("➕ Add New Patient"):
    st.write("Fill in the patient details below:")
    new_data = {}
    columns = list(df.columns)

    # Auto-generate unique ID (pt1, pt2...)
    if "Patient ID" in df.columns and not df.empty:
        next_n = len(df) + 1
        new_data["Patient ID"] = f"pt{next_n}"
    else:
        new_data["Patient ID"] = "pt1"

    for i, col in enumerate(columns):
        if col == "Patient ID":
            continue  # skip, already set
        key = f"patient_{i}"
        if col.lower() in ["timestamp"]:
            new_data[col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif "date of birth" in col.lower():
            new_data[col] = st.date_input(col, min_value=date(1900, 1, 1), max_value=date.today(), key=key)
        elif "time of visit" in col.lower():
            new_data[col] = st.time_input(col, key=key).strftime("%H:%M:%S")
        elif "duration" in col.lower():
            new_data[col] = st.text_input(col, placeholder="e.g., 2 weeks, 3 months", key=key)
        elif "past medical history" in col.lower():
            new_data[col] = st.selectbox(col, ["None", "Hypertension", "Diabetes", "Asthma", "Other"], key=key)
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
            # Convert date/time objects to strings where needed
            for k, v in new_data.items():
                if isinstance(v, (datetime, date, time)):
                    new_data[k] = v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else (v.strftime("%Y-%m-%d") if isinstance(v, date) else v.strftime("%H:%M:%S"))
            sheet.append_row(list(new_data.values()))
            st.success(f"✅ New patient {new_data.get('Full Name', '')} added successfully!")
            st.cache_data.clear()
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Error adding patient: {e}")

# -------------------------
# Add new visit (kept similar to yours)
# -------------------------
with st.expander("🩹 Add New Visit"):
    st.write("Fill in visit details for an existing patient:")
    visit_data = {}
    # If visits_df has columns, use them; otherwise provide defaults
    vcols = list(visits_df.columns) if not visits_df.empty else ["Visit ID", "Patient ID", "Visit Date", "Doctor's Name", "Notes"]

    # generate visit id
    if ("Visit ID" in visits_df.columns) and (not visits_df.empty):
        last_nums = [int(str(x).replace("vt", "")) for x in visits_df["Visit ID"].astype(str) if str(x).startswith("vt")]
        next_visit = f"vt{max(last_nums)+1:03d}" if last_nums else "vt001"
    else:
        next_visit = "vt001"
    visit_data["Visit ID"] = next_visit

    # select patient
    patient_names = df["Full Name"].tolist() if not df.empty else []
    selected_patient = st.selectbox("Select Patient", patient_names)
    if selected_patient:
        pid_val = df.loc[df["Full Name"] == selected_patient, "Patient ID"].values[0] if "Patient ID" in df.columns else selected_patient
        visit_data["Patient ID"] = pid_val

    for col in vcols:
        if col in ["Visit ID", "Patient ID", "Timestamp"]:
            continue
        key = f"visit_{col.replace(' ', '_')}"
        if "date" in col.lower():
            visit_data[col] = st.date_input(col, key=key)
        elif "time" in col.lower():
            visit_data[col] = st.time_input(col, key=key).strftime("%H:%M:%S")
        else:
            visit_data[col] = st.text_input(col, key=key)

    if st.button("💾 Add Visit"):
        try:
            # Convert any date object to string
            for k, v in visit_data.items():
                if isinstance(v, (datetime, date, time)):
                    visit_data[k] = v.strftime("%Y-%m-%d") if isinstance(v, date) else v.strftime("%H:%M:%S")
            # ensure same column order as visits_sheet header
            header = visits_sheet.row_values(1)
            row_to_append = [visit_data.get(h, "") for h in header]
            visits_sheet.append_row(row_to_append)
            st.success("✅ New visit added successfully!")
            st.cache_data.clear()
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Error adding visit: {e}")
