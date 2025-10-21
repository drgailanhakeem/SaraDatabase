import streamlit as st
import pandas as pd
from urllib.parse import quote, unquote
from datetime import date

# Google Sheet public CSV URL
sheet_url = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/gviz/tq?tqx=out:csv&gid=905987173"

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(sheet_url)
    return df

df = load_data()

# Apply CSS for light/dark mode toggle
dark_mode = st.toggle("🌙 Dark Mode", value=False)
if dark_mode:
    st.markdown("""
        <style>
        body, .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }
        .stTextInput, .stSelectbox, .stNumberInput, .stDateInput, .stTextArea {
            background-color: #1a1c23;
            color: white;
        }
        div[data-testid="stSidebar"] {
            background-color: #161a22;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        body, .stApp {
            background-color: white;
            color: black;
        }
        </style>
    """, unsafe_allow_html=True)

st.title("🏥 Patient Database")

# --- Search Existing Patient ---
st.subheader("🔍 Search Patient")
search_term = st.text_input("Search by Full Name")
filtered_df = df[df['Full Name'].str.contains(search_term, case=False, na=False)] if search_term else df

if not filtered_df.empty:
    selected_patient = st.selectbox("Select a patient:", filtered_df['Full Name'].unique())
else:
    selected_patient = None
    st.warning("No matching patient found.")

# --- Display Patient Data ---
if selected_patient:
    patient_data = df[df['Full Name'] == selected_patient]
    st.markdown(f"### 👤 Patient: {selected_patient}")

    for _, row in patient_data.iterrows():
        with st.expander(f"Visit on {row.get('Visit Date', 'Unknown Date')}"):
            for col, val in row.items():
                st.markdown(f"**{col}:** {val}")

# --- Add New Patient ---
st.subheader("➕ Add New Patient")

with st.form("add_patient_form"):
    full_name = st.text_input("Full Name")
    age = st.number_input("Age", min_value=0, max_value=120)
    sex = st.selectbox("Sex", ["Male", "Female"])
    phone = st.text_input("Phone Number")
    address = st.text_input("Address")
    diagnosis = st.text_area("Diagnosis / Comments")

    submit_patient = st.form_submit_button("Add Patient")

    if submit_patient:
        st.success(f"✅ Patient '{full_name}' added successfully (not synced yet).")

# --- Add New Visit for Existing Patient ---
st.subheader("🩺 Add New Visit")

with st.form("add_visit_form"):
    patient_for_visit = st.selectbox("Select Patient", df['Full Name'].unique())
    visit_date = st.date_input("Visit Date", date.today())
    hba1c = st.number_input("HbA1c (%)", min_value=0.0, max_value=20.0, step=0.1)
    fbg = st.number_input("Fasting Blood Glucose (mg/dL)", min_value=0, max_value=500)
    ppg = st.number_input("Postprandial Blood Glucose (mg/dL)", min_value=0, max_value=600)
    medications = st.multiselect("Medications", ["Metformin", "SU", "DPP-4", "SGLT2", "GLP-1", "Other"])
    notes = st.text_area("Visit Notes")

    submit_visit = st.form_submit_button("Add Visit")

    if submit_visit:
        st.success(f"✅ New visit added for '{patient_for_visit}' (not synced yet).")
