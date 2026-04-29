import io
import httpx
import streamlit as st

API_BASE_URL = "http://localhost:8000"

st.title("GDPR Compliance Checker")

input_mode = st.radio("Input", ["Text", "PDF"], horizontal=True)

if input_mode == "Text":
    text = st.text_area("Document text", height=400)
    if st.button("Analyse"):
        r = httpx.post(f"{API_BASE_URL}/api/v1/analyse/text", json={"text": text}, timeout=120)
        st.json(r.json())
else:
    file = st.file_uploader("Upload PDF", type=["pdf"])
    if st.button("Analyse") and file:
        r = httpx.post(
            f"{API_BASE_URL}/api/v1/analyse/pdf",
            files={"file": (file.name, io.BytesIO(file.read()), "application/pdf")},
            timeout=120,
        )
        st.json(r.json())