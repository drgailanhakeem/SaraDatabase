# app.py - Robust Streamlit + Google Sheets app (fixed APIError handling)
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import uuid
from datetime import datetime

st.set_page_config(page_title="Sara Patient Database", layout="wide")

# ---------------------------
# CONFIG: scopes + secrets
# ---------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# helpful check before doing anything
if "gcp_service_account" not in st.secrets or "sheet" not in st.secrets:
    st.error(
        "Streamlit secrets are missing. Add [gcp_service_account] and [sheet] sections in Settings → Secrets."
    )
    st.stop()

# ---------------------------
# CONNECT TO GOOGLE SHEETS
# ---------------------------
try:
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"Authentication failed: {e}")
    st.stop()

# read sheet config
sheet_id = st.secrets["sheet"].get("sheet_id")
sheet_name = st.secrets["sheet"].get("sheet_name", "")

if not sheet_id:
    st.error("Missing sheet.sheet_id in Streamlit secrets.")
    st.stop()

# try to open spreadsheet (single call)
try:
    spreadsheet = client.open_by_key(sheet_id)
except Exception as e:
    st.error(
        "Unable to open spreadsheet with the provided sheet_id. Common causes:\n\n"
        "- The service account email is not added as a reader/editor on the sheet.\n"
        "- The sheet_id is wrong.\n\n"
        "Fix: share the Google Sheet with the service account email (client_email in your service account JSON), "
        "verify the sheet_id, and ensure your secrets are correct.\n\n"
        f"Exact error: {e}"
    )
    st.stop()

# open main worksheet (by name if provided, otherwise first sheet)
try:
    if sheet_name:
        main_sheet = spreadsheet.worksheet(sheet_name)
    else:
        main_sheet = spreadsheet.sheet1
except Exception as e:
    st.error(
        "Could not open the worksheet by name. Check 'sheet_name' in secrets, and make sure the worksheet exists.\n\n"
        f"Error: {e}"
    )
    st.stop()

# ensure Visits sheet exists (create if missing)
VISITS_TITLE = "Visits"
try:
    try:
        visits_sheet = spreadsheet.worksheet(VISITS_TITLE)
    except gspread.exceptions.WorksheetNotFound:
        visits_sheet = spreadsheet.add_worksheet(title=VISITS_TITLE, rows="500", cols="50")
        # append header row - adjust to whatever columns you want in visits
        visits_sheet.append_row(["Visit ID", "Patient ID", "Date of Visit", "Time of Visit", "Doctor's Name", "Notes"])
except Exception as e:
    st.error(f"Error ensuring Visits sheet exists: {e}")
    st.stop()

# ---------------------------
# Load main & visits data (one-time, small app-level load)
# ---------------------------
def load_data():
    main_rows = main_sheet.get_all_records()
    visits_rows = visits_sheet.get_all_records()
    df_main = pd.DataFrame(main_rows)
    df_visits = pd.DataFrame(visits_rows)
    return df_main, df_visits

try:
    df, visits_df = load_data()
except Exception as e:
    st.error(f"Failed to load sheet data: {e}")
    st.stop()

# ---------------------------
# Helpers
# ---------------------------
def generate_patient_id():
    return f"pt{uuid.uuid4().hex[:6]}"

def generate_visit_id():
    return f"vt{uuid.uuid4().hex[:6]}"

def get_patient_by_id(pid):
    if "Patient ID" in df.columns:
        return df[df["Patient ID"] == pid]
    return pd.DataFrame()

def get_visits_for_patient(pid):
    if "Patient ID" in visits_df.columns:
        v = visits_df[visits_df["Patient ID"] == pid].copy()
        if "Date of Visit" in v.columns:
            v["Date of Visit"] = pd.to_datetime(v["Date of Visit"], errors="coerce")
            v = v.sort_values("Date of Visit", ascending=False)
        return v
    return pd.DataFrame()

def safe_str(x):
    if pd.isna(x):
        return ""
    return str(x)

# ---------------------------
# UI: Title / routing
# ---------------------------
st.title("🩺 Sara Patient Database")
params = st.query_params
patient_id = params.get("id", [None])[0] if isinstance(params.get("id"), list) else params.get("id")

