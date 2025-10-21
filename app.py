import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import gspread
from gspread_dataframe import set_with_dataframe
from urllib.parse import quote, unquote

# ======================================
# CONFIG
# ======================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"
SHEET_NAME = "Form Responses 1"
BASE_URL = "https://saradatabase.streamlit.app/"

# ======================================
# AUTH
# ======================================
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
client = gspread.authorize(credentials)
sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)

# ======================================
# LOAD DATA
# ======================================
data = sheet.get_all_records()
df = pd.DataFrame(data)

if "Patient ID" not in df.columns:
    df["Patient ID"] = [f"P{str(i+1).zfill(4)}" for i in range(len(df))]

# ======================================
# STYLING
# ======================================
st.markdown("""
<style>
    .block-container {max-width: 1000px !important;}
    .title {font-size: 28px; font-weight: 700; margin-bottom: 10px;}
    .card {
        background: #f8f9fa;
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 3px 8px rgba(0,0,0,0.08);
        margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

# ======================================
# QUERY PARAMS
# ======================================
query_params = st.query_params
selected_id = query_params.get("id", None)

# ======================================
# PATIENT PAGE
# ======================================
if selected_id:
    selected_id = unquote(selected_id)
    patient_data = df[df["Patient ID"] == selected_id]

    if not patient_data.empty:
        patient_name = patient_data.iloc[0]["Full Name"]
        st.markdown(f"<div class='title'>🧍 {patient_name}</div>", unsafe_allow_html=True)

        # Show editable data
        edited_df = st.data_editor(
            patient_data,
            use_container_width=True,
            num_rows="dynamic",
            key="edit_patient",
        )

        # Save changes
        if st.button("💾 Save Changes"):
            df.update(edited_df)
            set_with_dataframe(sheet, df)
            st.success("✅ Saved successfully to Google Sheets!")

        st.divider()
        if st.button("↩️ Back to All Patients"):
            st.query_params.clear()
            st.rerun()
    else:
        st.error("❌ Patient not found.")

# ======================================
# MAIN PAGE
# ======================================
else:
    st.markdown("<div class='title'>🩺 Patient Database Dashboard</div>", unsafe_allow_html=True)

    search = st.text_input("Search by name or ID:")
    if search:
        filtered = df[df["Full Name"].str.contains(search, case=False, na=False) |
                      df["Patient ID"].str.contains(search, case=False, na=False)]
    else:
        filtered = df

    st.dataframe(filtered)

    # Select a patient
    patient_name = st.selectbox("Select a patient to view/edit:", filtered["Full Name"].unique())
    if st.button("Open Patient Page"):
        patient_id = df.loc[df["Full Name"] == patient_name, "Patient ID"].iloc[0]
        encoded = quote(patient_id)
        st.query_params["id"] = encoded
        st.rerun()
