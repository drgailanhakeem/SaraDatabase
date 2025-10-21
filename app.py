# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from urllib.parse import quote, unquote
from datetime import date, datetime

st.set_page_config(page_title="Patient DB", layout="wide")
st.title("🩺 Patient Dashboard")

# ---------- Google Sheets connect (uses secrets) ----------
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
gc = gspread.authorize(creds)

sheet_id = st.secrets["sheet"]["sheet_id"]
sheet_name = st.secrets["sheet"].get("sheet_name", "Form Responses 1")
worksheet = gc.open_by_key(sheet_id).worksheet(sheet_name)

# ---------- Load data (preserves column order) ----------
records = worksheet.get_all_records()
df = pd.DataFrame(records)

# If no Patient ID, create stable IDs in memory (won't overwrite sheet)
if "Patient ID" not in df.columns:
    df.insert(0, "Patient ID", [f"P{str(i+1).zfill(4)}" for i in range(len(df))])

# ---------- Styling (modern card + form container) ----------
st.markdown("""
<style>
.block-container {max-width: 1100px;}
.card {
  background: var(--card-bg, #ffffff);
  border-radius:12px;
  padding:16px;
  box-shadow:0 6px 18px rgba(0,0,0,0.06);
  margin-bottom:12px;
}
.card-title {font-size:18px; font-weight:600; margin-bottom:6px;}
.small-muted {color: #6b7280; font-size:13px;}
.form-wrap {background: linear-gradient(180deg, rgba(255,255,255,1), rgba(250,250,250,1)); padding:18px; border-radius:12px; box-shadow: 0 6px 18px rgba(0,0,0,0.04);}
.open-btn {background:#2563eb; color:white; padding:7px 12px; border-radius:8px; text-decoration:none;}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers to pick widget type ----------
def widget_for_column(col_name, default=""):
    cname = col_name.lower()
    # Date hint
    if "date" in cname:
        return "date"
    # Boolean/meds checkboxes: short names or 'su' 'met' etc.
    if cname in ("su", "met", "dpp-4", "glp-1", "sglt2") or "med" in cname or "drug" in cname:
        return "checkbox"
    # numeric hints
    if any(k in cname for k in ("age", "weight", "kg", "years", "duration", "count", "number")):
        return "number"
    # long text
    if any(k in cname for k in ("note", "remark", "reason", "comments", "history")):
        return "textarea"
    # select gender
    if "gender" in cname:
        return "select_gender"
    # fallback short text
    return "text"

def default_value_for(col_name):
    typ = widget_for_column(col_name)
    if typ == "date":
        return date.today()
    if typ == "number":
        return 0 if "age" in col_name.lower() or "weight" in col_name.lower() else 0
    if typ == "checkbox":
        return False
    if typ == "textarea":
        return ""
    if typ == "select_gender":
        return "Male"
    return ""

# ---------- Query params / routing ----------
query = st.query_params
selected_patient_param = query.get("patient", None)
BASE_URL = st.secrets.get("base_url", {}).get("url", "https://saradatabase.streamlit.app/")

# ---------- Utilities ----------
def patient_list_from_df(dframe):
    # use Full Name column if exists
    if "Full Name" in dframe.columns:
        return sorted(dframe["Full Name"].dropna().unique().tolist())
    # fallback to first column
    return sorted(dframe[dframe.columns[0]].dropna().unique().tolist())

def build_patient_link(name):
    return f"{BASE_URL}?patient={quote(name)}"

# ---------- Display functions ----------
def render_visit_card(row):
    # row is a Series
    # Show date prominently if exists
    date_val = None
    for c in row.index:
        if "date" in c.lower():
            date_val = row.get(c)
            break
    title = f"Visit • {date_val}" if date_val else "Visit"
    # build key-value list (skip Patient ID and Full Name)
    lines = []
    for c in row.index:
        if c in ("Patient ID", "Full Name"):
            continue
        v = row.get(c)
        if v is None or (isinstance(v, str) and v.strip()==""):
            continue
        lines.append(f"<div style='margin-bottom:4px'><strong style='color:#111'>{c}:</strong> <span class='small-muted'> {v}</span></div>")
    html = f"<div class='card'><div class='card-title'>{title}</div>{''.join(lines)}</div>"
    st.markdown(html, unsafe_allow_html=True)

# ---------- MAIN: either patient page or list page ----------
if selected_patient_param:
    # patient page
    sel_name = unquote(selected_patient_param[0]) if isinstance(selected_patient_param, list) else unquote(selected_patient_param)
    st.markdown(f"## 🧾 Patient: {sel_name}")

    # filter by name match (case-insensitive)
    if "Full Name" in df.columns:
        patient_rows = df[df["Full Name"].str.strip().str.lower() == sel_name.strip().lower()]
    else:
        # fallback by first column
        patient_rows = df[df[df.columns[0]].str.strip().str.lower() == sel_name.strip().lower()]

    if patient_rows.empty:
        st.warning("No records found for this patient.")
    else:
        # show profile header
        first = patient_rows.iloc[0]
        header_html = f"<div class='card'><div class='card-title'>{first.get('Full Name','')}</div><div class='small-muted'>ID: {first.get('Patient ID','—')}</div></div>"
        st.markdown(header_html, unsafe_allow_html=True)

        # visits as cards
        st.markdown("### 📅 Visits")
        for _, r in patient_rows.iterrows():
            render_visit_card(r)

        st.markdown("---")
        st.markdown("### ➕ Add Visit")
        # Build form dynamically from sheet columns
        cols = list(df.columns)  # keep sheet order
        # We'll create inputs for each column except Patient ID (auto) and Full Name (we'll auto-fill)
        with st.form("dynamic_add_visit", clear_on_submit=True):
            st.markdown("<div class='form-wrap'>", unsafe_allow_html=True)
            inputs = {}
            # two-column layout for nicer look
            left_cols, right_cols = st.columns(2)
            for i, col in enumerate(cols):
                if col == "Patient ID":
                    continue
                # skip Full Name input because we already have patient
                if col == "Full Name":
                    # show but disabled
                    with left_cols if i%2==0 else right_cols:
                        st.text_input(col, value=sel_name, key=f"fld_{col}", disabled=True)
                        inputs[col] = sel_name
                    continue

                widget_type = widget_for_column(col)
                default_val = default_value_for(col)

                # place alternating
                container = left_cols if i%2==0 else right_cols
                with container:
                    if widget_type == "date":
                        val = st.date_input(col, value=default_val, key=f"fld_{col}")
                        # store as ISO date string
                        inputs[col] = val.strftime("%Y-%m-%d")
                    elif widget_type == "number":
                        val = st.number_input(col, value=default_val, key=f"fld_{col}")
                        inputs[col] = val
                    elif widget_type == "checkbox":
                        val = st.checkbox(col, value=False, key=f"fld_{col}")
                        inputs[col] = "Yes" if val else ""
                    elif widget_type == "textarea":
                        val = st.text_area(col, value="", key=f"fld_{col}")
                        inputs[col] = val
                    elif widget_type == "select_gender":
                        val = st.selectbox(col, options=["Male", "Female", "Other"], index=0, key=f"fld_{col}")
                        inputs[col] = val
                    else:
                        # text
                        val = st.text_input(col, value="", key=f"fld_{col}")
                        inputs[col] = val
            st.markdown("</div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Add Visit")

            if submitted:
                # Build row values in sheet column order
                row_values = []
                for col in cols:
                    if col == "Patient ID":
                        # create a new ID for the appended row if sheet doesn't have it
                        # attempt to find existing IDs in sheet
                        try:
                            sheet_vals = worksheet.get_all_records()
                            # if sheet already has Patient ID column, append as blank so sheet will auto-populate? safer to set empty
                        except Exception:
                            pass
                        row_values.append("")  # leave Patient ID blank (or set later)
                    else:
                        # use input if available else blank
                        v = inputs.get(col, "")
                        row_values.append(v if v is not None else "")
                # Append to sheet
                worksheet.append_row(row_values)
                st.success("✅ Visit added to Google Sheet (preserved sheet columns).")
                st.experimental_rerun()

    # back link
    st.markdown(f"<div style='margin-top:12px'><a href='/' class='open-btn'>← Back to all patients</a></div>", unsafe_allow_html=True)

else:
    # list page
    st.markdown("## 🔎 Patients")
    search = st.text_input("Search by name or ID")
    if search:
        mask = df.apply(lambda r: search.strip().lower() in str(r.astype(str)).lower(), axis=1)
        filtered = df[mask]
    else:
        filtered = df

    # show simple cards with link
    patients = patient_list_from_df(filtered)
    for name in patients:
        link = build_patient_link(name)
        card_html = f"<div class='card'><div style='display:flex;justify-content:space-between;align-items:center'><div><b>{name}</b></div><div><a class='open-btn' href='{link}'>Open</a></div></div></div>"
        st.markdown(card_html, unsafe_allow_html=True)
