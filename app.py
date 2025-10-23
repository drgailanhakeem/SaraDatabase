import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime

# ---------------- GOOGLE SHEETS CONNECTION ----------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL).sheet1

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=300)
def load_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

# ---------------- APP LAYOUT ----------------
st.set_page_config(page_title="Patient Database", layout="wide")

st.markdown("""
    <style>
        body {
            font-family: 'Inter', sans-serif;
        }
        .title {
            font-size: 30px;
            font-weight: 700;
            color: #333;
        }
        .subtitle {
            font-size: 16px;
            color: #666;
        }
        .card {
            background-color: #f9f9fb;
            border: 1px solid #e0e0e0;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }
        .label {
            font-weight: 600;
            color: #444;
        }
        .value {
            color: #000;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------- LOAD AND DISPLAY DATA ----------------
try:
    df = load_data()
    st.markdown("<div class='title'>Patient Records</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Select a patient to view full details.</div>", unsafe_allow_html=True)
    st.divider()

    if df.empty:
        st.warning("No data found in the Google Sheet.")
    else:
        # Dropdown for patient selection
        patient_list = df["Full Name"].dropna().unique().tolist()
        selected_patient = st.selectbox("Select Patient:", patient_list)

        if selected_patient:
            patient_data = df[df["Full Name"] == selected_patient]

            if not patient_data.empty:
                patient = patient_data.iloc[0].to_dict()

                st.markdown(f"<h3 style='margin-top:30px; color:#2b5876;'>🧾 {patient.get('Full Name', 'Unnamed Patient')}</h3>", unsafe_allow_html=True)
                st.write("---")

                # Display all columns, even if blank
                for key, value in patient.items():
                    display_value = value if str(value).strip() != "" else "N/A"
                    st.markdown(f"""
                        <div class='card'>
                            <span class='label'>{key}</span><br>
                            <span class='value'>{display_value}</span>
                        </div>
                    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
