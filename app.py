import streamlit as st
import pandas as pd
from urllib.parse import quote, unquote

# --- Load Google Sheet ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/gviz/tq?tqx=out:csv&gid=905987173"
df = pd.read_csv(SHEET_URL)

# --- Ensure unique patient ID column ---
if "Patient ID" not in df.columns:
    df["Patient ID"] = [f"P{str(i+1).zfill(4)}" for i in range(len(df))]

# --- App title ---
st.title("🩺 Patient Database Dashboard")

# --- Handle query parameter ---
query_params = st.experimental_get_query_params()
selected_id = query_params.get("id", [None])[0]

# --- Base URL ---
BASE_URL = "https://saradatabase.streamlit.app/"

# --- Helper: Render patient card ---
def render_patient_card(patient_row):
    st.markdown(f"""
    <div style="
        background-color:#f9f9f9;
        padding:20px;
        border-radius:15px;
        box-shadow:0 2px 8px rgba(0,0,0,0.1);
        margin-bottom:15px;">
        <h3 style="margin-bottom:0;">🧍‍♂️ {patient_row['Full Name']}</h3>
        <p style="margin:5px 0;"><b>ID:</b> {patient_row['Patient ID']}</p>
        <p style="margin:5px 0;"><b>Age:</b> {patient_row.get('Age ( In Years )', '—')}</p>
        <p style="margin:5px 0;"><b>Gender:</b> {patient_row.get('Gender', '—')}</p>
    </div>
    """, unsafe_allow_html=True)


# --- If viewing a single patient ---
if selected_id:
    selected_id = unquote(selected_id)
    patient_data = df[df["Patient ID"] == selected_id]

    if not patient_data.empty:
        patient_info = patient_data.iloc[0]
        st.markdown("## 🧾 Patient Profile")
        render_patient_card(patient_info)

        st.markdown("### 📊 Visit History")
        st.dataframe(patient_data)
    else:
        st.error("Patient not found.")
else:
    # --- Search / Browse mode ---
    st.subheader("🔍 Search or Browse Patients")

    search_query = st.text_input("Search by name or ID:")
    if search_query:
        filtered = df[df["Full Name"].str.contains(search_query, case=False, na=False) |
                      df["Patient ID"].str.contains(search_query, case=False, na=False)]
    else:
        filtered = df

    for _, row in filtered.iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            render_patient_card(row)
        with col2:
            encoded_id = quote(row["Patient ID"])
            link = f"{BASE_URL}?id={encoded_id}"
            st.markdown(f"[🔗 Open Record]({link})", unsafe_allow_html=True)
