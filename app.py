import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sara Patient Database", layout="wide")

# --- DARK MODE TOGGLE ---
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

# --- AUTH ---
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(st.secrets["sheet"]["sheet_name"])
    visits_sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet("Visits")
    st.success("✅ Successfully connected to Google Sheet")
except Exception as e:
    st.error(f"❌ Google Sheets Connection Failed: {e}")
    st.stop()


# --- CACHE SHEET DATA ---
@st.cache_data(ttl=300)
def load_data():
    patients = pd.DataFrame(sheet.get_all_records())
    visits = pd.DataFrame(visits_sheet.get_all_records())
    return patients, visits


try:
    df, visits_df = load_data()
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.stop()

st.title("🩺 Sara Patient Database")

# --- SEARCH ---
st.subheader("🔍 Search Patients")
search_query = st.text_input("Search by Full Name").strip().lower()
filtered_df = df[df["Full Name"].str.lower().str.contains(search_query)] if search_query else df

# --- DISPLAY PATIENTS ---
if not filtered_df.empty:
    for _, row in filtered_df.iterrows():
        patient_id = row.get("Patient ID", "Unknown")
        with st.expander(f"👤 {row['Full Name']} (ID: {patient_id})"):
            col1, col2 = st.columns(2)
            with col1:
                for col in df.columns[:len(df.columns)//2]:
                    st.markdown(f"**{col}:** {row.get(col, '')}")
            with col2:
                for col in df.columns[len(df.columns)//2:]:
                    st.markdown(f"**{col}:** {row.get(col, '')}")

            # --- Display Visits ---
            if not visits_df.empty:
                patient_visits = visits_df[visits_df["Patient ID"] == patient_id]
                if not patient_visits.empty:
                    st.markdown("### 🩹 Patient Visits")
                    for _, visit in patient_visits.iterrows():
                        with st.container():
                            st.markdown(f"**Visit ID:** {visit.get('Visit ID', 'N/A')}")
                            st.markdown(f"**Date of Visit:** {visit.get('Date of Visit', 'N/A')}")
                            st.markdown(f"**Doctor:** {visit.get('Doctor\'s Name', 'N/A')}")
                            st.markdown(f"**Diagnosis:** {visit.get('Final Diagnosis', 'N/A')}")
                            st.markdown(f"**Notes:** {visit.get('Doctor\'s Notes / Impression', 'N/A')}")
                            st.divider()
                else:
                    st.info("No visits recorded yet for this patient.")
else:
    st.info("No patients found.")

# --- ADD NEW PATIENT ---
with st.expander("➕ Add New Patient"):
    st.write("Fill in the patient details below:")
    new_data = {}
    columns = list(df.columns)

    for i, col in enumerate(columns):
        key = f"patient_{i}"
        if col.lower() in ["timestamp"]:
            new_data[col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif "date of birth" in col.lower():
            # Allow older years (1900–2025)
            new_data[col] = st.date_input(col, min_value=datetime(1900, 1, 1).date(), max_value=datetime(2025, 12, 31).date(), key=key)
        elif "date" in col.lower():
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
            new_data[col] = st.multiselect(col, ["Diabetes", "Hypertension", "Asthma", "Heart Disease", "Epilepsy", "None"], key=key)
        elif "duration" in col.lower():
            new_data[col] = st.text_input(col + " (e.g. 3 days / 2 weeks / 6 months)", key=key)
        else:
            new_data[col] = st.text_input(col, key=key)

    if st.button("✅ Add Patient"):
        try:
            # Convert all dates/times/multiselects to strings
            for k, v in new_data.items():
                if isinstance(v, (datetime, pd.Timestamp)):
                    new_data[k] = v.strftime("%Y-%m-%d %H:%M:%S")
                elif hasattr(v, "isoformat"):  # date or time
                    new_data[k] = v.isoformat()
                elif isinstance(v, list):
                    new_data[k] = ", ".join(v)
                else:
                    new_data[k] = str(v)

            # Generate a unique patient ID
            patient_id = f"pt{len(df) + 1}"
            new_data["Patient ID"] = patient_id

            sheet.append_row(list(new_data.values()))
            st.success(f"✅ New patient added successfully! (ID: {patient_id})")
            st.rerun()
        except Exception as e:
            st.error(f"Error adding patient: {e}")


# --- ADD NEW VISIT ---
with st.expander("🩺 Add New Visit"):
    st.subheader("➕ Record a Visit")

    if "Visit ID" in visits_df.columns and not visits_df.empty:
        last_visit_id_num = max([int(str(i).replace("vt", "")) for i in visits_df["Visit ID"].astype(str) if str(i).startswith("vt")] or [0])
        new_visit_id = f"vt{last_visit_id_num + 1:03d}"
    else:
        new_visit_id = "vt001"

    st.markdown(f"**🆔 Visit ID:** `{new_visit_id}`")

    visit_data = {"Visit ID": new_visit_id}

    patient_names = df["Full Name"].tolist() if not df.empty else []
    selected_patient = st.selectbox("Select Patient", patient_names)
    if selected_patient:
        patient_id = df.loc[df["Full Name"] == selected_patient, "Patient ID"].values[0]
        visit_data["Patient ID"] = patient_id

    for col in visits_df.columns:
        if col in ["Visit ID", "Patient ID", "Timestamp"]:
            continue

        key = f"visit_{col.replace(' ', '_')}"

        if "date" in col.lower():
            visit_data[col] = st.date_input(col, key=key)
        elif "time" in col.lower():
            visit_data[col] = st.time_input(col, key=key).strftime("%H:%M")
        elif "sex" in col.lower():
            visit_data[col] = st.selectbox(col, ["Male", "Female", "Other"], key=key)
        elif "duration" in col.lower():
            visit_data[col] = st.text_input(col, placeholder="e.g., 3 days", key=key)
        else:
            visit_data[col] = st.text_input(col, key=key)

    if st.button("💾 Add Visit"):
        try:
            visits_sheet.append_row(list(visit_data.values()))
            st.success(f"Visit for {selected_patient} added successfully!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error adding visit: {e}")
