# app.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="Inpatient System — Streamlit EMR", layout="wide", page_icon="🩺")

# EDIT THIS: put your Google Sheet ID here (the long id from the URL)
SHEET_ID = "1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"

# Tabs names in your Google Sheet
TAB_PATIENTS = "Patients"
TAB_VISITS = "Visits"
TAB_DISCHARGES = "Discharges"

# Expected headers — descriptive (doctor-oriented)
PATIENTS_HEADERS = [
    "Timestamp", "Patient ID", "Full Name", "Date of Birth", "Age (in years)", "Sex",
    "Ward / Bed Number", "Date of Admission", "Chief Complaint", "Duration of Complaint",
    "Onset & Course", "History of Present Illness", "Associated Symptoms", "Relevant Negatives",
    "Past Medical History", "Past Surgical History", "Drug History / Allergies", "Family History",
    "Social History", "General Examination", "Vital Signs", "Anthropometry (Height, Weight, BMI)",
    "Physical Examination Findings", "Investigations Ordered", "Preliminary Results",
    "Provisional Diagnosis", "Differential Diagnosis", "Initial Management Plan", "Attending Physician",
    "Notes / Remarks"
]

VISITS_HEADERS = [
    "Timestamp", "Visit ID", "Patient ID", "Full Name", "Date of Visit", "Time of Visit",
    "Ward / Bed Number", "Doctor / Submitter", "Subjective (S)", "Objective (O)",
    "Assessment (A)", "Plan (P)", "Vital Signs", "Investigations Ordered", "Investigations Results",
    "Changes in Medications", "Medications Given", "Non-Pharmacologic Advice", "Follow-Up Date", "Notes"
]

DISCHARGE_HEADERS = [
    "Timestamp", "Discharge ID", "Patient ID", "Full Name", "Date of Admission", "Date of Discharge",
    "Duration of Stay", "Admitting Diagnosis", "Final Diagnosis", "Comorbidities",
    "Major Interventions / Procedures", "Key Investigations & Results", "Hospital Course Summary",
    "Condition at Discharge", "Discharge Medications", "Non-Pharmacologic Advice", "Follow-Up Plan",
    "Attending Physician", "Remarks"
]

# -----------------------
# HELPERS: Google Sheets connection
# -----------------------
def connect_client():
    """
    Connect to Google using service account info stored in st.secrets["gcp_service_account"].
    Returns: gspread client
    """
    info = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def open_sheet_tab(client, sheet_id, tab_name):
    """
    Open a worksheet by name. If it doesn't exist, create it.
    Returns the gspread Worksheet object.
    """
    ss = client.open_by_key(sheet_id)
    try:
        ws = ss.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        # create worksheet with default 100 rows and columns
        ws = ss.add_worksheet(title=tab_name, rows="100", cols="40")
    return ws

def ensure_headers(ws, headers):
    """
    Ensure the first row contains the expected headers.
    If the sheet is empty, write the headers.
    If the first row is different but sheet is empty (no data rows), replace with headers.
    We will not overwrite user data if sheet already has data.
    """
    try:
        first_row = ws.row_values(1)
    except Exception:
        first_row = []
    if not first_row:
        ws.append_row(headers, value_input_option="RAW")
        # small pause for API consistency
        time.sleep(0.2)
    else:
        # If the existing first row is not a superset of required headers and sheet has only header row (no records), replace
        records = ws.get_all_records()
        if not records and first_row != headers:
            # replace first row with our headers
            ws.delete_row(1)
            ws.insert_row(headers, index=1)
            time.sleep(0.2)
    return

# -----------------------
# INITIALIZE GOOGLE SHEETS (not cached since worksheets are not hashable)
# -----------------------
try:
    client = connect_client()
    ws_patients = open_sheet_tab(client, SHEET_ID, TAB_PATIENTS)
    ws_visits = open_sheet_tab(client, SHEET_ID, TAB_VISITS)
    ws_discharges = open_sheet_tab(client, SHEET_ID, TAB_DISCHARGES)

    ensure_headers(ws_patients, PATIENTS_HEADERS)
    ensure_headers(ws_visits, VISITS_HEADERS)
    ensure_headers(ws_discharges, DISCHARGE_HEADERS)
except Exception as e:
    st.error("❌ Failed to connect to Google Sheets. Check st.secrets and sheet ID.")
    st.exception(e)
    st.stop()

