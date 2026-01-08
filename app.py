import streamlit as st
import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader, PdfWriter
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
pdf_file = st.sidebar.file_uploader("Upload ReportViewer PDF", type=["pdf"])
excel_file = st.sidebar.file_uploader("Upload GSTR-1 Excel (.xlsx)", type=["xlsx"])

if pdf_file and excel_file:
    if st.button("🚀 Run Quota-Safe Audit"):
        with st.spinner("Summarizing data locally to avoid API limits..."):
            try:
                # 1. PROCESS PDF (Slicing to last page)
                reader = PdfReader(pdf_file)
                writer = PdfWriter()
                writer.add_page(reader.pages[len(reader.pages) - 1])
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    writer.write(tmp_pdf)
                    tmp_pdf_path = tmp_pdf.name
                gemini_pdf = genai.upload_file(path=tmp_pdf_path, display_name="Summary")

                # 2. PROCESS EXCEL LOCALLY (The "Quota Saver")
                # We calculate totals in Python instead of
