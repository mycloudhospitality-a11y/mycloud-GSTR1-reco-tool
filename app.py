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
pdf_file = st.sidebar.file_uploader("Upload ReportViewer PDF (Max 800MB)", type=["pdf"])
excel_file = st.sidebar.file_uploader("Upload GSTR-1 Excel (.xlsx)", type=["xlsx"])

if pdf_file and excel_file:
    st.sidebar.success("Both files uploaded!")
    
    if st.button("🔍 Run Reconciliation"):
        with st.spinner("Processing large PDF and converting Excel..."):
            try:
                # --- Part A: Handle the 700MB PDF ---
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_file.getvalue())
                    tmp_path = tmp.name

                # Upload to Gemini staging area
                gemini_pdf = genai.upload_file(path=tmp_path, display_name="ReportViewer")

                # --- Part B: Handle the .xlsx Excel ---
                # We read the Excel and convert it to a Markdown string for the AI
                df = pd.read_excel(excel_file)
                excel_text = df.to_markdown() # Converting to text so Gemini can 'read' it

                # --- Part C: Run Reconciliation ---
                model = genai.GenerativeModel("gemini-2.5-pro")
                
                prompt = f"""
                You are a GST Auditor. 
                1. Look at the 'Booked Revenue Summary' on the final page of the uploaded PDF.
                2. Compare it with the following data from the GSTR-1 Excel file:
                
                {excel_text}
                
                3. Provide a reconciliation table showing: Component, Books Value, GSTR-1 Value, and Difference.
                """
                
                response = model.generate_content([prompt, gemini_pdf])
                
                st.subheader("📊 Reconciliation Result")
                st.markdown(response.text)

                # Cleanup local temp file
                os.remove(tmp_path)
                
            except Exception as e:
                st.error(f"Error during processing: {e}")
