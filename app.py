# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from urllib.parse import quote, unquote
from datetime import date

# ---------- App Config ----------
st.set_page_config(page_title="Patient DB", layout="wide")

# ---------- Sidebar Dark Mode Toggle ----------
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False

st.sidebar.title("⚙️ Settings")
dark_mode = st.sidebar.toggle("Dark Mode", value=st.session_state["dark_mode"])
st.session_state["dark_mode"] = dark_mode

# ---------- Theme Styles ----------
light_css = """
<style>
body {background-color: #f9fafb; color: #111;}
.block-container {max-width: 1100px;}
.card {
  background: #ffffff;
  border-radius:12px;
  padding:16px;
  box-shadow:0 6px 18px rgba(0,0,0,0.06);
  margin-bottom:12px;
}
.card-title {font-size:18px; font-weight:600; margin-bottom:6px;}
.small-muted {color: #6b7280; font-size:13px;}
.form-wrap {background: #ffffff; padding:18px; border-radius:12px; box-shadow:0 6px 18px rgba(0,0,0,0.04);}
.open-btn {background:#2563eb; color:white; padding:7px 12px; border-radius:8px; text-decoration:none;}
</style>
"""

dark_css = """
<style>
body {background-color: #0f172a; color: #f9fafb;}
.block-container {max-width: 1100px;}
.card {
  background: #1e293b;
  border-radius:12px;
  padding:16px;
  box-shadow:0 6px 18px rgba(0,0,0,0.4);
  margin-bottom:12px;
}
.card-title {font-size:18px; font-weight:600; margin-bottom:6px; color:#f8fafc;}
.small-muted {color: #94a3b8; font-size:13px;}
.form-wrap {background: #1e293b; padding:18px; border-radius:12px; box-shadow:0 6px 18px rgba(0,0,0,0.4);}
.open-btn {background:#3b82f6; color:white; padding:7px 12px; border-radius:8px; text-decoration:none;}
</style>
"""

st.markdown(dark_css if dark_mode else light_css, unsafe_allow_html=True)

# ---------- Google Sheets Setup ----------
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
gc = gspread.authorize(creds)

# Fallback values if not in secrets
FALLBACK_SHEET_ID = "1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"
FALLBACK_SHEET_NAME = "Form Responses 1"

sheet_secret = st.secrets.get("sheet", {})
sheet_id = sheet_secret.get("sheet_id", FALLBACK_SHEET_ID)
sheet_name = sheet_secret.get("sheet_name", FALLBACK_SHEET_NAME)

worksheet = gc.open_by_key(sheet_id).worksheet(sheet_name)
records = worksheet.get_all_records()
df = pd.DataFrame(records)

if "Patient ID" not in df.columns:
    df.insert(0, "Patient ID", [f"P{str(i+1).zfill(4)}" for i in range(len(df))])

# ---------- Helper Functions ----------
def widget_for_column(col_name):
    cname = col_name.lower()
    if "date" in cname:
        return "date"
    if cname in ("su", "met", "dpp-4", "glp-1", "sglt2") or "med" in cname or "drug" in cname:
        return "checkbox"
    if any(k in cname for k in ("age", "weight", "kg", "years", "duration", "count", "number")):
        return "number"
    if any(k in cname for k in ("note", "remark", "reason", "comments", "history")):
        return "textarea"
    if "gender" in cname:
        return "select_gender"
    return "text"

def default_value_for(col_name):
    typ = widget_for_column(col_name)
    if typ == "date": return date.today()
    if typ == "number": return 0
    if typ == "checkbox": return False
    if typ == "textarea": return ""
    if typ == "select_gender": return "Male"
    return ""

def patient_list_from_df(dframe):
    if "Full Name" in dframe.columns:
        return sorted(dframe["Full Name"].dropna().unique().tolist())
    return sorted(dframe[dframe.columns[0]].dropna().unique().tolist())

BASE_URL = st.secrets.get("base_url", {}).get("url", "https://saradatabase.streamlit.app/")

def build_patient_link(name):
    return f"{BASE_URL}?patient={quote(name)}"

