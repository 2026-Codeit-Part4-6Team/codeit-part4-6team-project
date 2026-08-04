import os

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(page_title="광고 콘텐츠 생성", page_icon=None)
st.title("광고 콘텐츠 생성")

prompt = st.text_area("광고할 제품이나 서비스를 입력하세요.")

if st.button("생성", type="primary", disabled=not prompt.strip()):
    try:
        response = httpx.post(
            f"{BACKEND_URL}/generate",
            json={"prompt": prompt},
            timeout=30.0,
        )
        response.raise_for_status()
        st.success(response.json()["result"])
    except httpx.HTTPError:
        st.error("생성 서버에 연결할 수 없습니다.")
