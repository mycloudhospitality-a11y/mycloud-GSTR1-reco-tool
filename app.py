import streamlit as st
import google.generativeai as genai
import pandas as pd
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
    if st.button("🚀 Run Full Audit"):
        with st.spinner("Analyzing 1,100+ pages and calculating Excel totals..."):
            try:
                # 1. Handle PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_file.getvalue())
                    tmp_path = tmp.name
                gemini_pdf = genai.upload_file(path=tmp_path, display_name="HotelReport")

                # 2. Read ALL Sheets from Excel to find the data
                excel_data = pd.read_excel(excel_file, sheet_name=None)
                combined_text = ""
                for sheet_name, df in excel_data.items():
                    combined_text += f"\n--- Sheet: {sheet_name} ---\n{df.to_markdown()}"

                # 3. Use Gemini 2.5 Flash
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                # THE "GOLDEN PROMPT" for your specific table format
                prompt = f"""
                You are a Senior GST Auditor. Your goal is to create a formal Reconciliation Table.
                
                SOURCES:
                1. PDF: Look at 'Booked Revenue Summary' on the very last page (Page 1160).
                2. EXCEL DATA: Summarize the actual numerical values from these sheets:
                {combined_text}

                TASK:
                Compare the PDF 'Total' row against the sum of the Excel data. 
                Ignore template instructions; look for the actual numbers.

                REQUIRED OUTPUT TABLE FORMAT (Markdown):
                | Component | GSTR-1 Excel Value (₹) | PDF Export Value (₹) | Formula / Logic Used | Status | Discrepancy (₹) |
                | :--- | :--- | :--- | :--- | :--- | :--- |
                | Total Taxable Value | | | Aggregated HSN/B2B | | |
                | B2B Taxable Value | | | Total Registered Invoices | | |
                | CGST Amount | | | Total Central Tax | | |
                | SGST Amount | | | Total State Tax | | |
                | IGST Amount | | | Total Integrated Tax | | |
                | Total Cess | | | Total Additional Cess | | |
                | Total Invoice Value | | | Gross Value | | |
                | Exempted/Non-GST | | | Non-taxable supplies | | |
                | Advances Adjusted | | | Previous Advance Tax | | |
                """
                
                response = model.generate_content([prompt, gemini_pdf])
                
                st.subheader("📊 Reconciliation Result")
                st.markdown(response.text)

                os.remove(tmp_path)
                
            except Exception as e:
                st.error(f"Error: {e}")
