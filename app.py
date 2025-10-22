import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date, time

# --- PAGE CONFIG ---
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

# --- AUTHENTICATION ---
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["sheet"]["sheet_id"]).worksheet(st.secrets["sheet"]["sheet_name"])
    st.success("✅ Successfully connected to Google Sheet")
except Exception as e:
    st.error(f"❌ Google Sheets Connection Failed: {e}")
    st.stop()

# --- LOAD DATA ---
try:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.stop()

st.title("🩺 Sara Patient Database")

# --- SEARCH PATIENT ---
st.subheader("🔍 Search Patients")
search_query = st.text_input("Search by Full Name").strip().lower()

if search_query:
    filtered_df = df[df["Full Name"].str.lower().str.contains(search_query)]
else:
    filtered_df = df

# --- DISPLAY PATIENTS NICELY ---
if not filtered_df.empty:
    for i, row in filtered_df.iterrows():
        patient_id = row.get("Patient ID", f"pt{i+1}")  # auto-generate if missing

        with st.expander(f"👤 {row['Full Name']} (Age: {row.get('Age (in years)', 'N/A')})"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Patient ID:** {patient_id}")
                st.markdown(f"**Sex:** {row.get('Sex', '')}")
                st.markdown(f"**Address:** {row.get('Address', '')}")
                st.markdown(f"**Date of Visit:** {row.get('Date of Visit', '')}")
                st.markdown(f"**Doctor's Name:** {row.get('Doctor\'s Name', '')}")
                st.markdown(f"**Chief Complaint:** {row.get('Cheif Compliant', '')}")
                st.markdown(f"**Onset:** {row.get('Onset', '')}")
            with col2:
                st.markdown(f"**Working Diagnosis:** {row.get('Working Diagnosis', '')}")
                st.markdown(f"**Final Diagnosis:** {row.get('Final Diagnosis', '')}")
                st.markdown(f"**Medications Prescribed:** {row.get('Medications Prescribed', '')}")
                st.markdown(f"**Follow-Up Date:** {row.get('Follow-Up Date', '')}")
                st.markdown(f"**Doctor's Notes / Impression:** {row.get('Doctor\'s Notes / Impression', '')}")

            # --- DELETE PATIENT BUTTON ---
            st.markdown("---")
            delete_col1, delete_col2 = st.columns([1, 4])
            with delete_col1:
                if st.button(f"🗑️ Delete {row['Full Name']}", key=f"delete_{patient_id}"):
                    confirm = st.warning(
                        f"Are you sure you want to permanently delete all data for **{row['Full Name']}**?",
                        icon="⚠️"
                    )
                    if st.button(f"✅ Confirm Delete {row['Full Name']}", key=f"confirm_delete_{patient_id}"):
                        try:
                            # Reload sheet to ensure fresh data
                            all_data = sheet.get_all_records()
                            df_all = pd.DataFrame(all_data)

                            # Find all matching rows by Patient ID (preferred) or by Full Name
                            if "Patient ID" in df_all.columns and patient_id in df_all["Patient ID"].values:
                                indexes_to_delete = df_all.index[df_all["Patient ID"] == patient_id].tolist()
                            else:
                                indexes_to_delete = df_all.index[df_all["Full Name"] == row["Full Name"]].tolist()

                            # Reverse so deleting rows doesn't shift indexes
                            for idx in sorted(indexes_to_delete, reverse=True):
                                sheet.delete_rows(idx + 2)  # +2 for header row + 1-indexed sheet

                            st.success(f"✅ Deleted all records for {row['Full Name']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error deleting patient: {e}")
else:
    st.info("No patients found.")

# --- ADD NEW PATIENT ---
with st.expander("➕ Add New Patient"):
    st.write("Fill in the patient details below:")
    new_data = {}
    columns = list(df.columns)

    # Auto-generate unique ID
    if "Patient ID" in df.columns and not df.empty:
        next_id = f"pt{len(df) + 1}"
    else:
        next_id = "pt1"
    new_data["Patient ID"] = next_id

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
            # Convert all date/time objects to strings
            for k, v in new_data.items():
                if isinstance(v, (datetime, date)):
                    new_data[k] = v.strftime("%Y-%m-%d")
            sheet.append_row(list(new_data.values()))
            st.success(f"✅ New patient {new_data.get('Full Name', '')} added successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error adding patient: {e}")

# --- ADD NEW VISIT ---
with st.expander("🩹 Add New Visit"):
    st.write("Fill in visit details for an existing patient:")
    visit_data = {}
    columns = list(df.columns)

    for i, col in enumerate(columns):
        key = f"visit_{i}"  # Unique key for visit form
        if col.lower() in ["timestamp"]:
            visit_data[col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif "date" in col.lower():
            visit_data[col] = st.date_input(col, key=key)
        elif "sex" in col.lower():
            visit_data[col] = st.selectbox(col, ["Male", "Female", "Other"], key=key)
        elif "smoking" in col.lower():
            visit_data[col] = st.selectbox(col, ["Never", "Former", "Current"], key=key)
        elif "alcohol" in col.lower():
            visit_data[col] = st.selectbox(col, ["No", "Occasionally", "Regularly"], key=key)
        elif "substance" in col.lower():
            visit_data[col] = st.selectbox(col, ["No", "Yes"], key=key)
        elif "marital" in col.lower():
            visit_data[col] = st.selectbox(col, ["Single", "Married", "Divorced", "Widowed"], key=key)
        else:
            visit_data[col] = st.text_input(col, key=key)

    if st.button("💾 Add Visit"):
        try:
            for k, v in visit_data.items():
                if isinstance(v, (datetime, date)):
                    visit_data[k] = v.strftime("%Y-%m-%d")
            sheet.append_row(list(visit_data.values()))
            st.success("✅ New visit added successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error adding visit: {e}")
