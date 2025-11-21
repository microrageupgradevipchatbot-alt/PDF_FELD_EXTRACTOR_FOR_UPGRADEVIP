# app4_streamlit.py
"""
UI for Docling + Gemini extraction (App4 version)
"""

import streamlit as st
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from app4 import extract_fields_ai_docling


st.set_page_config(page_title="Service PDF Extractor (Docling)", layout="centered")

st.markdown("""
# 📄 Service PDF Extractor — Docling + Gemini
Parses PDF using Docling (OCR + tables) then extracts fields via Gemini.
Faster & cheaper than Vision model.
""")


uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

def create_pdf_from_text(text):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    text_obj = pdf.beginText(40, 750)
    text_obj.setFont("Helvetica", 11)

    for line in text.split("\n"):
        if text_obj.getY() < 40:
            pdf.drawText(text_obj)
            pdf.showPage()
            text_obj = pdf.beginText(40, 750)
            text_obj.setFont("Helvetica", 11)
        text_obj.textLine(line)

    pdf.drawText(text_obj)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


if uploaded_files:
    for pdf_file in uploaded_files:
        st.markdown("---")
        st.write(f"**File:** {pdf_file.name}")

        with st.spinner(f"Processing {pdf_file.name} using Docling..."):
            result = extract_fields_ai_docling(pdf_file)

        st.subheader("Extracted JSON")
        st.json(result)

        # Create formatted text summary
        summary = "\n".join(f"{k}: {v}" for k, v in result.items())

        st.download_button(
            label="📥 Download as TXT",
            data=summary,
            file_name=f"{pdf_file.name}_docling.txt",
            mime="text/plain"
        )

        pdf_buffer = create_pdf_from_text(summary)
        st.download_button(
            label="📄 Download as PDF",
            data=pdf_buffer,
            file_name=f"{pdf_file.name}_docling.pdf",
            mime="application/pdf"
        )
else:
    st.info("Upload PDF to begin.")
