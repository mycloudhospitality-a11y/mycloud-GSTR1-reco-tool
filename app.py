import streamlit as st
import google.generativeai as genai
import pandas as pd
import tempfile
import os

st.set_page_config(page_title="GSTR-1 Reco Tool", layout="wide")
st.title("🏨 MyCloud GSTR-1 Reconciliation Tool")

# API Setup
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Please add GEMINI_API_KEY to Streamlit Secrets!")
    st.stop()

st.sidebar.header("Step 1: Upload Files")
pdf_file = st.sidebar.file_uploader("Upload ReportViewer PDF (Max 800MB)", type=["pdf"])
excel_file = st.sidebar.file_uploader("Upload GSTR-1 Excel (.xlsx)", type=["xlsx"])

if pdf_file and excel_file:
    if st.button("🚀 Start Reconciliation"):
        with st.spinner("Processing... Using Flash model to stay within free quota."):
            try:
                # 1. Handle Large PDF via Files API
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_file.getvalue())
                    tmp_path = tmp.name

                # Staging the file on Google's server (Free for 48hrs)
                gemini_pdf = genai.upload_file(path=tmp_path, display_name="HotelReport")

                # 2. Convert Excel to Text
                df = pd.read_excel(excel_file)
                excel_summary = df.to_markdown()

                # 3. Use the High-Limit Flash Model
                # Gemini 2.5 Flash is the 'workhorse' for free users in 2026
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                prompt = f"""
                AUDIT TASK:
                1. Navigate to the VERY LAST PAGE of the attached PDF. 
                2. Locate the table named 'Booked Revenue Summary'.
                3. Compare those totals with this GSTR-1 Excel data:
                
                {excel_summary}
                
                4. Output a Reconciliation Table: [Component | Books | GSTR-1 | Diff | Status]
                """
                
                response = model.generate_content([prompt, gemini_pdf])
                
                st.subheader("📊 Reconciliation Result")
                st.markdown(response.text)

                # Cleanup
                os.remove(tmp_path)
                
            except Exception as e:
                st.error(f"Error: {e}")
