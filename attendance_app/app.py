import streamlit as st
import requests
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="학교축제 출석확인", page_icon="📷", layout="centered")

def api(action, **payload):
    r = requests.post(
        st.secrets["APPS_SCRIPT_URL"],
        json={"action": action, "key": st.secrets["APP_SHARED_KEY"], **payload},
        timeout=25
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("message", "요청을 처리하지 못했습니다."))
    return data

def decode_qr(upload):
    image = Image.open(upload).convert("RGB")
    arr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    value, points, _ = detector.detectAndDecode(arr)
    return value.strip() if value else ""

st.title("📷 학교축제 출석확인 관리자")
st.write("방문자가 제시한 QR코드를 카메라로 촬영하거나 이미지 파일로 올려 입장을 확인합니다.")
st.warning("관리자에게만 이 앱 주소와 접속 권한을 공유하세요.")

tab_scan, tab_stats = st.tabs(["QR 출석 확인", "방문자 통계"])

with tab_scan:
    st.subheader("QR코드 촬영")
    shot = st.camera_input("방문자의 QR코드를 화면 안에 맞춘 후 촬영하세요.")
    uploaded = st.file_uploader("또는 QR코드 이미지 업로드", type=["png", "jpg", "jpeg"])
    source = shot if shot is not None else uploaded

    if source is not None:
        token = decode_qr(source)
        if not token:
            st.error("QR코드를 인식하지 못했습니다. 밝은 곳에서 다시 촬영해 주세요.")
        else:
            st.success("QR코드 인식 완료")
            if st.button("입장 확인 및 등록완료 처리", type="primary"):
                try:
                    result = api("checkin", token=token)
                    st.success(f"입장 확인 완료: {result['visitor']['name']}님")
                    st.write(f"학교: {result['visitor']['school']}")
                    st.write(f"방문 목적: {result['visitor']['purpose']}")
                    st.write(f"입장 시각: {result['visitor']['checkin_time']}")
                except Exception as e:
                    st.error(str(e))
    st.caption("이미 등록완료된 QR코드를 다시 인식하면 중복 입장을 차단합니다.")

with tab_stats:
    st.subheader("실시간 방문 현황")
    if st.button("통계 새로고침"):
        st.session_state["refresh_stats"] = True
    try:
        stats = api("stats")
        a, b, c = st.columns(3)
        a.metric("사전 등록자", stats["total"])
        b.metric("입장 완료", stats["checked_in"])
        c.metric("미입장", stats["not_checked_in"])
        st.write("**방문 목적별 사전 등록 현황**")
        st.dataframe(stats["by_purpose"], use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"통계를 불러오지 못했습니다: {e}")
