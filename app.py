import streamlit as st
import pandas as pd
from urllib.parse import quote, unquote
import datetime

# Load your Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/export?format=csv&gid=905987173"
df = pd.read_csv(SHEET_URL)

# Initialize dark mode toggle
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# Apply custom CSS for dark mode
def set_dark_mode():
    if st.session_state.dark_mode:
        st.markdown(
            """
            <style>
            body, .stApp {
                background-color: #121212 !important;
                color: white !important;
            }
            .stButton>button {
                background-color: #1f1f1f !important;
                color: white !important;
                border-radius: 10px !important;
                border: 1px solid #444 !important;
            }
            .stSelectbox, .stTextInput, .stTextArea, .stDateInput, .stNumberInput {
                background-color: #1e1e1e !important;
                color: white !important;
            }
            .stDataFrame, .stTable {
                background-color: #1f1f1f !important;
                color: white !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
set_dark_mode()

# Dark mode toggle
st.sidebar.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, key="dark_mode", on_change=set_dark_mode)

# App Title
st.title("Patient Database")

# Search functionality
search_term = st.text_input("🔍 Search patient by name:")
if search_term:
    filtered_df = df[df["Full Name"].str.contains(search_term, case=False, na=False)]
else:
    filtered_df = df.copy()

# Show filtered patients in modern cards
for _, row in filtered_df.iterrows():
    with st.container():
        st.markdown("---")
        st.subheader(f"🧍 {row['Full Name']}")
        st.write(f"**Age:** {row['Age (in years)']} | **Sex:** {row['Sex']} | **Visit Date:** {row['Date of Visit']}")
        st.write(f"**Doctor:** {row['Doctor\'s Name']}")
        st.write(f"**Chief Complaint:** {row['Cheif Compliant']}")
        with st.expander("View Full Details"):
            st.dataframe(row.to_frame().rename(columns={0: "Details"}))

        # Add Visit Section
        with st.expander("➕ Add Visit"):
            st.write("Enter visit details below:")
            visit_data = {}
            for col in df.columns:
                if col in ["Full Name", "Timestamp"]:
                    continue
                elif "Date" in col:
                    visit_data[col] = st.date_input(col, datetime.date.today())
                elif "Sex" in col:
                    visit_data[col] = st.selectbox(col, ["Male", "Female", "Other"])
                elif "Status" in col or "Use" in col or "Marital" in col:
                    visit_data[col] = st.selectbox(col, ["Yes", "No", "Unknown"])
                else:
                    visit_data[col] = st.text_input(col)
            if st.button(f"Submit Visit for {row['Full Name']}"):
                st.success(f"Visit for {row['Full Name']} recorded successfully (not yet synced to sheet).")

# Add New Patient Section
with st.expander("➕ Add New Patient"):
    st.write("Fill out the following form to add a new patient:")
    new_patient = {}
    for col in df.columns:
        if "Timestamp" in col:
            new_patient[col] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif "Date" in col:
            new_patient[col] = st.date_input(col, datetime.date.today())
        elif "Sex" in col:
            new_patient[col] = st.selectbox(col, ["Male", "Female", "Other"])
        elif "Status" in col or "Use" in col or "Marital" in col:
            new_patient[col] = st.selectbox(col, ["Yes", "No", "Unknown"])
        else:
            new_patient[col] = st.text_input(col)

    if st.button("Submit New Patient"):
        st.success(f"New patient '{new_patient['Full Name']}' added successfully (not yet synced to sheet).")
