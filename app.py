import streamlit as st
import pandas as pd
from urllib.parse import quote, unquote

# --- Load your Google Sheet ---
sheet_url = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/gviz/tq?tqx=out:csv&gid=905987173"
df = pd.read_csv(sheet_url)

st.title("🩺 Patient Database")

# --- Get query parameters ---
query_params = st.query_params
selected_patient = query_params.get("patient", None)

# --- Base URL of your deployed Streamlit app ---
BASE_URL = "https://saradatabase.streamlit.app/"

# --- Main logic ---
if selected_patient:
    selected_patient = unquote(selected_patient)
    st.subheader(f"📋 Data for {selected_patient}")
    
    # Filter patient's data
    patient_data = df[df["Full Name"].str.strip().str.lower() == selected_patient.strip().lower()]
    
    if not patient_data.empty:
        st.dataframe(patient_data)
    else:
        st.warning("No records found for this patient.")
else:
    st.subheader("👥 All Patients")
    st.dataframe(df)

    st.markdown("---")
    st.subheader("🔍 Search Patient and Generate Link")

    # --- Search bar ---
    search_query = st.text_input("Type a name to search:")
    if search_query:
        filtered_patients = df[df["Full Name"].str.contains(search_query, case=False, na=False)]
    else:
        filtered_patients = df

    # --- Show filtered patient list ---
    patient_list = sorted(filtered_patients["Full Name"].dropna().unique())
    patient_name = st.selectbox("Select a patient", patient_list)

    # --- Generate link for selected patient ---
    if st.button("Generate Link"):
        encoded_patient = quote(patient_name)
        link = f"{BASE_URL}?patient={encoded_patient}"

        st.success(f"Link for **{patient_name}** generated successfully!")
        st.code(link, language="text")
        st.markdown(f"[Open {patient_name}'s record]({link})", unsafe_allow_html=True)
