import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Patient Profiles", layout="wide")

# Google Sheets setup
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/"
SHEET_NAME = "Form Responses 1"

# Google API connection
def connect_to_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(credentials)
    return client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)

# Load all data (no filtering)
def load_data(sheet):
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df.columns = [c.strip() for c in df.columns]
    return df

# Main app
st.title("🧠 Patient Profiles Viewer")

try:
    sheet = connect_to_google_sheet()
    patients_df = load_data(sheet)

    if patients_df.empty:
        st.warning("No patient records found in the Google Sheet.")
    else:
        st.success(f"Loaded {len(patients_df)} patient records.")
        st.dataframe(patients_df, use_container_width=True)

        # Optional: search bar for quick lookup
        search = st.text_input("🔍 Search by name, ID, or diagnosis:")
        if search:
            filtered = patients_df[
                patients_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            ]
            if not filtered.empty:
                st.dataframe(filtered, use_container_width=True)
            else:
                st.warning("No matching records found.")
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
