import streamlit as st
import google.generativeai as genai
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
csv_files = st.sidebar.file_uploader("Upload GSTR-1 CSVs", accept_multiple_files=True, type=["csv"])

if pdf_file and csv_files:
    if st.button("🔍 Run Reconciliation"):
        with st.spinner("Uploading and analyzing large files..."):
            try:
                # 1. Save PDF to a temporary file locally
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_file.getvalue())
                    tmp_path = tmp.name

                # 2. Upload to Gemini Files API (Required for files > 20MB)
                gemini_pdf = genai.upload_file(path=tmp_path, display_name="ReportViewer")
                
                # 3. Process CSVs
                gemini_csvs = []
                for csv in csv_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as t_csv:
                        t_csv.write(csv.getvalue())
                        gemini_csvs.append(genai.upload_file(path=t_csv.name))

                # 4. Run Analysis
                model = genai.GenerativeModel("gemini-1.5-pro")
                prompt = "Compare the 'Booked Revenue Summary' on the final page of the PDF with the CSV totals. Provide a reconciliation table."
                
                response = model.generate_content([prompt, gemini_pdf, *gemini_csvs])
                
                st.subheader("📊 Results")
                st.markdown(response.text)

                # Cleanup
                os.remove(tmp_path)
                
            except Exception as e:
                st.error(f"Error: {e}")
