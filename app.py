import streamlit as st
import pandas as pd
import uuid

# --- Load DataFrame ---
data = sheet.get_all_records()
df = pd.DataFrame(data)

# --- Ensure unique ID ---
if 'Patient ID' not in df.columns:
    df['Patient ID'] = [str(uuid.uuid4())[:8] for _ in range(len(df))]

st.title("🩺 Sara Patient Database")

# --- Routing ---
query_params = st.experimental_get_query_params()
selected_patient_id = query_params.get("patient", [None])[0]

if selected_patient_id:
    # Display individual patient profile
    patient_data = df[df['Patient ID'] == selected_patient_id]
    
    if not patient_data.empty:
        patient = patient_data.iloc[0]
        st.subheader(f"👤 {patient['Full Name']}")
        st.write(f"**Age:** {patient.get('Age', 'N/A')}")
        st.write(f"**Gender:** {patient.get('Gender', 'N/A')}")
        st.write(f"**Phone:** {patient.get('Phone Number', 'N/A')}")
        st.write(f"**Address:** {patient.get('Address', 'N/A')}")
        st.write(f"**Diagnosis:** {patient.get('Diagnosis', 'N/A')}")
        st.divider()

        st.markdown("### 📋 Add Visit")
        with st.form("add_visit_form"):
            new_visit = {}
            for col in df.columns:
                if col not in ['Patient ID', 'Full Name', 'Age', 'Gender']:
                    new_visit[col] = st.text_input(col)
            submitted = st.form_submit_button("Add Visit")
            if submitted:
                st.success("✅ Visit added successfully (simulation).")
    else:
        st.error("Patient not found in database.")
else:
    # --- Main page: show patient list ---
    st.header("🔍 Search Patients")
    search_term = st.text_input("Search by Full Name")

    if search_term:
        filtered_df = df[df['Full Name'].str.contains(search_term, case=False, na=False)]
    else:
        filtered_df = df

    for _, row in filtered_df.iterrows():
        patient_link = f"?patient={row['Patient ID']}"
        with st.expander(f"👤 {row['Full Name']} (Age: {row.get('Age', 'N/A')})"):
            st.markdown(f"[Open Patient Profile]({patient_link})")

    st.divider()
    st.subheader("➕ Add New Patient")
    with st.form("add_patient_form"):
        new_patient = {}
        for col in df.columns:
            new_patient[col] = st.text_input(col)
        submitted = st.form_submit_button("Add Patient")
        if submitted:
            st.success("✅ New patient added successfully (simulation).")
