import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- Page Config ---
st.set_page_config(
    page_title="Patient Profiles",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS (modern card look) ---
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"]{ background-color: #f7f9fb; }
        [data-testid="stHeader"]{ background: rgba(0,0,0,0); }

        .main-title { font-size: 2rem; font-weight: 700; color: #111827; }
        .sub-title  { color: #6b7280; margin-bottom: 1rem; }

        .patient-card {
            background: white;
            border-radius: 14px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 6px 20px rgba(13, 38, 59, 0.04);
            transition: transform .12s ease-in-out, box-shadow .12s ease-in-out;
        }
        .patient-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 30px rgba(13, 38, 59, 0.07);
        }
        .patient-name { font-weight: 600; font-size: 1.05rem; color: #0f172a; }
        .patient-meta { color: #475569; font-size: 0.9rem; margin-bottom: 0.65rem; }

        .metric { display:inline-block; background:#f3f4f6; padding:0.35rem 0.6rem; border-radius:8px; margin-right:0.45rem; font-size:0.85rem; color:#374151; }

        /* make dataframes look better */
        div[data-testid="stDataFrame"] { background: white; border-radius: 10px; padding: 10px; box-shadow: 0 6px 20px rgba(13,38,59,0.04); }
    </style>
""", unsafe_allow_html=True)

# --- Google Sheets setup (adjusted to your sheet) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/"
SHEET_NAME = "Responses"

def connect_to_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)

def load_data(sheet):
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df.columns = [c.strip() for c in df.columns]
    return df

# --- Helper: robust field getter that accepts multiple possible header names ---
def get_field(row, candidates, fallback="N/A"):
    """
    row: a pandas Series for one record
    candidates: list of possible header names in order of preference
    returns first non-empty value found, else fallback
    """
    for key in candidates:
        if key in row.index:
            val = row.get(key)
            # Accept non-empty, non-null strings/numbers
            if pd.isna(val):
                continue
            s = str(val).strip()
            if s != "":
                return s
    return fallback

# --- UI header ---
st.markdown('<div class="main-title">🧠 Patient Profiles</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Cards view — shows key patient info. Search across all fields below.</div>', unsafe_allow_html=True)
st.markdown("---")

# --- Load data ---
try:
    sheet = connect_to_google_sheet()
    patients_df = load_data(sheet)

    if patients_df.empty:
        st.warning("No patient records found in the Google Sheet.")
        st.stop()

    st.success(f"✅ Loaded {len(patients_df)} patient records.")

    # --- Search ---
    search = st.text_input("🔍 Search by name, ID, diagnosis, or any text (press Enter)")

    if search:
        filtered = patients_df[
            patients_df.apply(lambda r: r.astype(str).str.contains(search, case=False, na=False).any(), axis=1)
        ].reset_index(drop=True)
    else:
        filtered = patients_df.reset_index(drop=True)

    if filtered.empty:
        st.warning("No matching records found.")
        st.stop()

    # --- Build cards: use flexible candidate headers ---
    # Candidate header lists (common variations)
    name_keys = ["Full Name", "Patient Name", "Name", "FullName"]
    visit_date_keys = ["Date of Visit", "Visit Date", "Date of visit", "Timestamp"]
    sex_keys = ["Sex", "Gender"]
    age_keys = ["Age (in years)", "Age ( In Years )", "Age", "Age (In Years)"]
    weight_keys = ["Weight", "Weight (kg)"]
    fbg_keys = [
        "Fasting Blood Glucose (FBG) before Pentat therapy ( mg/dL )",
        "Fasting Blood Glucose (FBG) before Pentat therapy ( mg/dL)",
        "FBG", "Fasting Blood Glucose", "FBG (mg/dL)"
    ]
    hba1c_keys = [
        "Most Recent HbA1c Before Starting Pentat Therapy (%)",
        "HbA1c at the latest follow-up (%)",
        "Most Recent HbA1c Before Starting Pentat Therapy (%)", "HbA1c"
    ]
    meds_keys = ["Medications Prescribed", "Current Medications", "Medications", "Treatment", "Medication"]
    met_keys = ["Met","Metformin","Met (mg)","Met (Dose)"]
    dpp4_keys = ["DPP-4"]
    glp1_keys = ["GLP-1", "GLP1"]
    sglt2_keys = ["SGLT2", "SGLT-2"]
    working_dx_keys = ["Working Diagnosis", "Working Dx", "Working_Diagnosis"]
    final_dx_keys = ["Final Diagnosis", "Final Dx", "Final_Diagnosis"]
    notes_keys = ["Doctor's Notes / Impression", "Doctor Notes / Impression", "Doctor Notes", "Doctor's Notes", "Notes"]
    pid_keys = ["Patient ID", "ID"]

    # Render cards: two per row
    cols_per_row = 2
    cols = st.columns(cols_per_row)
    for i, (_, row) in enumerate(filtered.iterrows()):
        col = cols[i % cols_per_row]

        # pull values using robust getter
        full_name = get_field(row, name_keys, fallback="Unnamed")
        visit_date = get_field(row, visit_date_keys, fallback="N/A")
        sex = get_field(row, sex_keys, fallback="N/A")
        age = get_field(row, age_keys, fallback="N/A")
        weight = get_field(row, weight_keys, fallback="N/A")
        fbg = get_field(row, fbg_keys, fallback="N/A")
        hba1c = get_field(row, hba1c_keys, fallback="N/A")
        patient_id = get_field(row, pid_keys, fallback="N/A")

        # Gather medications: try meds field first, else combine specific drug columns
        meds_text = get_field(row, meds_keys, fallback="")
        if meds_text == "" or meds_text == "N/A":
            med_parts = []
            for keys, label in [(met_keys,"Met"), (dpp4_keys,"DPP-4"), (glp1_keys,"GLP-1"), (sglt2_keys,"SGLT2")]:
                val = get_field(row, keys, fallback="")
                if val not in ("", "N/A"):
                    med_parts.append(val)
            meds_text = ", ".join(med_parts) if med_parts else "None"

        working_dx = get_field(row, working_dx_keys, fallback="N/A")
        final_dx = get_field(row, final_dx_keys, fallback="N/A")
        notes = get_field(row, notes_keys, fallback="")

        # Card HTML (safe)
        with col:
            st.markdown(f"""
                <div class="patient-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div class="patient-name">{full_name}</div>
                            <div class="patient-meta">ID: {patient_id} &nbsp;•&nbsp; {visit_date} &nbsp;•&nbsp; {sex}</div>
                        </div>
                    </div>

                    <div style="margin-top:0.6rem;">
                        <span class="metric">Age: {age}</span>
                        <span class="metric">Weight: {weight}</span>
                        <span class="metric">FBG: {fbg}</span>
                        <span class="metric">HbA1c: {hba1c}</span>
                    </div>

                    <div style="margin-top:0.7rem;">
                        💊 <b>Medications:</b> {meds_text}
                    </div>

                    <div style="margin-top:0.45rem;color:#6b7280;">
                        📋 <b>Working Dx:</b> {working_dx}
                    </div>
                    <div style="margin-top:0.25rem;color:#6b7280;">
                        📌 <b>Final Dx:</b> {final_dx}
                    </div>

                    {"<hr style='margin-top:8px;margin-bottom:8px;border:none;border-top:1px solid #eef2f6;' />" if notes else ""}
                    <div style="margin-top:0.4rem;color:#475569;font-size:0.95rem;">
                        {('📝 ' + notes) if notes else ''}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # bottom: download filtered or full data
    st.markdown("---")
    st.download_button(
        "⬇️ Download Displayed Data (CSV)",
        filtered.to_csv(index=False),
        "displayed_patients.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
