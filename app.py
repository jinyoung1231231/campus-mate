import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
import time
import gc
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# 1. 노션 스타일 및 수직선 점(Dot) 타임라인 전용 CSS 주입
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
        color: #37352f;
    }
    .notion-header {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 4px;
        color: #37352f;
    }
    .notion-sub {
        font-size: 14px;
        color: #7c7b77;
        margin-bottom: 24px;
    }
    
    /* 과목 카드 상하 세로 정렬 디자인 */
    .subject-block {
        background-color: #fbfbfa;
        border: 1px solid #ededeb;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .subject-title {
        font-size: 18px;
        font-weight: 700;
        color: #37352f;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .schedule-box {
        background-color: #f7f7f5;
        border-radius: 6px;
        padding: 12px 16px;
        margin-top: 12px;
        margin-bottom: 16px;
        border-left: 3px solid #60a5fa;
        display: flex;
        gap: 24px;
    }
    .schedule-item {
        font-size: 13px;
        color: #4b5563;
    }
    
    /* 수직선 포인트 타임라인 보드 그래픽 구조 */
    .vertical-timeline {
        position: relative;
        border-left: 2px solid #e3e2e0;
        margin-left: 12px;
        padding-left: 24px;
        margin-top: 16px;
        margin-bottom: 16px;
    }
    .timeline-node {
        position: relative;
        margin-bottom: 18px;
    }
    .timeline-node:last-child {
        margin-bottom: 0;
    }
    
    /* 수직선 위의 점(Dot) 디자인 */
    .timeline-dot {
        position: absolute;
        left: -31px;
        top: 3px;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background-color: #fff;
        border: 3px solid #cbd5e1;
        z-index: 2;
    }
    .dot-active {
        border-color: #238387;
        background-color: #238387;
        box-shadow: 0 0 0 4px #e2f3f5;
    }
    .dot-done {
        border-color: #2e7d32;
        background-color: #2e7d32;
    }
    
    /* 일차별 텍스트 및 배지 조화 */
    .node-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
    }
    .node-badge {
        font-size: 11px;
        font-weight: 700;
        padding: 1px 6px;
        border-radius: 3px;
    }
    .nb-waiting { background-color: #f1f1ef; color: #7c7b77; }
    .nb-active { background-color: #e2f3f5; color: #238387; }
    .nb-done { background-color: #eaf5ea; color: #2e7d32; }
    
    .node-text {
        font-size: 13.5px;
        color: #37352f;
        line-height: 1.5;
    }

    .focus-panel {
        background-color: #f7f7f5;
        border-radius: 12px;
        padding: 32px;
        text-align: center;
        border: 1px solid #e3e2e0;
        margin-bottom: 24px;
    }
    .focus-timer {
        font-size: 48px;
        font-weight: 700;
        font-family: monospace;
        color: #238387;
        margin: 12px 0;
    }
    .focus-badge {
        background-color: #e2f3f5;
        color: #238387;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    }
    .test-panel {
        background-color: #fff5f5;
        border: 1px solid #ffe3e3;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
    }
    .test-timer {
        font-size: 36px;
        font-weight: 700;
        font-family: monospace;
        color: #e03131;
    }
    .omr-container {
        background-color: #fcfcfb;
        border-left: 3px solid #37352f;
        padding: 20px;
        border-radius: 0 8px 8px 0;
    }
    .consult-container {
        background-color: #fbfbfa;
        border: 1px solid #e3e2e0;
        border-radius: 8px;
        padding: 20px;
        margin-top: 20px;
        margin-bottom: 16px;
    }
    .consult-user-q {
        font-size: 14px;
        font-weight: 600;
        color: #4b5563;
        background-color: #f3f4f6;
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 14px;
    }
    .consult-ai-a {
        font-size: 14px;
        color: #1f2937;
        line-height: 1.6;
        padding-left: 4px;
    }
    .report-card {
        background: linear-gradient(135deg, #f8fafc, #f1f5f9);
        border: 2px dashed #cbd5e1;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 2. 데이터베이스 초기화
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# 3. 세션 상태 관리
session_keys = {
    'page': 'gate',
    'my_name': '',
    'invite_code': '',
    'current_mode': 'dashboard', 
    'active_subject': '',        
    'active_day': 1,             
    'timer_running': False,
    'start_time': None,
    'elapsed_time': 0,
    'test_start_time': None,
    'test_limit_seconds': 600,   
    'user_answers': {},          
    'current_ai_plan': '', 
    'current_ai_quiz': '',
    'current_ai_quiz_answers': '', 
    'current_ai_consult_q': '', 
    'current_ai_consult_a': '', 
    'input_manual_text': '',
    'input_days': 7,
    'input_grade': 'A+',
    'refresh_lock': False,
    'saved_study_content': '',
    'focus_chat_history': [],
    'focus_detailed_checklist': []  
}

for key, default in session_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default

# 4. 파일 본문 텍스트 파싱 유틸리티
@st.cache_data(max_entries=5, ttl=300)
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([p.extract_text() for p in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except:
        return ""

# 5. 제미나이 AI 백엔드 (자동 탐색 로직 적용)
def run_ai_engine(prompt_type, **kwargs):
    st.session_state["refresh_lock"] = True
    with st.spinner("AI가 핵심 데이터를 분석하고 있습니다... 📝"):
        try:
            today_str = datetime.now().strftime("%Y년 %m월 %d일")
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            
            # API 키가 접근 가능한 모델을 서버에서 직접 조회하여 404 에러를 원천 차단하는 로직
            def get_ai_response(prompt_text):
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                if not available_models:
                    raise Exception("현재 API 키로 사용할 수 있는 생성형 AI 모델이 구글 서버에 없습니다. API 키 설정이나 권한을 확인해주세요.")
                
                # 우선순위: 1.5 Flash -> 1.5 Pro -> 일반 Pro -> 사용 가능한 첫 번째 모델
                target_model_name = None
                for pref in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
                    if pref in available_models:
                        target_model_name = pref
                        break
                        
                if not target_model_name:
                    target_model_name = available_models[0] # 우선순위 모델이 없으면 허용된 아무 모델이나 사용
                    
                # 'models/' 접두사를 제거하고 모델 인스턴스 생성
                clean_model_name = target_model_name.replace('models/', '')
                model = genai.GenerativeModel(clean_model_name)
                return model.generate_content(prompt_text)

            if prompt_type == "plan":
                p = f"""오늘 날짜는 {today_str}입니다. 타겟 과목명: [{kwargs['sub_name']}], 목표 성적: {kwargs['grade']}, 남은 기간: {kwargs['days']}일.
제공된 학습 자료를 바탕으로, 사용자가 매일 공부할 수 있도록 각 일차별 학습 미션을 구분하여 계획표를 짜주세요.

작성 수칙 - 매우 중요
반드시 하루의 스케줄은 한 줄로 끝나야 하며, 문장의 시작을 '과목명 Day X:' 형태로만 가공해야 합니다. 추가 문장이나 줄바꿈을 넣지 마세요.
양식 준수 예시 (과목명이 '로봇공학'인 경우):
로봇공학 Day 1: 로봇 센서 개론 기초 용어 정리 및 핵심 개념 요약하기

학습 자료
{kwargs['content'][:4000]}"""
                res = get_ai_response(p)
                st.session_state["current_ai_plan"] = st.session_state.get("current_ai_plan", "") + "\n" + res.text
                st.session_state["current_ai_quiz"] = "" 

            elif prompt_type == "checklist":
                p = f"""오늘의 핵심 미션: {kwargs['mission']}
위 미션을 완수하기 위해 학생이 차근차근 따라할 수 있는 상세 행동 체크리스트를 3~5개로 쪼개서 만들어주세요.

작성 수칙 - 매우 중요 (규칙 위반 시 시스템 오류 발생)
1. 반드시 기호나 번호(-, *, 1. 등) 없이 체크리스트 내용만 한 줄에 하나씩 적어주세요.
2. 제공된 [학습 자료] 안의 핵심 키워드를 포함해서 구체적인 행동으로 지시해주세요.

학습 자료
{kwargs['content'][:4000]}"""
                res = get_ai_response(p)
                
                raw_list = res.text.split('\n')
                cleaned_list = []
                for l in raw_list:
                    clean_l = l.strip(" -=*1234567890.")
                    if clean_l:
                        cleaned_list.append(clean_l)
                
                st.session_state["focus_detailed_checklist"] = cleaned_list

            elif prompt_type == "quiz_questions":
                p = f"""당신은 대학교 교수이자 시험 출제위원입니다. 
아래 [학습 자료]만을 읽고, 주관식/서술형 퀴즈 3개와 그에 대한 정답을 함께 출제하세요.

작성 수칙 - 매우 중요
1. 문제 1, 2는 단답형, 문제 3은 서술형입니다.
2. 반드시 아래 [출제 양식]을 그대로 따르고, 문제와 정답 사이에 '정답선' 이라는 단어를 무조건 넣어야 합니다.
3. 마크다운 효과를 전혀 쓰지 말고 순수 텍스트로만 작성하세요.

[출제 양식]
문제 1. (문제 내용)

문제 2. (문제 내용)

문제 3. (문제 내용)

정답선
[정답 및 해설]
1번 정답: 
2번 정답: 
3번 정답/해설: 

학습 자료
{kwargs['content'][:4000]}"""
                res = get_ai_response(p)
                
                if "정답선" in res.text:
                    parts = res.text.split("정답선", 1)
                    st.session_state["current_ai_quiz"] = parts[0].strip("= -\n")
                    st.session_state["current_ai_quiz_answers"] = parts[1].strip("= -\n")
                else:
                    st.session_state["current_ai_quiz"] = res.text.strip()
                    st.session_state["current_ai_quiz_answers"] = "AI가 해설을 분리하지 못했습니다. 채점 시 전체 문항을 참고해주세요."

            elif prompt_type == "consult":
                p = f"학업 및 진로 고민 상담 내용입니다: {kwargs['q']}\n학생의 상황에 진심으로 공감하며 향후 진로 설계와 동기부여에 도움이 될 수 있는 구체적인 가이드와 솔루션을 제공해주세요."
                res = get_ai_response(p)
                st.session_state["current_ai_consult_q"] = kwargs['q']
                st.session_state["current_ai_consult_a"] = res.text
                
            elif prompt_type == "focus_chat":
                p = f"""당신은 현재 학습 중인 과목의 1:1 전담 친절한 AI 튜터입니다. 
아래 [학습 자료]를 최우선으로 참고하여 학생의 질문에 답변해주세요. 

학습 자료
{kwargs['content'][:8000]}

학생의 질문
{kwargs['q']}"""
                res = get_ai_response(p)
                history = st.session_state.get("focus_chat_history", [])
                history.append({"role": "user", "content": kwargs['q']})
                history.append({"role": "assistant", "content": res.text})
                st.session_state["focus_chat_history"] = history
            
            gc.collect()
            st.session_state["refresh_lock"] = False
            st.rerun()
                
        except Exception as e:
            st.session_state["refresh_lock"] = False
            st.error(f"AI 통신 중 오류 발생: {e}")

# 6. 사용자 인증 및 팀 게이트웨이 렌더링
if st.session_state.get('page') == 'gate':
    st.title("Check-Mate")
    
    un = st.text_input("사용자 닉네임 입력 (로그인)")
    
    if un:
        try:
            all_teams = supabase.table("team").select("*").execute().data
            my_teams
