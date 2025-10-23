import streamlit as st
import pandas as pd

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="Patient EMR Dashboard", layout="wide", page_icon="🧠")

# ========== GOOGLE SHEET SETTINGS ==========
# ⚠️ Make sure your Google Sheet is shared as "Anyone with the link can view"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GKGJQQii5lrXvYNjk7mGt6t2VUY6n5BNqS9lkI_vRH0/"
SHEET_GID = "0"  # Usually 0 for the first sheet, but you can check the URL

# ========== LOAD DATA DIRECTLY ==========
@st.cache_data(ttl=300)
def load_data():
    csv_url = SHEET_URL.replace("/edit#", f"/export?format=csv&gid={SHEET_GID}")
    df = pd.read_csv(csv_url)
    df.columns = [c.strip() for c in df.columns]

    # ✅ Validate structure
    required_cols = [
        "Patient ID", "Full Name", "Age (in years)", "Sex",
        "Doctor's Name", "Date of Visit", "Working Diagnosis"
    ]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in Google Sheet: {', '.join(missing_cols)}")

    df = df.dropna(axis=1, how='all')
    return df

# ========== UI STYLE ==========
st.markdown("""
<style>
    .stApp { background-color: #f7f9fc; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stExpander {
        border-radius: 12px !important;
        border: 1px solid #ddd !important;
        background-color: #fff !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        padding: 0.3rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ========== MAIN APP ==========
try:
    patients_df = load_data()

    st.title("🧠 Patient EMR Dashboard")

    if patients_df.empty:
        st.warning("No patient records found in the Google Sheet.")
        st.stop()

    # ======= SIDEBAR FILTERS =======
    st.sidebar.header("🔍 Filters")
    search = st.sidebar.text_input("Search by name, ID, or diagnosis:")
    doctor_filter = st.sidebar.selectbox(
        "Doctor", ["All"] + sorted(patients_df["Doctor's Name"].dropna().unique())
    )
    sex_filter = st.sidebar.selectbox(
        "Sex", ["All"] + sorted(patients_df["Sex"].dropna().unique())
    )
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # ======= FILTER LOGIC =======
    filtered_df = patients_df.copy()

    if search:
        filtered_df = filtered_df[
            filtered_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        ]
    if doctor_filter != "All":
        filtered_df = filtered_df[filtered_df["Doctor's Name"] == doctor_filter]
    if sex_filter != "All":
        filtered_df = filtered_df[filtered_df["Sex"] == sex_filter]

    # ======= SUMMARY METRICS =======
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Total Patients", len(patients_df))
    col2.metric("🩺 Filtered Patients", len(filtered_df))
    col3.metric("♂️ Males", sum(patients_df["Sex"] == "Male"))
    col4.metric("♀️ Females", sum(patients_df["Sex"] == "Female"))

    # ======= PATIENT PROFILES =======
    st.subheader("🧾 Patient Profiles")

    if filtered_df.empty:
        st.info("No patients match the current filters.")
    else:
        for _, row in filtered_df.iterrows():
            with st.expander(f"👤 {row['Full Name']} — {row['Patient ID']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Age:** {row.get('Age (in years)', '')}")
                    st.markdown(f"**Sex:** {row.get('Sex', '')}")
                    st.markdown(f"**Date of Visit:** {row.get('Date of Visit', '')}")
                    st.markdown(f"**Doctor:** {row.get('Doctor\'s Name', '')}")
                    st.markdown(f"**Visit Type:** {row.get('Visit Type', '')}")
                with col2:
                    st.markdown(f"**Working Dx:** {row.get('Working Diagnosis', '')}")
                    st.markdown(f"**Final Dx:** {row.get('Final Diagnosis', '')}")
                    st.markdown(f"**Follow-Up:** {row.get('Follow-Up Date', '')}")

                st.divider()
                st.markdown(f"**HPI:** {row.get('HPI', '')}")
                st.markdown(f"**Medications Prescribed:** {row.get('Medications Prescribed', '')}")
                st.markdown(f"**Doctor Notes:** {row.get('Doctor\'s Notes / Impression', '')}")

    # ======= DOWNLOAD DATA =======
    st.download_button(
        "⬇️ Download Filtered Data as CSV",
        filtered_df.to_csv(index=False),
        "filtered_patients.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
