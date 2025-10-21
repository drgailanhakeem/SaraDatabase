import streamlit as st
import pandas as pd
from urllib.parse import quote, unquote

# --- Load Google Sheet ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/gviz/tq?tqx=out:csv&gid=905987173"
df = pd.read_csv(SHEET_URL)

# --- Ensure unique patient ID column ---
if "Patient ID" not in df.columns:
    df["Patient ID"] = [f"P{str(i+1).zfill(4)}" for i in range(len(df))]

# --- Inject global CSS ---
st.markdown("""
<style>
    /* Base layout */
    body {
        font-family: "Inter", sans-serif;
        background-color: var(--background-color);
        transition: background 0.3s, color 0.3s;
    }

    /* Light & dark mode variables */
    @media (prefers-color-scheme: dark) {
        :root {
            --background-color: #0e1117;
            --card-bg: #1e2127;
            --text-color: #f0f0f0;
            --subtext-color: #9da0a6;
            --border-color: #2a2d34;
        }
    }

    @media (prefers-color-scheme: light) {
        :root {
            --background-color: #f8f9fa;
            --card-bg: #ffffff;
            --text-color: #202124;
            --subtext-color: #5f6368;
            --border-color: #e0e0e0;
        }
    }

    /* Patient card */
    .patient-card {
        background-color: var(--card-bg);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 15px;
        transition: transform 0.2s ease, box-shadow 0.3s ease;
    }

    .patient-card:hover {
        transform: scale(1.01);
        box-shadow: 0 6px 18px rgba(0,0,0,0.15);
    }

    .patient-name {
        font-size: 1.2rem;
        font-weight: 600;
        color: var(--text-color);
    }

    .patient-details p {
        margin: 2px 0;
        color: var(--subtext-color);
    }

    /* Visit card */
    .visit-card {
        background-color: var(--card-bg);
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08);
    }

    .visit-card p {
        margin: 4px 0;
        color: var(--subtext-color);
    }

    .visit-card strong {
        color: var(--text-color);
    }

    /* Link button */
    .open-btn {
        display: inline-block;
        text-decoration: none;
        background: #3b82f6;
        color: white !important;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 500;
        transition: background 0.2s;
    }
    .open-btn:hover {
        background: #2563eb;
    }

    /* Responsive design */
    @media (max-width: 768px) {
        .patient-card {
            padding: 15px;
        }
        .patient-name {
            font-size: 1.1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- App title ---
st.title("🩺 Patient Database Dashboard")

# --- Query parameters ---
query_params = st.query_params
selected_id = query_params.get("id", None)

# --- Base URL ---
BASE_URL = "https://saradatabase.streamlit.app/"

# --- Render patient info card ---
def render_patient_card(patient_row):
    st.markdown(f"""
    <div class="patient-card">
        <div class="patient-name">🧍‍♂️ {patient_row['Full Name']}</div>
        <div class="patient-details">
            <p><strong>ID:</strong> {patient_row['Patient ID']}</p>
            <p><strong>Age:</strong> {patient_row.get('Age ( In Years )', '—')}</p>
            <p><strong>Gender:</strong> {patient_row.get('Gender', '—')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Render visit info as styled cards ---
def render_visit_cards(visits_df):
    st.markdown("### 📅 Visit History")
    for _, visit in visits_df.iterrows():
        st.markdown(f"""
        <div class="visit-card">
            <p><strong>📆 Date:</strong> {visit.get('Visit Date', 'N/A')}</p>
            <p><strong>Weight:</strong> {visit.get('Weight (kg)', '—')} kg</p>
            <p><strong>HbA1c:</strong> {visit.get('HbA1c (%)', '—')}%</p>
            <p><strong>FBG:</strong> {visit.get('Fasting Blood Glucose (FBG) (mg/dL)', '—')} mg/dL</p>
            <p><strong>PPG:</strong> {visit.get('Postprandial Blood Glucose (PPG) (mg/dL)', '—')} mg/dL</p>
            <p><strong>Medications:</strong> {', '.join([str(visit.get(x, '')) for x in ['Su', 'Met', 'DPP-4', 'GLP-1', 'SGLT2', 'Other'] if pd.notna(visit.get(x)))}</p>
        </div>
        """, unsafe_allow_html=True)

# --- Single patient view ---
if selected_id:
    selected_id = unquote(selected_id)
    patient_data = df[df["Patient ID"] == selected_id]

    if not patient_data.empty:
        patient_info = patient_data.iloc[0]
        st.markdown("## 🧾 Patient Profile")
        render_patient_card(patient_info)
        render_visit_cards(patient_data)
    else:
        st.error("Patient not found.")

# --- Search / Browse view ---
else:
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
            st.markdown(f"<a href='{link}' class='open-btn'>🔗 Open Record</a>", unsafe_allow_html=True)
