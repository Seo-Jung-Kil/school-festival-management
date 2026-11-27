import streamlit as st
import requests, qrcode, io, uuid
from datetime import datetime

st.set_page_config(page_title="학교축제 방문자 사전등록", page_icon="🎪", layout="centered")

def api(action, **payload):
    url = st.secrets["APPS_SCRIPT_URL"]
    key = st.secrets["APP_SHARED_KEY"]
    r = requests.post(url, json={"action": action, "key": key, **payload}, timeout=25)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("message", "요청을 처리하지 못했습니다."))
    return data

st.title("🎪 학교축제 방문자 사전등록")
st.write("축제 방문 전 정보를 등록해 주세요. 등록이 완료되면 입장용 QR코드가 발급됩니다.")
st.info("QR코드는 축제 당일 입장 확인에 사용됩니다. 다른 사람에게 전달하지 마세요.")

with st.form("visitor_form"):
    school = st.text_input("학교", placeholder="예: 대성고등학교")
    student_id = st.text_input("학번 (해당하는 경우)", placeholder="외부 방문자는 비워 두셔도 됩니다.")
    name = st.text_input("이름")
    phone = st.text_input("연락처", placeholder="예: 010-1234-5678")
    purpose = st.selectbox("방문 목적", [
        "축제 관람", "학생·교직원 가족", "학교 관계자", "초청 및 업무", "공연", "기타"
    ])
    agree = st.checkbox("방문자 정보 수집 및 축제 입장 확인 목적의 이용에 동의합니다.")
    submitted = st.form_submit_button("방문자 등록하기", type="primary", use_container_width=True)

if submitted:
    if not school.strip() or not name.strip() or not phone.strip():
        st.error("학교, 이름, 연락처는 필수 입력 항목입니다.")
    elif not agree:
        st.error("개인정보 수집·이용 동의가 필요합니다.")
    else:
        token = uuid.uuid4().hex
        try:
            result = api("register", visitor={
                "school": school.strip(),
                "student_id": student_id.strip(),
                "name": name.strip(),
                "phone": phone.strip(),
                "purpose": purpose,
                "token": token
            })
            st.session_state["registered"] = {
                "token": token, "name": name.strip(), "school": school.strip(),
                "purpose": purpose
            }
            st.success("사전 등록이 완료되었습니다.")
        except Exception as e:
            st.error(f"등록에 실패했습니다: {e}")

if "registered" in st.session_state:
    v = st.session_state["registered"]
    st.divider()
    st.subheader("입장용 QR코드")
    st.write(f"**이름:** {v['name']}  \n**학교:** {v['school']}  \n**방문 목적:** {v['purpose']}")
    img = qrcode.make(v["token"])
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue(), caption="축제 당일 입장 확인 시 제시해 주세요.", width=280)
    st.download_button("QR코드 저장하기", buf.getvalue(), file_name="학교축제_입장_QR.png", mime="image/png")
    st.caption("QR에는 개인정보 대신 임의 발급된 식별 토큰만 저장됩니다.")
