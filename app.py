import streamlit as st
import pandas as pd
from urllib.parse import quote, unquote

# --- Load your Google Sheet ---
sheet_url = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/export?format=csv&gid=905987173"
df = pd.read_csv(sheet_url)

st.title("Patient Database")

# --- Get query parameters ---
query_params = st.query_params
selected_patient = query_params.get("patient", None)

# --- Main logic ---
if selected_patient:
    selected_patient = unquote(selected_patient)
    st.subheader(f"Data for {selected_patient}")
    
    # Filter patient's data
    patient_data = df[df["Full Name"].str.strip().str.lower() == selected_patient.strip().lower()]
    
    if not patient_data.empty:
        st.dataframe(patient_data)
    else:
        st.warning("No records found for this patient.")
else:
    st.subheader("All Patients")
    st.dataframe(df)

    st.markdown("---")
    st.subheader("Generate Patient Link")

    # Dropdown to select a patient
    patient_name = st.selectbox("Select a patient", sorted(df["Full Name"].dropna().unique()))
    
    if st.button("Generate Link"):
        encoded_name = quote(patient_name)
        link = f"{st.runtime.scriptrunner.script_run_context.get_script_run_ctx().page_script_hash}?patient={encoded_name}"
        st.write("Patient link:")
        st.code(f"?patient={encoded_name}", language="text")
        st.markdown(f"[Open Patient Page](?patient={encoded_name})", unsafe_allow_html=True)
