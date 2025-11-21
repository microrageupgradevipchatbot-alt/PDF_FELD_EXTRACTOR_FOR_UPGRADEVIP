# app3_streamlit.py
"""
Streamlit UI for app3: multi-file upload, send each PDF to app3.extract_fields_ai,
display JSON results, allow copy/download.
"""

import streamlit as st
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from app3 import extract_fields_ai

st.set_page_config(page_title="Service PDF Extractor (Vision)", layout="centered")

st.markdown("""
# 📄 Service PDF Extractor — Gemini Vision
Upload one or more **service PDFs** . The Vision model will read the PDF (including images/tables)
and return a strict JSON with the service schema.
""")

# small old-style UI wrapper (like your screenshot)
st.write("Upload PDF(s) — the model will extract these keys: service_type, services, title, airport, pricing (1-10 pax), ...")

uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

# helper to create a simple downloadable PDF from text
def create_pdf_from_text(text):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    text_obj = pdf.beginText(40, 750)
    text_obj.setFont("Helvetica", 11)
    for line in text.split("\n"):
        # guard: if text runs off page we simply keep adding pages (simple approach)
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

# JS copy button helper
def copy_button(text, key):
    # Escape backticks and backslashes in text for safe inline JS
    safe_text = text.replace("\\", "\\\\").replace("`", "\\`")
    copy_js = f"""
    <script>
    function copyToClipboard{key}() {{
        navigator.clipboard.writeText(`{safe_text}`).then(function() {{
            const e = document.createElement('div');
            e.innerText = "Copied!";
            e.style.position = 'fixed';
            e.style.right = '20px';
            e.style.top = '20px';
            e.style.background = '#0b7285';
            e.style.color = 'white';
            e.style.padding = '8px 12px';
            e.style.borderRadius = '6px';
            document.body.appendChild(e);
            setTimeout(()=>document.body.removeChild(e), 1200);
        }});
    }}
    </script>
    
    """
    st.markdown(copy_js, unsafe_allow_html=True)

if uploaded_files:
    for idx, uploaded in enumerate(uploaded_files):
        st.markdown("---")
        st.write(f"**File:** {uploaded.name}")

        with st.spinner(f"Processing {uploaded.name} with Gemini Vision..."):
            # Important: pass the stream (uploaded) to backend. The backend will read it.
            try:
                result = extract_fields_ai(uploaded)
            except Exception as e:
                st.error(f"Processing error: {e}")
                continue

        # If backend returned an error wrapper
        if isinstance(result, dict) and result.get("error"):
            st.error("Extraction error — see raw output below.")
            st.write(result.get("detail") or result.get("raw"))
            continue

        # Show JSON result prettily
        st.subheader("Extracted JSON")
        st.json(result)

        # Prepare a human-friendly text summary for download/copy
        def _format_summary(d):
            lines = []
            # iterate keys in a predictable order
            preferred_keys = [
                "service_type", "services", "title", "airport", "max_passengers_allowed",
                "travel_type", "status", "meeting_point", "fast_track",
                "transportation_inside_airport", "assistance_with_pieces_of_luggage",
                "lounge_access", "farewell", "special_announcement",
                "duration_minutes", "fee_ooh", "late_booking_fee", "usp", "refund_policy_hours"
            ]
            for k in preferred_keys:
                v = d.get(k, None)
                lines.append(f"{k}: {v}")
            # pricing block
            pricing = d.get("pricing", {})
            lines.append("pricing:")
            if isinstance(pricing, dict):
                for pax_key in sorted(pricing.keys(), key=lambda s: int(s.split("_")[0])):
                    pax = pricing.get(pax_key)
                    lines.append(f"  {pax_key}: {pax}")
            # service details
            sd = d.get("service_details", [])
            lines.append("service_details:")
            if isinstance(sd, list):
                for bullet in sd:
                    lines.append(f"  - {bullet}")
            return "\n".join(lines)

        summary = _format_summary(result if isinstance(result, dict) else {})

        with st.expander("Preview / Copy / Download", expanded=False):
            st.code(summary, language="text")

            # copy
            copy_button(summary, key=f"{idx}")

            # download txt
            st.download_button(
                label="📥 Download as TXT",
                data=summary,
                file_name=f"{uploaded.name}_extracted.txt",
                mime="text/plain"
            )

            # download PDF
            pdf_buffer = create_pdf_from_text(summary)
            st.download_button(
                label="📄 Download as PDF",
                data=pdf_buffer,
                file_name=f"{uploaded.name}_extracted.pdf",
                mime="application/pdf"
            )

else:
    st.info("Please upload one or more PDF files to extract.")