# -----------------------
# UTIL: load sheets as dataframes
# -----------------------
@st.cache_data(ttl=60)
def load_dataframe_from_ws(ws):
    """
    Load worksheet into DataFrame. Uses sheet.get_all_records().
    """
    try:
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        # strip column names
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

patients_df = load_dataframe_from_ws(ws_patients)
visits_df = load_dataframe_from_ws(ws_visits)
discharges_df = load_dataframe_from_ws(ws_discharges)

# -----------------------
# UTIL: ID generators
# -----------------------
def generate_patient_id(df):
    # P-0001 style
    existing = df.get("Patient ID", pd.Series(dtype=str)).dropna().astype(str)
    nums = []
    for v in existing:
        if isinstance(v, str) and v.startswith("P-"):
            try:
                nums.append(int(v.split("-")[1]))
            except:
                pass
    nxt = max(nums)+1 if nums else 1
    return f"P-{nxt:04d}"

def generate_visit_id(df):
    existing = df.get("Visit ID", pd.Series(dtype=str)).dropna().astype(str)
    nums = []
    for v in existing:
        if isinstance(v, str) and v.startswith("V-"):
            try:
                nums.append(int(v.split("-")[1]))
            except:
                pass
    nxt = max(nums)+1 if nums else 1
    return f"V-{nxt:05d}"

def generate_discharge_id(df):
    existing = df.get("Discharge ID", pd.Series(dtype=str)).dropna().astype(str)
    nums = []
    for v in existing:
        if isinstance(v, str) and v.startswith("D-"):
            try:
                nums.append(int(v.split("-")[1]))
            except:
                pass
    nxt = max(nums)+1 if nums else 1
    return f"D-{nxt:05d}"

# -----------------------
# UI: header and layout
# -----------------------
st.title("🩺 Inpatient EMR — Streamlit")
st.caption("Admissions, daily progress, and discharge notes — in-app forms and timeline view")

# Sidebar actions
with st.sidebar:
    st.header("Actions")
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.experimental_rerun()
    st.markdown("---")
    # Downloads
    if not patients_df.empty:
        st.download_button("⬇️ Download Patients CSV", patients_df.to_csv(index=False), "patients.csv", mime="text/csv")
    if not visits_df.empty:
        st.download_button("⬇️ Download Visits CSV", visits_df.to_csv(index=False), "visits.csv", mime="text/csv")
    if not discharges_df.empty:
        st.download_button("⬇️ Download Discharges CSV", discharges_df.to_csv(index=False), "discharges.csv", mime="text/csv")
    st.markdown("---")
    st.info("Note: Data is stored in your Google Sheet. Make backups regularly.")

# -----------------------
# Homepage: patient list + add new patient form
# -----------------------
st.subheader("Patient Registry")
col1, col2 = st.columns([3, 1])

# Search box
search = col2.text_input("🔍 Search", placeholder="name / id / diagnosis")

# New patient form (collapsible)
with st.expander("➕ Add New Patient (Admission)", expanded=False):
    with st.form("add_patient_form"):
        # Pre-generate patient id
        new_pid = generate_patient_id(patients_df)
        full_name = st.text_input("Full Name")
        dob = st.date_input("Date of Birth", value=None)
        age = st.number_input("Age (years)", min_value=0, max_value=150, value=0)
        sex = st.selectbox("Sex", options=["Male", "Female", "Other"])
        ward_bed = st.text_input("Ward / Bed Number")
        date_adm = st.date_input("Date of Admission", value=datetime.today())
        chief = st.text_input("Chief Complaint")
        hpi = st.text_area("History of Present Illness (brief)")
        pmh = st.text_area("Past Medical History")
        allergies = st.text_input("Drug History / Allergies")
        vitals = st.text_input("Vital Signs (e.g. T36.8 HR76 BP120/80 SpO298%)")
        plan = st.text_area("Initial Management Plan")
        attending = st.text_input("Attending Physician")
        submitted = st.form_submit_button("Add Patient")
        if submitted:
            # Compose row in same order as PATIENTS_HEADERS
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [
                timestamp, new_pid, full_name, dob.isoformat() if dob else "", age, sex,
                ward_bed, date_adm.isoformat() if date_adm else "", chief, "", "", hpi,
                "", "", pmh, "", allergies, "", "", "", vitals, "",
                "", "", "", "", "", plan, attending, ""
            ]
            try:
                ws_patients.append_row(row, value_input_option="USER_ENTERED")
                st.success(f"Added patient {full_name} ({new_pid})")
                st.cache_data.clear()
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed to add patient: {e}")

