import streamlit as st
import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader, PdfWriter
import tempfile
import os
import re

st.set_page_config(page_title="GSTR-1 Reco Tool", layout="wide")
st.title("🏨 Final GSTR-1 Reconciliation Tool")

# API Setup
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key missing! Add GEMINI_API_KEY to Streamlit Secrets.")
    st.stop()

st.sidebar.header("Step 1: Upload Files")
pdf_file = st.sidebar.file_uploader("ReportViewer PDF", type=["pdf"])
excel_file = st.sidebar.file_uploader("GSTR-1 Excel (.xlsx)", type=["xlsx"])

if pdf_file and excel_file:
    if st.button("🚀 Run Accuracy-First Audit"):
        with st.spinner("Processing documents..."):
            try:
                # 1. SLICE PDF (Last 2 pages)
                reader = PdfReader(pdf_file)
                total_pages = len(reader.pages)
                writer = PdfWriter()
                start_page = max(0, total_pages - 2)
                for i in range(start_page, total_pages):
                    writer.add_page(reader.pages[i])
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    writer.write(tmp_pdf)
                    tmp_pdf_path = tmp_pdf.name
                gemini_pdf = genai.upload_file(path=tmp_pdf_path, display_name="SummaryPages")

                # 2. ROBUST EXCEL PROCESSING (Reads ALL sheets)
                all_sheets = pd.read_excel(excel_file, sheet_name=None)
                
                def get_global_sum(keywords):
                    total = 0.0
                    for sheet_name, df in all_sheets.items():
                        for col in df.columns:
                            if any(k.lower() in str(col).lower() for k in keywords):
                                # Clean data: convert to numeric, ignore errors, fill NaN with 0
                                clean_col = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.replace('₹', ''), errors='coerce').fillna(0)
                                total += clean_col.sum()
                    return round(total, 2)

                # Matching your requested components
                ex_tax = get_global_sum(["Taxable", "Assessed"])
                ex_cgst = get_global_sum(["CGST", "Central"])
                ex_sgst = get_global_sum(["SGST", "State"])
                ex_igst = get_global_sum(["IGST", "Integrated"])
                ex_cess = get_global_sum(["Cess"])
                ex_total = get_global_sum(["Invoice Value", "Total Amount"])

                # 3. AI ANALYSIS WITH STRICT FORMATTING
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"""
                You are a Senior GST Auditor. Perform a STRICT reconciliation.
                
                EXCEL CALCULATED TOTALS:
                - Taxable Value: {ex_tax}
                - CGST: {ex_cgst}
                - SGST: {ex_sgst}
                - IGST: {ex_igst}
                - Cess: {ex_cess}
                - Gross Total: {ex_total}

                PDF DATA:
                Find the 'Booked Revenue Summary' on the attached pages.

                OUTPUT FORMAT (Provide only this table):
                | Component | GSTR-1 Excel (₹) | PDF Export (₹) | Formula / Logic Used | Status | Discrepancy (₹) |
                | :--- | :--- | :--- | :--- | :--- | :--- |
                """
                
                response = model.generate_content([prompt, gemini_pdf])
                
                st.subheader("📊 Audit Report")
                st.markdown(response.text)

                # Debugging view
                with st.expander("Debug: All Sheets and Columns Found"):
                    for name, df in all_sheets.items():
                        st.write(f"Sheet: {name} | Columns: {list(df.columns)}")

                os.remove(tmp_pdf_path)
            except Exception as e:
                st.error(f"Error: {e}")
