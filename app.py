import streamlit as st
import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader, PdfWriter
import tempfile
import io
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
    if st.button("🚀 Run Full Audit"):
        with st.spinner("Slicing PDF to last page & analyzing..."):
            try:
                # --- NEW: Extract ONLY the last page to save tokens ---
                pdf_reader = PdfReader(pdf_file)
                last_page_index = len(pdf_reader.pages) - 1
                
                writer = PdfWriter()
                writer.add_page(pdf_reader.pages[last_page_index])
                
                # Save just that 1 page to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    writer.write(tmp)
                    tmp_path = tmp.name

                # Upload the 1-page PDF to Gemini
                gemini_pdf = genai.upload_file(path=tmp_path, display_name="LastPageSummary")

                # --- Handle Excel ---
                excel_data = pd.read_excel(excel_file, sheet_name=None)
                combined_text = ""
                for sheet_name, df in excel_data.items():
                    combined_text += f"\n--- Sheet: {sheet_name} ---\n{df.to_markdown()}"

                # --- Use Flash Model ---
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                prompt = f"""
                You are a Senior GST Auditor. Use the provided page (the last page of the report) 
                and the Excel data to create a Reconciliation Table.
                
                EXCEL DATA:
                {combined_text}

                TASK:
                Compare the 'Booked Revenue Summary' on this PDF page against the Excel totals.
                Provide the results in this EXACT table format:

                | Component | GSTR-1 Excel Value (₹) | PDF Export Value (₹) | Formula / Logic Used | Status | Discrepancy (₹) |
                | :--- | :--- | :--- | :--- | :--- | :--- |
                | Total Taxable Value | | | Aggregated HSN/B2B | | |
                | B2B Taxable Value | | | Total Registered Invoices | | |
                | CGST Amount | | | Total Central Tax | | |
                | SGST Amount | | | Total State Tax | | |
                | IGST Amount | | | Total Integrated Tax | | |
                | Total Cess | | | Total Additional Cess | | |
                | Total Invoice Value | | | Gross Value | | |
                """
                
                response = model.generate_content([prompt, gemini_pdf])
                
                st.subheader("📊 Reconciliation Result")
                st.markdown(response.text)

                os.remove(tmp_path)
                
            except Exception as e:
                st.error(f"Error: {e}")
