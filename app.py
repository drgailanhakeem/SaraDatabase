import streamlit as st
import pandas as pd
from urllib.parse import quote, unquote
import datetime
from google.oauth2 import service_account
import gspread

# ===========================
# 🔗 CONFIGURATION
# ===========================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/gviz/tq?tqx=out:csv&gid=905987173"
SHEET_NAME = "Form Responses 1"  # change if your sheet has another name
BASE_URL = "https://saradatabase.streamlit.app/"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ===========================
# 🔐 GOOGLE AUTH (from st.secrets)
# ===========================
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
client = gspread.authorize(credentials)
sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"
).worksheet(SHEET_NAME)

# ===========================
# 📥 LOAD SHEET
# ===========================
df = pd.read_csv(SHEET_URL)

if "Patient ID" not in df.columns:
    df["Patient ID"] = [f"P{str(i+1).zfill(4)}" for i in range(len(df))]

# ===========================
# 💅 STYLE
# ===========================
st.markdown("""
<style>
    body { font-family: "Inter", sans-serif; }
    .patient-card {
        background-color: #1e1e1e10;
        padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.08);
        margin-bottom: 15px;
    }
    .visit-card {
        background-color: #1e1e1e08;
        border-radius: 12px;
        padding: 15px; margin-bottom: 12px;
    }
    .open-btn {
        text-decoration: none;
        background: #3b82f6;
        color: white !important;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# ===========================
# 🔍 QUERY PARAM
# ===========================
query_params = st.query_params
selected_id = query_params.get("id", None)

# ===========================
# 🧍‍♂️ VIEW SINGLE PATIENT
# ===========================
if selected_id:
    selected_id = unquote(selected_id)
    patient_data = df[df["Patient ID"] == selected_id]

    if not patient_data.empty:
        patient_info = patient_data.iloc[0]
        st.title(f"🧍 Patient: {patient_info['Full Name']}")
        st.write(f"**ID:** {patient_info['Patient ID']}")
        st.write(f"**Age:** {patient_info.get('Age ( In Years )', '—')}")
        st.write(f"**Gender:** {patient_info.get('Gender', '—')}")

        st.divider()
        st.subheader("📅 Visit History")

        if len(patient_data) > 0:
            st.dataframe(patient_data)
        else:
            st.info("No visit records yet.")

        # ===========================
        # ➕ ADD NEW VISIT
        # ===========================
        st.divider()
        st.subheader("➕ Add New Visit")

        with st.form("new_visit_form", clear_on_submit=True):
            visit_date = st.date_input("Visit Date", datetime.date.today())
            weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
            hba1c = st.number_input("HbA1c (%)", min_value=0.0, step=0.1)
            fbg = st.number_input("Fasting Blood Glucose (mg/dL)", min_value=0, step=1)
            ppg = st.number_input("Postprandial Blood Glucose (mg/dL)", min_value=0, step=1)

            meds = st.multiselect(
                "Medications used",
                ["Su", "Met", "DPP-4", "GLP-1", "SGLT2", "Other"]
            )

            notes = st.text_area("Notes (optional)")

            submitted = st.form_submit_button("Save Visit")

            if submitted:
                new_row = [
                    patient_info["Full Name"],
                    patient_info.get("Age ( In Years )", ""),
                    patient_info.get("Gender", ""),
                    visit_date.strftime("%Y-%m-%d"),
                    weight,
                    hba1c,
                    fbg,
                    ppg,
                    ",".join(meds),
                    notes,
                    patient_info["Patient ID"]
                ]
                sheet.append_row(new_row)
                st.success("✅ New visit added successfully!")
                st.rerun()
    else:
        st.error("Patient not found.")

# ===========================
# 📋 SEARCH / BROWSE PATIENTS
# ===========================
else:
    st.title("🩺 Patient Database Dashboard")
    search_query = st.text_input("Search by name or ID:")

    if search_query:
        filtered = df[df["Full Name"].str.contains(search_query, case=False, na=False) |
                      df["Patient ID"].str.contains(search_query, case=False, na=False)]
    else:
        filtered = df

    for _, row in filtered.iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"""
            <div class="patient-card">
                <b>{row['Full Name']}</b><br>
                ID: {row['Patient ID']}<br>
                Age: {row.get('Age ( In Years )', '—')} | Gender: {row.get('Gender', '—')}
            </div>
            """, unsafe_allow_html=True)
        with col2:
            encoded_id = quote(row["Patient ID"])
            link = f"{BASE_URL}?id={encoded_id}"
            st.markdown(f"<a href='{link}' class='open-btn'>Open</a>", unsafe_allow_html=True)
