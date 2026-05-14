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

# --- 팀 생성 로직 (수정본) ---
elif st.session_state.page == 'create':
    st.subheader("🆕 새로운 팀 만들기")
    t_name = st.text_input("팀 이름", placeholder="예: 파이썬 열공방")
    u_name = st.text_input("내 닉네임", placeholder="예: 홍길동")
    
    if st.button("확인 및 시작"):
        if not t_name or not u_name:
            st.warning("이름과 닉네임을 모두 입력해주세요!")
        else:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            row = {
                "invite_code": code,
                "team_name": t_name,
                "members": [{"name": u_name, "status": "대기"}],
                "subjects": {"기본과목": {"grade": "A+"}} # 초기 과목 설정
            }
            
            try:
                # 1. 서버 저장
                supabase.table("team").insert(row).execute()
                
                # 2. 세션 상태에 저장 (이게 중요!)
                st.session_state.invite_code = code
                st.session_state.my_name = u_name
                st.session_state.page = 'dashboard'
                
                # 3. 강제 재시작
                st.success(f"팀 생성 완료! 코드: {code}")
                st.rerun() 
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")
