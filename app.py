# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.title("My Google Sheet Data")

# Authenticate using your secrets
scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_info(
    st.secrets["sara-177@sara-database-97.iam.gserviceaccount.com"], scopes=scope
)
client = gspread.authorize(creds)

#Replace this URL with your own Google Sheet link
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/edit?gid=905987173#gid=905987173"
sheet = client.open_by_url(SHEET_URL).sheet1

# Get data from the first sheet
data = pd.DataFrame(sheet.get_all_records())

# Show the table
st.dataframe(data)
