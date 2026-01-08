import streamlit as st
import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader, PdfWriter
import tempfile
import os

st.set_page_config(page_title="GSTR-1 Reco Tool", layout="wide")
st.title("🏨 Final GSTR-1 Reconciliation Tool")

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
        with st.spinner("Hunting for numbers in all Excel sheets..."):
            try:
                # 1. PDF PROCESSING (Last 2 pages)
                reader = PdfReader(pdf_file)
                writer = PdfWriter()
                start_page = max(0, len(reader.pages) - 2)
                for i in range(start_page, len(reader.pages)):
                    writer.add_page(reader.pages[i])
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    writer.write(tmp_pdf)
                    tmp_pdf_path = tmp_pdf.name
                gemini_pdf = genai.upload_file(path=tmp_pdf_path, display_name="Summary")

                # 2. ROBUST EXCEL SCANNER
                # Load every single sheet in the file
                all_sheets = pd.read_excel(excel_file, sheet_name=None)
                
                def deep_search_sum(keywords):
                    total = 0.0
                    for name, df in all_sheets.items():
                        for col in df.columns:
                            # Check if column name contains any of our keywords
                            if any(k.lower() in str(col).lower() for k in keywords):
                                # Clean: remove commas, currency, and spaces
                                s = df[col].astype(str).str.replace(r'[^\d.]', '', regex=True)
                                total += pd.to_numeric(s, errors='coerce').fillna(0).sum()
                    return round(total, 2)

                # These keywords are designed to catch standard GSTR-1 headers
                ex_data = {
                    "Taxable": deep_search_sum(["Taxable Value", "Taxable Amt", "Assessed"]),
                    "CGST": deep_search_sum(["CGST", "Central Tax"]),
                    "SGST": deep_search_sum(["SGST", "State Tax"]),
                    "IGST": deep_search_sum(["IGST", "Integrated Tax"]),
                    "Cess": deep_search_sum(["Cess"]),
                    "Total": deep_search_sum(["Invoice Value", "Total Value", "Total Amount"])
                }

                # 3. AI RECONCILIATION
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"""
                AUDIT TASK: Reconcile the 'Booked Revenue Summary' on the PDF against these Excel totals:
                Excel Totals: {ex_data}

                OUTPUT THE TABLE:
                | Component | GSTR-1 Excel (₹) | PDF Export (₹) | Formula / Logic Used | Status | Discrepancy (₹) |
                | :--- | :--- | :--- | :--- | :--- | :--- |
                """
                
                response = model.generate_content([prompt, gemini_pdf])
                st.subheader("📊 Audit Report")
                st.markdown(response.text)

                os.remove(tmp_pdf_path)
            except Exception as e:
                st.error(f"Error: {e}")
