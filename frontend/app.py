import os

import httpx
import streamlit as st

from frontend.api_client import ApiClient

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
api_client = ApiClient(BACKEND_URL)

st.set_page_config(page_title="광고 콘텐츠 생성", page_icon=None)
st.title("광고 콘텐츠 생성")

prompt = st.text_area("광고할 제품이나 서비스를 입력하세요.")

if st.button("생성", type="primary", disabled=not prompt.strip()):
    try:
        response = api_client.generate(prompt)
        st.success(response["result"]["text"])
    except httpx.HTTPError:
        st.error("생성 서버에 연결할 수 없습니다.")