# Filtered patient list
if patients_df.empty:
    st.info("No patient records yet. Add a patient to get started.")
else:
    # apply search filter if provided
    display_df = patients_df.copy()
    if search:
        search_l = search.lower()
        display_df = display_df[
            display_df.apply(lambda r: r.astype(str).str.lower().str.contains(search_l).any(), axis=1)
        ]
    # show list: only show names as buttons (compact)
    st.markdown("**Click a patient to open their chart**")
    for idx, row in display_df.iterrows():
        name = row.get("Full Name", "Unnamed Patient")
        pid = row.get("Patient ID", "")
        # Skip if name is empty
        if not isinstance(name, str) or name.strip() == "":
            continue
        # show a compact clickable area: use button key unique
        key = f"open_{idx}"
        if st.button(f"👤 {name}", key=key):
            # store selected patient index (we store patient ID and the row index)
            st.session_state["selected_patient_id"] = pid
            st.session_state["selected_patient_idx"] = int(idx)
            st.experimental_rerun()

# -----------------------
# Patient detail view (if selected)
# -----------------------
if "selected_patient_id" in st.session_state and st.session_state.get("selected_patient_id"):
    pid = st.session_state["selected_patient_id"]
    # reload dataframes to ensure we have latest
    patients_df = load_dataframe_from_ws(ws_patients)
    visits_df = load_dataframe_from_ws(ws_visits)
    discharges_df = load_dataframe_from_ws(ws_discharges)

    patient_row = patients_df[patients_df["Patient ID"] == pid]
    if patient_row.empty:
        st.error("Selected patient not found (they may have been removed).")
    else:
        patient = patient_row.iloc[0].to_dict()
        st.markdown("---")
        # Header / summary
        title_col, action_col = st.columns([4, 1])
        with title_col:
            st.markdown(f"## {patient.get('Full Name','Unnamed')}")
            st.markdown(f"**Patient ID:** {pid}  •  **Ward/Bed:** {patient.get('Ward / Bed Number','N/A')}  •  **Age:** {patient.get('Age (in years)','N/A')}")
            st.markdown(f"**Admitted:** {patient.get('Date of Admission','N/A')}  •  **Attending:** {patient.get('Attending Physician','N/A')}")
        with action_col:
            if st.button("← Back", key="back_to_list"):
                # clear selection
                st.session_state.pop("selected_patient_id", None)
                st.session_state.pop("selected_patient_idx", None)
                st.experimental_rerun()

        # top summary card
        st.markdown("### Summary")
        st.markdown(f"> **Provisional Dx:** {patient.get('Provisional Diagnosis','N/A')}  •  **Initial Plan:** {patient.get('Initial Management Plan','N/A')}")

        # Two-column: left = forms (add visit/discharge), right = timeline
        left, right = st.columns([1.2, 1])

        # Left: forms to add Visit or Discharge
        with left:
            st.subheader("Add a Visit / Progress Note")
            with st.form("add_visit_form"):
                v_visit_date = st.date_input("Date of Visit", value=datetime.today())
                v_time = st.time_input("Time of Visit", value=datetime.now().time())
                v_doctor = st.text_input("Doctor / Submitter", value=st.secrets.get("user_name",""))
                v_subjective = st.text_area("Subjective (S)", height=80)
                v_objective = st.text_area("Objective (O)", height=80)
                v_assessment = st.text_area("Assessment (A)", height=80)
                v_plan = st.text_area("Plan (P)", height=80)
                v_vitals = st.text_input("Vital Signs (brief)")
                v_investigations = st.text_input("Investigations Ordered")
                v_results = st.text_input("Investigations Results")
                v_meds_changed = st.text_input("Changes in Medications")
                submit_visit = st.form_submit_button("Add Visit")
                if submit_visit:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # generate visit id
                    visit_id = generate_visit_id(visits_df)
                    row = [
                        ts, visit_id, pid, patient.get("Full Name",""), v_visit_date.isoformat(), v_time.strftime("%H:%M"),
                        patient.get("Ward / Bed Number",""), v_doctor, v_subjective, v_objective, v_assessment, v_plan,
                        v_vitals, v_investigations, v_results, v_meds_changed, "", "", "", ""
                    ]
                    try:
                        ws_visits.append_row(row, value_input_option="USER_ENTERED")
                        st.success("Visit added.")
                        st.cache_data.clear()
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Failed to add visit: {e}")

            st.markdown("---")
            st.subheader("Add Discharge Summary")
            with st.form("add_discharge_form"):
                d_date = st.date_input("Date of Discharge", value=datetime.today())
                d_final_dx = st.text_area("Final Diagnosis", height=80)
                d_summary = st.text_area("Hospital Course Summary", height=120)
                d_condition = st.selectbox("Condition at Discharge", options=["Improved", "Stable", "Referred", "Died", "Other"])
                d_medications = st.text_area("Discharge Medications")
                d_followup = st.text_area("Follow-Up Plan / Next Appointment")
                submit_dis = st.form_submit_button("Add Discharge")
                if submit_dis:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    discharge_id = generate_discharge_id(discharges_df)
                    # compute duration if possible
                    adm_date = patient.get("Date of Admission", "")
                    try:
                        if adm_date:
                            dau = pd.to_datetime(d_date) - pd.to_datetime(adm_date)
                            duration = f"{dau.days} days"
                        else:
                            duration = ""
                    except:
                        duration = ""
                    row = [
                        ts, discharge_id, pid, patient.get("Full Name",""), patient.get("Date of Admission",""), d_date.isoformat(),
                        duration, patient.get("Provisional Diagnosis",""), d_final_dx, patient.get("Past Medical History",""),
                        "", "", d_summary, d_condition, d_medications, "", d_followup, patient.get("Attending Physician",""), ""
                    ]
                    try:
                        ws_discharges.append_row(row, value_input_option="USER_ENTERED")
                        st.success("Discharge added.")
                        st.cache_data.clear()
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Failed to add discharge: {e}")

        # Right: Timeline - visits followed by discharges
        with right:
            st.subheader("Timeline")
            # load fresh
            visits_df = load_dataframe_from_ws(ws_visits)
            discharges_df = load_dataframe_from_ws(ws_discharges)

            patient_visits = visits_df[visits_df["Patient ID"] == pid].copy()
            patient_discharges = discharges_df[discharges_df["Patient ID"] == pid].copy()

            # Sort by Timestamp
            if not patient_visits.empty:
                patient_visits["ts_sort"] = pd.to_datetime(patient_visits.get("Timestamp", patient_visits.get("Date of Visit", "")), errors="coerce")
                patient_visits = patient_visits.sort_values("ts_sort", ascending=False)
                for _, vr in patient_visits.iterrows():
                    vdate = vr.get("Date of Visit", "") or vr.get("Timestamp","")
                    vdoc = vr.get("Doctor / Submitter", "")
                    st.markdown(f"**{vdate} — {vdoc}**")
                    st.markdown(f"- **Assessment:** {vr.get('Assessment (A)','—')}")
                    st.markdown(f"- **Plan:** {vr.get('Plan (P)','—')}")
                    st.markdown(f"- **Vitals:** {vr.get('Vital Signs','—')}")
                    st.markdown("---")
            else:
                st.info("No visits recorded for this patient.")

            if not patient_discharges.empty:
                st.markdown("### Discharge(s)")
                for _, dr in patient_discharges.sort_values("Date of Discharge", ascending=False).iterrows():
                    st.markdown(f"**{dr.get('Date of Discharge','')} — {dr.get('Condition at Discharge','')}**")
                    st.markdown(f"- **Final Dx:** {dr.get('Final Diagnosis','—')}")
                    st.markdown(f"- **Medications:** {dr.get('Discharge Medications','—')}")
                    st.markdown(f"- **Follow-up:** {dr.get('Follow-Up Plan','—')}")
                    st.markdown("---")

        st.markdown("---")
        st.markdown("**Raw patient record**")
        st.dataframe(patient_row.T.reset_index().rename(columns={"index":"Field", 0:"Value"}), use_container_width=True)

# -----------------------
# Footer
# -----------------------
st.caption("Inpatient EMR — built with Streamlit. Keep backups of your Google Sheet.")
