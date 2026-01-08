import streamlit as st
import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader, PdfWriter
import tempfile
import os

st.set_page_config(page_title="GSTR-1 Reco Tool", layout="wide")
st.title("🏨 Hotel GSTR-1 Reconciliation Tool")

# API Setup
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Please add GEMINI_API_KEY to Streamlit Secrets!")
    st.stop()

st.sidebar.header("Step 1: Upload Files")
pdf_file = st.sidebar.file_uploader("Upload ReportViewer PDF", type=["pdf"])
excel_file = st.sidebar.file_uploader("Upload GSTR-1 Excel (.xlsx)", type=["xlsx"])

if pdf_file and excel_file:
    if st.button("🚀 Run Reconciliation"):
        with st.spinner("Extracting summary page & analyzing..."):
            try:
                # --- PDF SLICING: Extract ONLY the last page ---
                reader = PdfReader(pdf_file)
                total_pages = len(reader.pages)
                writer = PdfWriter()
                # We take the very last page (index -1)
                writer.add_page(reader.pages[total_pages - 1])
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    writer.write(tmp_pdf)
                    tmp_pdf_path = tmp_pdf.name

                # Upload only the 1-page PDF to Gemini
                gemini_pdf = genai.upload_file(path=tmp_pdf_path, display_name="SummaryPage")

                # --- EXCEL: Read all sheets ---
                excel_sheets = pd.read_excel(excel_file, sheet_name=None)
                excel_text = ""
                for name, df in excel_sheets.items():
                    excel_text += f"\n### Sheet: {name}\n{df.to_markdown()}\n"

                # --- AI PROCESSING: Using Gemini 2.5 Flash ---
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                prompt = f"""
                AUDIT TASK: Compare the 'Booked Revenue Summary' on this PDF page with the Excel data.
                
                EXCEL DATA:
                {excel_text}

                REQUIRED TABLE FORMAT:
                | Component | GSTR-1 Excel (₹) | PDF Export (₹) | Formula / Logic | Status | Discrepancy (₹) |
                | :--- | :--- | :--- | :--- | :--- | :--- |
                | Total Taxable Value | | | Sum of Taxable | | |
                | CGST Amount | | | Total Central Tax | | |
                | SGST Amount | | | Total State Tax | | |
                | IGST Amount | | | Total Integrated Tax | | |
                | Total Cess | | | Total Addl Cess | | |
                | Total Invoice Value | | | Gross Value | | |
                """
                
                response = model.generate_content([prompt, gemini_pdf])
                
                st.subheader("📊 Audit Results")
                st.markdown(response.text)

                # Cleanup
                os.remove(tmp_pdf_path)
                
            except Exception as e:
                st.error(f"Audit Error: {e}")
