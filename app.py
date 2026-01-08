import streamlit as st
import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader, PdfWriter
import tempfile
import os

# 1. Page Configuration
st.set_page_config(page_title="GSTR-1 Reco Tool", layout="wide")
st.title("🏨 Hotel GSTR-1 Reconciliation Tool")

# 2. API Key Security Check
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing API Key! Please add 'GEMINI_API_KEY' in Streamlit Advanced Settings.")
    st.stop()

# 3. Sidebar Uploaders
st.sidebar.header("Step 1: Upload Files")
pdf_file = st.sidebar.file_uploader("Upload ReportViewer PDF (Max 800MB)", type=["pdf"])
excel_file = st.sidebar.file_uploader("Upload GSTR-1 Excel (.xlsx)", type=["xlsx"])

# 4. Processing Logic
if pdf_file and excel_file:
    if st.button("🚀 Run Quota-Safe Audit"):
        with st.spinner("Analyzing data..."):
            try:
                # A. EXTRACT LAST PAGE (Bypasses the 250k token limit)
                reader = PdfReader(pdf_file)
                total_pages = len(reader.pages)
                writer = PdfWriter()
                writer.add_page(reader.pages[total_pages - 1]) # Always target the summary page
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    writer.write(tmp_pdf)
                    tmp_pdf_path = tmp_pdf.name

                # Upload slice to Google
                gemini_pdf = genai.upload_file(path=tmp_pdf_path, display_name="SummaryPage")

                # B. SUMMARIZE EXCEL LOCALLY (Prevents "429 Quota Exceeded")
                # We do the heavy math in Python so we don't send 10,000 rows to the AI
                df = pd.read_excel(excel_file)
                
                def safe_sum(keywords):
                    # Finds columns like 'Taxable', 'CGST', etc., regardless of exact name
                    for col in df.columns:
                        if any(k.lower() in str(col).lower() for k in keywords):
                            return round(pd.to_numeric(df[col], errors='coerce').sum(), 2)
                    return 0.0

                excel_data_summary = {
                    "Taxable Value": safe_sum(["Taxable", "Assessed"]),
                    "CGST": safe_sum(["CGST", "Central"]),
                    "SGST": safe_sum(["SGST", "State"]),
                    "IGST": safe_sum(["IGST", "Integrated"]),
                    "Cess": safe_sum(["Cess"]),
                    "Total Invoice Value": safe_sum(["Invoice Value", "Total Amount"])
                }

                # C. AI RECONCILIATION (Using Flash for speed)
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                prompt = f"""
                You are a GST Auditor. Perform a reconciliation.
                
                DATA FROM EXCEL (Calculated Totals):
                {excel_data_summary}

                DATA FROM PDF:
                Extract the 'Booked Revenue Summary' totals from the attached PDF page.

                OUTPUT FORMAT:
                | Component | GSTR-1 Excel (₹) | PDF Export (₹) | Status | Discrepancy (₹) |
                | :--- | :--- | :--- | :--- | :--- |
                | Taxable Value | | | | |
                | CGST | | | | |
                | SGST | | | | |
                | IGST | | | | |
                | Total Cess | | | | |
                | Gross Total | | | | |
                """
                
                response = model.generate_content([prompt, gemini_pdf])
                
                # 5. Display Result
                st.subheader("📊 Reconciliation Audit Report")
                st.markdown(response.text)

                # Cleanup
                os.remove(tmp_pdf_path)
                
            except Exception as e:
                st.error(f"Audit Error: {e}")
