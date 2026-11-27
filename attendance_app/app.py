import hashlib
import re
import cv2
import numpy as np
import requests
import streamlit as st
from PIL import Image
from io import BytesIO

st.set_page_config(page_title='학교축제 출석확인', page_icon='📷')

def api(action, **payload):
    r = requests.post(st.secrets['APPS_SCRIPT_URL'], json={
        'action': action, 'key': st.secrets['APP_SHARED_KEY'], **payload
    }, timeout=35)
    r.raise_for_status()
    return r.json()

# 관리자 비밀번호는 Streamlit Secrets에 별도로 설정합니다.
if not st.session_state.get('authenticated'):
    st.title('관리자 로그인')
    with st.form('login'):
        password = st.text_input('관리자 비밀번호', type='password')
        login = st.form_submit_button('로그인')
    if login:
        import hmac
        if hmac.compare_digest(password.encode(), str(st.secrets.get('ADMIN_PASSWORD', '')).encode()) and password:
            st.session_state.authenticated = True
            st.rerun()
        st.error('비밀번호가 올바르지 않습니다.')
    st.stop()

st.title('📷 학교축제 출석확인')
if st.button('로그아웃'):
    st.session_state.clear()
    st.rerun()

st.session_state.setdefault('scan_round', 0)
st.session_state.setdefault('scan_result', None)
st.session_state.setdefault('scan_hash', None)

def reset_scan():
    st.session_state.scan_round += 1
    st.session_state.scan_result = None
    st.session_state.scan_hash = None

scan, stats = st.tabs(['QR 자동 입장 확인', '방문자 통계'])
with scan:
    st.info('QR 촬영 또는 이미지 입력 즉시 입장 처리합니다.')
    mode = st.radio('입력 방식', ['카메라', '이미지 파일', 'USB QR 인식기'], horizontal=True, on_change=reset_scan)
    n = st.session_state.scan_round
    token = None
    raw = None
    if mode == '카메라':
        source = st.camera_input('QR코드 촬영', key=f'camera_{n}')
        if source: raw = source.getvalue()
    elif mode == '이미지 파일':
        source = st.file_uploader('QR 이미지', type=['png','jpg','jpeg'], key=f'upload_{n}')
        if source: raw = source.getvalue()
    else:
        token = st.text_input('QR 인식기 입력 (Enter로 전송)', key=f'token_{n}').strip()
    fingerprint = hashlib.sha256(raw).hexdigest() if raw else ('token:'+token if token else None)
    if fingerprint and fingerprint != st.session_state.scan_hash:
        st.session_state.scan_hash = fingerprint
        try:
            if raw:
                img = Image.open(BytesIO(raw)).convert('RGB')
                token, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
            if not re.fullmatch(r'[0-9a-fA-F]{32}', (token or '').strip()):
                st.session_state.scan_result = {'ok':False, 'message':'유효한 축제 QR코드를 인식하지 못했습니다.'}
            else:
                with st.spinner('구글시트 입장 상태 확인 중...'):
                    st.session_state.scan_result = api('checkin', token=token.strip())
        except Exception:
            st.session_state.scan_result = {'ok':False, 'message':'처리 결과를 확인할 수 없습니다. 구글시트에서 입장 상태를 확인한 후 필요하면 다시 스캔하세요.'}
    result = st.session_state.scan_result
    if result:
        if result.get('ok'):
            v = result.get('visitor', {})
            st.success(f"입장 확인 완료: {v.get('name','')}")
            st.write('학교:', v.get('school',''))
            st.write('방문 목적:', v.get('purpose',''))
            st.write('등록완료: 완료')
            st.write('입장일시:', v.get('checkin_time',''))
        else:
            st.error(result.get('message','입장 확인 실패'))
        st.button('다음 방문자 확인 / 다시 스캔', on_click=reset_scan)
with stats:
    if st.button('통계 조회 / 새로고침'):
        try:
            st.session_state.stats_result = api('stats')
        except Exception:
            st.session_state.stats_result = {'ok':False,'message':'통계 연결 실패'}
    s = st.session_state.get('stats_result')
    if s:
        if s.get('ok'):
            a,b,c = st.columns(3)
            a.metric('사전 등록자',s['total'])
            b.metric('입장 완료',s['checked_in'])
            c.metric('미입장',s['not_checked_in'])
            st.dataframe(s['by_purpose'], hide_index=True)
        else:
            st.error(s.get('message','통계 조회 실패'))