def render_visit_card(row):
    title = f"Visit • {row.get('Visit Date', '')}" if "Visit Date" in row.index else "Visit"
    lines = []
    for c in row.index:
        if c in ("Patient ID", "Full Name"): continue
        v = row.get(c)
        if v is None or (isinstance(v, str) and v.strip() == ""): continue
        lines.append(f"<div style='margin-bottom:4px'><strong>{c}:</strong> <span class='small-muted'>{v}</span></div>")
    st.markdown(f"<div class='card'><div class='card-title'>{title}</div>{''.join(lines)}</div>", unsafe_allow_html=True)

# ---------- Main Page ----------
query = st.query_params
selected_patient_param = query.get("patient", None)

if selected_patient_param:
    sel_name = unquote(selected_patient_param[0]) if isinstance(selected_patient_param, list) else unquote(selected_patient_param)
    st.markdown(f"## 🧾 Patient: {sel_name}")

    patient_rows = df[df["Full Name"].str.strip().str.lower() == sel_name.strip().lower()]
    if patient_rows.empty:
        st.warning("No records found for this patient.")
    else:
        st.markdown("### 📅 Visits")
        for _, r in patient_rows.iterrows():
            render_visit_card(r)

        st.markdown("---")
        st.markdown("### ➕ Add Visit")
        cols = list(df.columns)

        with st.form("dynamic_add_visit", clear_on_submit=True):
            inputs = {}
            left_cols, right_cols = st.columns(2)
            for i, col in enumerate(cols):
                if col == "Patient ID": continue
                container = left_cols if i % 2 == 0 else right_cols
                with container:
                    widget_type = widget_for_column(col)
                    default_val = default_value_for(col)
                    if col == "Full Name":
                        val = st.text_input(col, value=sel_name, disabled=True)
                    elif widget_type == "date":
                        val = st.date_input(col, value=default_val)
                    elif widget_type == "number":
                        val = st.number_input(col, value=default_val)
                    elif widget_type == "checkbox":
                        val = st.checkbox(col, value=False)
                        val = "Yes" if val else ""
                    elif widget_type == "textarea":
                        val = st.text_area(col, value="")
                    elif widget_type == "select_gender":
                        val = st.selectbox(col, ["Male", "Female", "Other"])
                    else:
                        val = st.text_input(col, value="")
                    inputs[col] = val
            if st.form_submit_button("Add Visit"):
                row_values = [inputs.get(c, "") for c in cols]
                worksheet.append_row(row_values)
                st.success("✅ Visit added successfully.")
                st.rerun()

    st.markdown(f"<div style='margin-top:12px'><a href='/' class='open-btn'>← Back to all patients</a></div>", unsafe_allow_html=True)

else:
    st.markdown("## 🩺 Patient Database")

    # ----- Add New Patient Section -----
    with st.expander("➕ Add New Patient", expanded=False):
        cols = list(df.columns)
        with st.form("add_patient", clear_on_submit=True):
            inputs = {}
            left_cols, right_cols = st.columns(2)
            for i, col in enumerate(cols):
                if col == "Patient ID": continue
                container = left_cols if i % 2 == 0 else right_cols
                with container:
                    widget_type = widget_for_column(col)
                    default_val = default_value_for(col)
                    if widget_type == "date":
                        val = st.date_input(col, value=default_val)
                    elif widget_type == "number":
                        val = st.number_input(col, value=default_val)
                    elif widget_type == "checkbox":
                        val = st.checkbox(col, value=False)
                        val = "Yes" if val else ""
                    elif widget_type == "textarea":
                        val = st.text_area(col, value="")
                    elif widget_type == "select_gender":
                        val = st.selectbox(col, ["Male", "Female", "Other"])
                    else:
                        val = st.text_input(col, value="")
                    inputs[col] = val
            if st.form_submit_button("Add Patient"):
                row_values = [inputs.get(c, "") for c in cols]
                worksheet.append_row(row_values)
                st.success("✅ Patient added successfully.")
                st.rerun()

    # ----- Search + Display Patients -----
    search = st.text_input("Search by name or ID")
    filtered = df[df.apply(lambda r: search.strip().lower() in str(r).lower(), axis=1)] if search else df
    patients = patient_list_from_df(filtered)

    for name in patients:
        link = build_patient_link(name)
        st.markdown(f"<div class='card'><div style='display:flex;justify-content:space-between;align-items:center'><div><b>{name}</b></div><div><a class='open-btn' href='{link}'>Open</a></div></div></div>", unsafe_allow_html=True)
