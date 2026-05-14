import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string

# 1. 연결 설정 (슬래시 / 주의!!)
URL = "https://bpyxibaquftjjzvsoord.supabase.co" # 주소 끝에 아무것도 붙이지 마세요
KEY = "sb_publishable_rNyeIYS4lrfQ9eRhEgCVqw_ATzUoPCS"
GEMINI = "AIzaSyBIqXd2kYdsPfPER7BJXEreSMQaBX49Oyo"

# 서버 연결 (예외처리 추가)
try:
    supabase: Client = create_client(URL, KEY)
    genai.configure(api_key=GEMINI)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"연결 실패: {e}")

if 'page' not in st.session_state: st.session_state.page = 'gate'

# --- 게이트웨이 ---
if st.session_state.page == 'gate':
    st.title("🔥 체크메이트")
    if st.button("팀 만들기"): st.session_state.page = 'create'; st.rerun()
    if st.button("참여하기"): st.session_state.page = 'join'; st.rerun()

# --- 팀 생성 (에러 포인트 65라인 수정) ---
elif st.session_state.page == 'create':
    t_name = st.text_input("팀 이름")
    u_name = st.text_input("내 닉네임")
    if st.button("확인"):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # 데이터를 변수에 먼저 담기
        row = {
            "invite_code": code,
            "team_name": t_name,
            "members": [{"name": u_name, "status": "대기"}],
            "subjects": {}
        }
        
        # insert 방식 변경 (가장 안전한 형태)
        try:
            supabase.table("team").insert(row).execute()
            st.session_state.update({"invite_code": code, "my_name": u_name, "page": "dashboard"})
            st.rerun()
        except Exception as e:
            st.error(f"서버 저장 실패: {e}") # 여기서 진짜 이유를 화면에 띄웁니다
