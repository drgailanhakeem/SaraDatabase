# -*- coding: utf-8 -*-
"""
Full production-ready Streamlit app:
- Reads/writes to Google Sheet (service account via st.secrets["gcp_service_account"])
- Uses your sheet id and tab "Form Responses 1"
- Dynamic forms that match your sheet columns exactly (Add Patient, Add Visit)
- Modern card UI for visits
- Dark mode toggle (CSS injection)
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from urllib.parse import quote, unquote
from datetime import date, datetime
from google.oauth2.service_account import Credentials

st.title("Google Sheets Connection Test")

try:
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(st.secrets["sheet"]["sheet_name"])
    st.success("✅ Connected successfully to Google Sheet!")
except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheet:\n\n{e}")


# ---------------------------
# Config - set your sheet id and tab name
# ---------------------------
SHEET_ID = "1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"
SHEET_TAB = "Form Responses 1"

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(page_title="Patient Dashboard", layout="wide")
st.title("🩺 Patient Dashboard")

# ---------------------------
# Dark mode toggle stored in session_state
# ---------------------------
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False

def apply_css(dark: bool):
    """Inject CSS for light or dark theme (affects most elements)."""
    if dark:
        css = """
        <style>
        :root { color-scheme: dark; }
        .stApp { background: #0b1220; color: #e6eef8; }
        .card { background:#0f1724; color:#e6eef8; border: 1px solid #1f2937; }
        .form-wrap { background:#0f1724; color:#e6eef8; border: 1px solid #1f2937; }
        .open-btn { background:#2563eb; color:#fff !important; }
        .small-muted { color:#94a3b8; }
        a { color: #93c5fd; }
        </style>
        """
    else:
        css = """
        <style>
        :root { color-scheme: light; }
        .stApp { background: #f7fafc; color: #0f1724; }
        .card { background:#ffffff; color:#0f1724; border: 1px solid #e6eef8; }
        .form-wrap { background:#ffffff; color:#0f1724; border: 1px solid #e6eef8; }
        .open-btn { background:#2563eb; color:#fff !important; }
        .small-muted { color:#6b7280; }
        a { color: #1e40af; }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)

# sidebar toggle
with st.sidebar:
    st.write("⚙️ Settings")
    dm = st.checkbox("Dark mode", value=st.session_state["dark_mode"], key="dark_mode_checkbox")
    st.session_state["dark_mode"] = dm
apply_css(dm)

# ---------------------------
# Connect to Google Sheets (gspread + service account)
# ---------------------------
@st.cache_resource
def connect_gs(secrets_dict):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_info(secrets_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

try:
    gclient = connect_gs(st.secrets["gcp_service_account"])
except Exception as e:
    st.error("Google Sheets authentication failed. Make sure your service account JSON is in Streamlit Secrets under [gcp_service_account].")
    st.stop()

try:
    worksheet = gclient.open_by_key(SHEET_ID).worksheet(SHEET_TAB)
except Exception as e:
    st.error(f"Could not open sheet/tab. Check SHEET_ID and SHEET_TAB (currently {SHEET_ID} / {SHEET_TAB}). Error: {e}")
    st.stop()

# ---------------------------
# Load sheet data (preserve column order)
# ---------------------------
@st.cache_data(ttl=20)
def load_sheet_df(ws):
    records = ws.get_all_records()
    df_local = pd.DataFrame(records)
    return df_local

df = load_sheet_df(worksheet)

# If sheet is empty, create empty df with no columns (shouldn't happen)
if df is None:
    df = pd.DataFrame()

# ---------------------------
# Ensure required columns mapping and keep original order
# ---------------------------
sheet_columns = list(df.columns)  # exact sheet column order

# Helper: build patient names list (uses Full Name if present)
def patient_list_from_df(dframe):
    if "Full Name" in dframe.columns:
        return sorted(dframe["Full Name"].dropna().unique().tolist())
    return sorted(dframe[dframe.columns[0]].dropna().unique().tolist())

# Base URL for patient links (optional in secrets)
BASE_URL = st.secrets.get("base_url", {}).get("url", f"{st.get_option('server.address') or ''}")

def build_patient_link(name):
    # if base url not set, produce relative link
    if BASE_URL:
        return f"{BASE_URL}?patient={quote(name)}"
    return f"?patient={quote(name)}"

# ---------------------------
# Widget type heuristics (detect best widget type from column name)
# ---------------------------
def widget_for_column(col_name):
    cname = col_name.lower()
    # prefer exact matches for common fields
    if "date" in cname or "dob" in cname:
        return "date"
    if cname in ("sex", "gender"):
        return "select_gender"
    if any(k in cname for k in ("age", "height", "weight", "years", "duration", "hb", "hba", "count", "number")):
        return "number"
    if any(k in cname for k in ("note", "remark", "impression", "history", "hpi", "chief", "diagnosis", "comments", "notes")):
        return "textarea"
    if any(k in cname for k in ("yes/no", "status", "use", "smoking", "alcohol")):
        return "select_simple"
    # medication-like columns (short names)
    if cname in ("su", "met", "dpp-4", "glp-1", "sglt2") or "med" in cname or "medications" in cname:
        return "checkbox"
    # default
    return "text"

def default_value_for(col_name):
    t = widget_for_column(col_name)
    if t == "date":
        return date.today()
    if t == "number":
        return 0
    if t == "checkbox":
        return False
    if t == "textarea":
        return ""
    if t == "select_gender":
        return "Male"
    if t == "select_simple":
        return "Unknown"
    return ""

# ---------------------------
# UI: Main split: list view vs patient view via query param 'patient'
# ---------------------------
query = st.query_params
selected_patient_param = query.get("patient", None)

# Helper: Render visit card (modern)
def render_visit_card(row):
    # title – prefer 'Date of Visit' or any column containing 'date'
    date_col = next((c for c in row.index if "date" in c.lower()), None)
    title = f"Visit • {row.get(date_col, '')}" if date_col else "Visit"
    lines = []
    for c in row.index:
        if c in ("Full Name",):  # skip Full Name header inside card (we show header externally)
            continue
        val = row.get(c)
        if val is None or (isinstance(val, str) and val.strip()==""):
            continue
        lines.append(f"<div style='margin-bottom:6px'><strong style='color:var(--title-color,#0f1724)'>{c}:</strong> <span class='small-muted'>{val}</span></div>")
    html = f"<div class='card' style='padding:14px'>{'<div style=\"font-weight:600;margin-bottom:6px\">'+title+'</div>' + ''.join(lines)}</div>"
    st.markdown(html, unsafe_allow_html=True)

# ---------- MAIN: Patient page ----------
if selected_patient_param:
    sel_name = unquote(selected_patient_param[0]) if isinstance(selected_patient_param, list) else unquote(selected_patient_param)
    st.markdown(f"## 🧾 Patient: {sel_name}")

    # filter dataframe for this patient
    if "Full Name" in df.columns:
        patient_rows = df[df["Full Name"].str.strip().str.lower() == sel_name.strip().lower()]
    else:
        patient_rows = df[df[df.columns[0]].str.strip().str.lower() == sel_name.strip().lower()]

    if patient_rows.empty:
        st.warning("No records found for this patient.")
    else:
        # Header card with basic info (use first row)
        first = patient_rows.iloc[0]
        basic_fields = []
        for col in ("Full Name", "Age (in years)", "Sex"):
            if col in first.index:
                basic_fields.append(f"<div><strong>{col}:</strong> {first.get(col,'')}</div>")
        header_html = f"<div class='card' style='padding:14px; margin-bottom:12px'><div style='font-size:18px;font-weight:600'>{first.get('Full Name','')}</div>{''.join(basic_fields)}</div>"
        st.markdown(header_html, unsafe_allow_html=True)

        st.markdown("### 📅 Visit History")
        for _, r in patient_rows.iterrows():
            render_visit_card(r)

        st.markdown("---")
        st.markdown("### ➕ Add Visit")
        cols = sheet_columns  # exact sheet column order

        # Dynamic Add Visit form (builds inputs for every sheet column)
        with st.form("add_visit_form", clear_on_submit=True):
            st.markdown("<div class='form-wrap'>", unsafe_allow_html=True)
            inputs = {}
            # Use two columns layout for compact look
            left, right = st.columns(2)
            for i, col in enumerate(cols):
                # Skip Patient ID if present (we let sheet/GForm handle it) but include if you want to write
                container = left if i % 2 == 0 else right
                widget_key = f"visit_{sel_name}_{col}_{i}"
                # For Full Name: auto-fill and disable
                if col == "Full Name":
                    with container:
                        st.text_input(col, value=sel_name, disabled=True, key=widget_key)
                        inputs[col] = sel_name
                    continue
                # Create widgets according to heuristics
                wtype = widget_for_column(col)
                with container:
                    if wtype == "date":
                        val = st.date_input(col, value=default_value_for(col), key=widget_key)
                        inputs[col] = val.strftime("%Y-%m-%d")
                    elif wtype == "number":
                        val = st.number_input(col, value=default_value_for(col), key=widget_key)
                        inputs[col] = val
                    elif wtype == "checkbox":
                        val = st.checkbox(col, value=False, key=widget_key)
                        inputs[col] = "Yes" if val else ""
                    elif wtype == "textarea":
                        val = st.text_area(col, value="", key=widget_key)
                        inputs[col] = val
                    elif wtype == "select_gender":
                        val = st.selectbox(col, options=["Male", "Female", "Other"], index=0, key=widget_key)
                        inputs[col] = val
                    elif wtype == "select_simple":
                        val = st.selectbox(col, options=["Yes", "No", "Unknown"], index=2, key=widget_key)
                        inputs[col] = val
                    else:
                        val = st.text_input(col, value="", key=widget_key)
                        inputs[col] = val
            st.markdown("</div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Add Visit")
            if submitted:
                # Build row in exact sheet column order
                row_values = []
                for col in cols:
                    row_values.append(inputs.get(col, ""))
                try:
                    worksheet.append_row(row_values)
                    st.success("✅ Visit appended to Google Sheet.")
                    # reload cached df
                    load_sheet_df.clear()
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Write failed: {e}")

    st.markdown(f"<div style='margin-top:12px'><a href='/' class='open-btn'>← Back to all patients</a></div>", unsafe_allow_html=True)

# ---------- MAIN: All patients list + Add Patient ----------
else:
    st.markdown("## 🔎 Patients")

    # Add New Patient (expandable) — uses same column order
    with st.expander("➕ Add New Patient", expanded=False):
        st.markdown("Fill the form below (fields match your Google Sheet columns).")
        cols = sheet_columns
        with st.form("add_patient_form", clear_on_submit=True):
            st.markdown("<div class='form-wrap'>", unsafe_allow_html=True)
            inputs = {}
            left, right = st.columns(2)
            for i, col in enumerate(cols):
                container = left if i % 2 == 0 else right
                widget_key = f"new_{col}_{i}"
                # For Timestamp, auto-populate
                if "timestamp" in col.lower():
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with container:
                        st.text_input(col, value=ts, disabled=True, key=widget_key)
                    inputs[col] = ts
                    continue
                # Build widget based on heuristics
                wtype = widget_for_column(col)
                with container:
                    if wtype == "date":
                        val = st.date_input(col, value=default_value_for(col), key=widget_key)
                        inputs[col] = val.strftime("%Y-%m-%d")
                    elif wtype == "number":
                        val = st.number_input(col, value=default_value_for(col), key=widget_key)
                        inputs[col] = val
                    elif wtype == "checkbox":
                        val = st.checkbox(col, value=False, key=widget_key)
                        inputs[col] = "Yes" if val else ""
                    elif wtype == "textarea":
                        val = st.text_area(col, value="", key=widget_key)
                        inputs[col] = val
                    elif wtype == "select_gender":
                        val = st.selectbox(col, options=["Male", "Female", "Other"], index=0, key=widget_key)
                        inputs[col] = val
                    elif wtype == "select_simple":
                        val = st.selectbox(col, options=["Yes", "No", "Unknown"], index=2, key=widget_key)
                        inputs[col] = val
                    else:
                        val = st.text_input(col, value="", key=widget_key)
                        inputs[col] = val
            st.markdown("</div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Add Patient")
            if submitted:
                row_values = [inputs.get(col, "") for col in cols]
                try:
                    worksheet.append_row(row_values)
                    st.success("✅ Patient added to Google Sheet.")
                    # reload
                    load_sheet_df.clear()
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Write failed: {e}")

    # Search / list
    search = st.text_input("Search by name or any text (press Enter)")
    if search:
        mask = df.apply(lambda r: search.strip().lower() in str(r.astype(str)).lower(), axis=1)
        filtered = df[mask]
    else:
        filtered = df

    patients = patient_list_from_df(filtered)
    # Show cards
    for name in patients:
        link = build_patient_link(name)
        card_html = f"""
        <div class='card' style='padding:10px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center'>
            <div style='font-weight:600'>{name}</div>
            <div><a class='open-btn' href='{link}'>Open</a></div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