# ---------------------------
# PATIENT PROFILE PAGE
# ---------------------------
if patient_id:
    patient_df = get_patient_by_id(patient_id)
    if patient_df.empty:
        st.error("❌ Patient not found.")
    else:
        patient = patient_df.iloc[0]
        st.header(f"{safe_str(patient.get('Full Name', 'Unknown'))}  —  ID: {patient_id}")

        # Dynamic display of every column in two columns
        st.subheader("📋 Patient Information")
        cols = st.columns(2)
        display_items = [(c, safe_str(v)) for c, v in patient.items() if str(v).strip() != ""]
        for i, (col_name, value) in enumerate(display_items):
            with cols[i % 2]:
                st.markdown(f"**{col_name}:** {value}")

        st.divider()

        # Delete (two-step confirm using session state)
        delete_key = f"delete_{patient_id}"
        confirm_key = f"confirm_{patient_id}"
        if delete_key not in st.session_state:
            st.session_state[delete_key] = False

        col_left, col_right = st.columns([1, 3])
        with col_left:
            if not st.session_state[delete_key]:
                if st.button("🗑️ Delete Patient", key=delete_key):
                    st.session_state[delete_key] = True
                    st.experimental_rerun()
            else:
                st.warning(f"⚠️ Confirm deletion of patient **{safe_str(patient.get('Full Name',''))}** (ID: {patient_id})")
                if st.button("✅ Confirm Delete", key=confirm_key):
                    # perform deletion from main sheet & visits
                    try:
                        # reload fresh main rows
                        all_main = main_sheet.get_all_records()
                        rows_to_delete = []
                        for idx, row in enumerate(all_main, start=2):
                            if "Patient ID" in row and str(row.get("Patient ID")) == str(patient_id):
                                rows_to_delete.append(idx)
                            elif "Full Name" in row and str(row.get("Full Name")).strip() == str(patient.get("Full Name","")).strip():
                                # fallback if no Patient ID column or missing values
                                rows_to_delete.append(idx)
                        for r in sorted(rows_to_delete, reverse=True):
                            main_sheet.delete_rows(r)

                        # delete visits
                        all_vis = visits_sheet.get_all_records()
                        rows_to_delete_v = []
                        for idx, row in enumerate(all_vis, start=2):
                            if "Patient ID" in row and str(row.get("Patient ID")) == str(patient_id):
                                rows_to_delete_v.append(idx)
                        for r in sorted(rows_to_delete_v, reverse=True):
                            visits_sheet.delete_rows(r)

                        st.success("✅ Patient and associated visits deleted.")
                        st.session_state[delete_key] = False
                        # clear query param to go back home
                        st.experimental_set_query_params()
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")
                if st.button("✖ Cancel", key=f"cancel_{patient_id}"):
                    st.session_state[delete_key] = False
                    st.experimental_rerun()

        # Add Visit (on patient page) - uses visits sheet headers dynamically
        st.divider()
        with st.expander("➕ Add New Visit"):
            st.subheader("Record Visit for this patient")
            visit_row = {}
            visit_row["Visit ID"] = generate_visit_id()
            visit_row["Patient ID"] = patient_id

            # use visits_sheet headers as source of fields (fallback to sensible defaults)
            headers = visits_sheet.row_values(1)
            if not headers:
                headers = ["Visit ID", "Patient ID", "Date of Visit", "Time of Visit", "Doctor's Name", "Notes"]

            for col in headers:
                if col in ["Visit ID", "Patient ID"]:
                    continue
                key = f"visit_{col}_{patient_id}"
                if "date" in col.lower():
                    visit_row[col] = st.date_input(col, key=key)
                elif "time" in col.lower():
                    visit_row[col] = st.time_input(col, key=key)
                else:
                    visit_row[col] = st.text_input(col, key=key)

            if st.button("💾 Save Visit", key=f"save_visit_{patient_id}"):
                try:
                    # serialize dates/times
                    row_values = []
                    for h in headers:
                        val = visit_row.get(h, "")
                        if isinstance(val, (datetime,)):
                            row_values.append(val.strftime("%Y-%m-%d %H:%M:%S"))
                        else:
                            row_values.append(str(val))
                    visits_sheet.append_row(row_values)
                    st.success("✅ Visit saved.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to save visit: {e}")

        # Visit history: load and display, sorted by date desc, each in expander
        st.divider()
        st.subheader("📅 Visit History")
        pv = get_visits_for_patient(patient_id)
        if pv.empty:
            st.info("No visits recorded.")
        else:
            for idx, row in pv.iterrows():
                date_display = ""
                if "Date of Visit" in pv.columns:
                    dt = row.get("Date of Visit")
                    try:
                        date_display = pd.to_datetime(dt).strftime("%Y-%m-%d")
                    except Exception:
                        date_display = str(dt)
                title = f"Visit — {date_display}" if date_display else "Visit"
                with st.expander(title, expanded=False):
                    # show all fields for that visit
                    cols2 = st.columns(2)
                    items = [(c, safe_str(row.get(c, ""))) for c in pv.columns if str(row.get(c, "")).strip() != ""]
                    for i, (cname, cval) in enumerate(items):
                        with cols2[i % 2]:
                            st.markdown(f"**{cname}:** {cval}")

        st.markdown("[⬅ Back to Home](?)")

# ---------------------------
# HOMEPAGE (patient list + add patient)
# ---------------------------
else:
    st.subheader("🔍 Patients")
    search = st.text_input("Search by Full Name")
    filtered = df[df["Full Name"].str.contains(search, case=False, na=False)] if search else df

    if filtered.empty:
        st.info("No patients found.")
    else:
        for _, r in filtered.iterrows():
            pid = r.get("Patient ID") or ""
            display_name = safe_str(r.get("Full Name", "Unnamed"))
            age = safe_str(r.get("Age (in years)", ""))
            link = f"?id={pid}" if pid else ""
            st.markdown(f"👤 [{display_name} (Age: {age})]({link})")

    st.divider()

    # Add new patient (uses main_sheet headers)
    with st.expander("➕ Add New Patient"):
        st.subheader("Register New Patient")
        new_row = {}
        new_row["Patient ID"] = generate_patient_id()
        headers_main = main_sheet.row_values(1)
        if not headers_main:
            st.error("Main sheet has no header row.")
        else:
            for h in headers_main:
                if h == "Patient ID":
                    continue
                key = f"new_{h}"
                if "date" in h.lower():
                    new_row[h] = st.date_input(h, key=key)
                elif "time" in h.lower():
                    new_row[h] = st.time_input(h, key=key)
                else:
                    new_row[h] = st.text_input(h, key=key)

            if st.button("💾 Save Patient", key="save_new_patient"):
                try:
                    # serialize
                    row_to_append = []
                    for h in headers_main:
                        v = new_row.get(h, "")
                        if isinstance(v, datetime):
                            row_to_append.append(v.strftime("%Y-%m-%d %H:%M:%S"))
                        else:
                            row_to_append.append(str(v))
                    main_sheet.append_row(row_to_append)
                    st.success("✅ Patient added.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to add patient: {e}")
