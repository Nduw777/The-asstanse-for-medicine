"""
Vincent's Med AI — Streamlit front‑end (Gemini version)
WARNING: Educational only; always confirm with a licensed physician.
"""
import os
import io
import time
import streamlit as st
from dotenv import load_dotenv

# Google Gemini SDK
import google.generativeai as genai

# Smart retry helper (avoids rate‑limit crashes)
from tenacity import retry, wait_random_exponential, stop_after_attempt

# 1️⃣ Load the secret key
load_dotenv()
google_key = os.getenv("GOOGLE_API_KEY")
if not google_key:
    st.error("❌ Please set a GOOGLE_API_KEY in a .env file or Streamlit secret.")
    st.stop()

# 2️⃣ Configure Gemini
try:
    genai.configure(api_key=google_key)
    model = genai.GenerativeModel("gemini-pro")  # free tier supports this model (≈5 RPM / 25 req/day)
except Exception as e:
    st.error(f"😓 Could not initialise Gemini: {e}")
    st.stop()

# 2️⃣½ Retry wrapper with 12 s minimum (Gemini free limit = 5 RPM)
@retry(wait=wait_random_exponential(min=12, max=60), stop=stop_after_attempt(4))
def safe_generate(prompt: str) -> str:
    """Generate text with automatic back‑off on rate‑limit errors."""
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.25, "max_output_tokens": 512},
    )
    return response.text.strip()

# 3️⃣ Streamlit layout
st.set_page_config(page_title="Vincent's Med AI (Gemini)", page_icon="🩺")
st.title("🩺 Vincent's Medical AI (Gemini Edition)")

st.markdown(
    """
    **Hi, Doctor!** Paste a patient’s lab result **or upload a file** below and I’ll explain it in plain language.  
    I’ll also list **possible** medicine *classes* and next steps.

    > ⚠️ **Remember:** I’m just an AI helper, *not* a real doctor.  
    Use my notes for brainstorming and always double‑check with proper clinical guidelines.
    """
)

# 4️⃣ File upload
uploaded_file = st.file_uploader(
    "📂 Upload a lab‑result file (TXT or CSV)",
    type=["txt", "csv"],
    help="Supported formats: plain‑text .txt or comma‑separated .csv files.",
)
file_text = ""
if uploaded_file is not None:
    try:
        bytes_content = uploaded_file.read()
        file_text = bytes_content.decode("utf-8")
    except Exception:
        st.warning("😕 I couldn't read that file. Please make sure it's plain text or CSV.")
        file_text = ""

# 5️⃣ Manual text area (kept for flexibility)
sample_text = """Hemoglobin A1C: 8.2% (High)\nLDL Cholesterol: 165 mg/dL (High)"""
lab_text_input = st.text_area(
    "…or paste the lab‑test text here:",
    placeholder=sample_text,
    height=150,
    value=file_text,  # pre‑fill with uploaded content if any
)

# Decide which text actually gets sent
final_text = file_text if file_text.strip() else lab_text_input

# 6️⃣ Handle button click
if st.button("🔍 Explain & Recommend"):
    if not final_text.strip():
        st.warning("Please upload a file or paste a lab result before clicking 😊")
        st.stop()

    # Build the prompt for Gemini
    system_prompt = (
        "You are a compassionate medical doctor AI assistant. "
        "Explain lab results in simple terms. "
        "You may suggest general medicine classes or lifestyle tips, "
        "but do NOT give drug names or exact doses. "
        "Always remind the reader to confirm with a licensed doctor."
    )
    full_prompt = f"{system_prompt}\n\nHere is the lab result:\n{final_text}\n\nExplain and recommend."

    with st.spinner("Thinking …"):
        try:
            answer = safe_generate(full_prompt)
            st.success("Here’s my draft explanation:")
            st.write(answer)
        except Exception as e:
            if any(word in str(e).lower() for word in ["quota", "rate", "limit"]):
                st.error("⚠️ Free Gemini quota reached or too many requests. Please wait a bit and try again.")
            else:
                st.error(f"😓 Oops, something went wrong: {e}")

# 7️⃣ Footer
st.sidebar.info("Built with Streamlit, Google Gemini & Tenacity · July 2025")
