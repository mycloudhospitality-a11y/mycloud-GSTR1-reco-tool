import streamlit as st
import google.generativeai as genai
import pandas as pd
import time

# 1. Page Config
st.set_page_config(page_title="GSTR-1 Reco Tool", layout="wide")
st.title("🏨 MyCloud GSTR-1 Reconciliation Tool")

# 2. API Setup from Streamlit Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Please add GEMINI_API_KEY to Streamlit Secrets!")
    st.stop()

# 3. Sidebar - The Upload Zone
st.sidebar.header("Step 1: Upload Files")
pdf_file = st.sidebar.file_uploader("Upload ReportViewer PDF", type=["pdf"])
csv_files = st.sidebar.file_uploader("Upload GSTR-1 CSVs (HSN, B2B, B2CS)", accept_multiple_files=True, type=["csv"])

# 4. Main Body
if pdf_file and csv_files:
    st.success("Files ready for processing!")
    
    if st.button("🔍 Run Reconciliation"):
        with st.spinner("Analyzing data... This may take a minute for large PDFs."):
            try:
                # Instruction for the AI
                system_prompt = """
                Extract 'Booked Revenue Summary' from the final page of the PDF. 
                Reconcile it with the uploaded CSV totals. 
                Output a clean table with: Component, GSTR-1 Value, Books Value, Difference, and Status.
                """
                
                model = genai.GenerativeModel("gemini-1.5-pro")
                
                # Note: Sending files directly to API
                response = model.generate_content([system_prompt, pdf_file, *csv_files])
                
                st.subheader("📊 Reconciliation Result")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
else:
    st.info("Waiting for PDF and CSV uploads in the sidebar...")
