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
    .subject-block:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
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

# 사용 가능한 모델명 자동 탐색 및 캐싱
@st.cache_data(ttl=3600)
def get_valid_model_name(api_key):
    genai.configure(api_key=api_key)
    try:
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for keyword in ['1.5-flash', 'flash', 'gemini-pro']:
            for model_name in valid_models:
                if keyword in model_name:
                    return model_name
        return valid_models[0] if valid_models else 'gemini-pro'
    except:
        return 'gemini-pro'

# 5. 제미나이 AI 백엔드 오케스트레이션 함수
def run_ai_engine(prompt_type, **kwargs):
    st.session_state.refresh_lock = True
    should_rerun = False
    
    with st.spinner("AI가 핵심 데이터를 분석하고 있습니다... 📝"):
        try:
            today_str = datetime.now().strftime("%Y년 %m월 %d일")
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
            
            exact_model_name = get_valid_model_name(api_key)
            model_instance = genai.GenerativeModel(exact_model_name)

            if prompt_type == "plan":
                p = f"""오늘 날짜는 {today_str}입니다. 타겟 과목명: [{kwargs['sub_name']}], 목표 성적: {kwargs['grade']}, 남은 기간: {kwargs['days']}일.
제공된 학습 자료를 바탕으로, 사용자가 매일 공부할 수 있도록 각 일차별 학습 미션을 구분하여 계획표를 짜주세요.

작성 수칙 - 매우 중요
반드시 하루의 스케줄은 한 줄로 끝나야 하며, 문장의 시작을 '과목명 Day X:' 형태로만 가공해야 합니다. 추가 문장이나 줄바꿈을 넣지 마세요.
양식 준수 예시 (과목명이 '로봇공학'인 경우):
로봇공학 Day 1: 로봇 센서 개론 기초 용어 정리 및 핵심 개념 요약하기

학습 자료
{kwargs['content'][:4000]}"""
                res = model_instance.generate_content(p)
                st.session_state.current_ai_plan = st.session_state.current_ai_plan + "\n" + res.text
                st.session_state.current_ai_quiz = "" 

            elif prompt_type == "checklist":
                p = f"""오늘의 핵심 미션: {kwargs['mission']}
위 미션을 완수하기 위해 학생이 차근차근 따라할 수 있는 상세 행동 체크리스트를 3~5개로 쪼개서 만들어주세요.

작성 수칙 - 매우 중요 (규칙 위반 시 시스템 오류 발생)
1. 반드시 기호나 번호(-, *, 1. 등) 없이 체크리스트 내용만 한 줄에 하나씩 적어주세요.
2. 제공된 [학습 자료] 안의 핵심 키워드를 포함해서 구체적인 행동으로 지시해주세요.

학습 자료
{kwargs['content'][:4000]}"""
                res = model_instance.generate_content(p)
                st.session_state.focus_detailed_checklist = [l.strip() for l in res.text.split('\n') if l.strip()]

            elif prompt_type == "quiz_questions":
                config = {
                    "temperature": 0.0,
                    "top_k": 1,
                    "top_p": 0.1
                }
                
                p = f"""[최고 수준의 엄격한 보안 지시사항]
당신은 제공된 [학습 자료] 외부의 지식은 전혀 알지 못하는 완벽한 백지 상태의 시스템입니다.

이번 시험의 출제 범위는 학생이 오늘 수행한 아래의 [오늘의 미션]과 [학습 체크리스트]입니다.
반드시 [학습 자료] 안에서 아래의 미션 및 체크리스트와 관련된 텍스트와 사실만을 100% 그대로 발췌하여 주관식/서술형 퀴즈 3개와 정답을 출제하세요.

[오늘의 미션]
{kwargs.get('mission', '지정되지 않음')}

[학습 체크리스트]
{kwargs.get('checklist', '지정되지 않음')}

작성 수칙 - 매우 중요
1. [학습 자료]에 등장하지 않는 외부 지식, 고유명사, 개념, 일반 상식은 단 1글자도 개입시키지 마세요.
2. 정답 역시 [학습 자료] 안에서 그대로 복사하여 붙여넣을 수 있는 수준으로만 출제하세요.
3. 만약 제공된 [학습 자료]에 체크리스트와 관련된 내용이 부족하다면, 절대 상상해서 만들지 말고 "학습 자료 내용이 부족하여 문제를 출제할 수 없습니다."라고만 출력하세요.
4. 문제 1, 2는 단답형, 문제 3은 서술형입니다.
5. 반드시 아래 [출제 양식]을 그대로 따르고, 문제와 정답 사이에 '===정답선===' 이라는 구분선을 무조건 넣어야 합니다.
6. 마크다운 효과를 전혀 쓰지 말고 순수 텍스트로만 작성하세요.

[출제 양식]
문제 1. (체크리스트에 기반한 단답형 문제)

문제 2. (체크리스트에 기반한 단답형 문제)

문제 3. (체크리스트에 기반한 서술형 문제)

===정답선===
[정답 및 해설]
1번 정답: 
2번 정답: 
3번 정답/해설: 

[학습 자료]
{kwargs['content'][:4000]}"""
                
                res = model_instance.generate_content(p, generation_config=config)
                
                if "===정답선===" in res.text:
                    quiz_part, ans_part = res.text.split("===정답선===", 1)
                    st.session_state.current_ai_quiz = quiz_part.strip()
                    st.session_state.current_ai_quiz_answers = ans_part.strip()
                else:
                    st.session_state.current_ai_quiz = res.text.strip()
                    st.session_state.current_ai_quiz_answers = "AI가 해설을 분리하지 못했거나 자료가 부족합니다."

            elif prompt_type == "consult":
                p = f"학업 및 진로 고민 상담 내용입니다: {kwargs['q']}\n학생의 상황에 진심으로 공감하며 향후 진로 설계와 동기부여에 도움이 될 수 있는 구체적인 가이드와 솔루션을 제공해주세요."
                res = model_instance.generate_content(p)
                st.session_state.current_ai_consult_q = kwargs['q']
                st.session_state.current_ai_consult_a = res.text
                
            elif prompt_type == "focus_chat":
                p = f"""당신은 현재 학습 중인 과목의 1:1 전담 친절한 AI 튜터입니다. 
아래 [학습 자료]를 최우선으로 참고하여 학생의 질문에 답변해주세요. 

학습 자료
{kwargs['content'][:8000]}

학생의 질문
{kwargs['q']}"""
                res = model_instance.generate_content(p)
                st.session_state.focus_chat_history.append({"role": "user", "content": kwargs['q']})
                st.session_state.focus_chat_history.append({"role": "assistant", "content": res.text})
            
            gc.collect()
            st.session_state.refresh_lock = False
            should_rerun = True
            
        except Exception as e:
            st.session_state.refresh_lock = False
            st.error(f"AI 통신 중 오류 발생: {e}")

    if should_rerun:
        st.rerun()

# 6. 사용자 인증 및 팀 게이트웨이 렌더링
if st.session_state.page == 'gate':
    st.title("Check-Mate")
    un = st.text_input("사용자 닉네임 입력 (로그인)")
    
    if un:
        my_teams = []
        db_error = False
        try:
            all_teams = supabase.table("team").select("*").execute().data
            my_teams = [t for t in all_teams if any(m['name'] == un for m in t['members'])]
        except:
            db_error = True
            
        if db_error:
            st.warning("데이터베이스 연결 상태를 점검 중입니다...")
            
        if my_teams:
            st.write(" 내 스터디 팀 목록")
            for t in my_teams:
                if st.button(f"🏠 {t['team_name']} 입장하기", key=f"t_{t['invite_code']}"):
                    st.session_state.update({"invite_code": t['invite_code'], "my_name": un, "page": "dashboard"})
                    st.rerun()
        elif not db_error:
            st.info("가입된 스터디 팀이 없습니다. 아래에서 팀을 생성하거나 초대 코드를 입력해 동시 접속하세요.")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(" 워크스페이스 팀 신규 생성")
            tn = st.text_input("새로운 스터디 팀 이름")
            if st.button("신규 워크스페이스 생성"):
                if tn and un:
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    try:
                        supabase.table("team").insert({
                            "invite_code": code, "team_name": tn,
                            "members": [{"name": un, "status": "대기", "grade": "-", "days": "-", "total_time": 0}],
                            "subjects": {un: []}, "posts": []
                        }).execute()
                        st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"})
                        st.rerun()
                    except:
                        st.error("데이터 저장에 실패했습니다.")
        with c2:
            st.subheader(" 기존 팀 워크스페이스 참여")
            ci = st.text_input("발급받은 초대 코드 입력")
            if st.button("공유 워크스페이스 입장"):
                try:
                    res = supabase.table("team").select("*").eq("invite_code", ci).execute()
                    if res.data:
                        d = res.data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}
                        if not any(m['name'] == un for m in ml):
                            ml.append({"name": un, "status": "대기", "grade": "-", "days": "-", "total_time": 0})
                            sl[un] = []
                            supabase.table("team").update({"members": ml, "subjects": sl}).eq("invite_code", ci).execute()
                        st.session_state.update({"invite_code": ci, "my_name": un, "page": "dashboard"})
                        st.rerun()
                except:
                    st.error("초대 코드를 인증할 수 없습니다.")

# 7. 핵심 메인 워크스페이스 렌더링 
elif st.session_state.page == 'dashboard':
    if not st.session_state.invite_code: 
        st.session_state.page = 'gate'; st.rerun()

    if not st.session_state.refresh_lock:
        st_autorefresh(interval=2000, limit=999999, key="global_refresh_engine")
    
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    data = res.data[0] if res.data else None
    
    if data:
        if isinstance(data.get('subjects'), list):
            recovered_subjects = {st.session_state.my_name: data['subjects']}
            supabase.table("team").update({"subjects": recovered_subjects}).eq("invite_code", st.session_state.invite_code).execute()
            data['subjects'] = recovered_subjects

        st.sidebar.markdown(f"<div class='notion-header' style='font-size:20px;'>📂 {data['team_name']}</div>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<div class='notion-sub'>사용자: {st.session_state.my_name} 님</div>", unsafe_allow_html=True)
        
        if st.session_state.current_mode in ['dashboard', 'result']:
            menu = st.sidebar.radio("내비게이션", [" 내 학습 보드 (메인)", "👥 팀원 실시간 페이스", " 공유 게시판", " AI 진로 및 학업 상담"])
        else:
            st.sidebar.warning("⚠️ 현재 공부/시험이 진행 중입니다. 메뉴 이동이 제한됩니다.")
            menu = " 내 학습 보드 (메인)"
            
        if st.sidebar.button("🚪 워크스페이스 로그아웃"):
            st.session_state.update({"invite_code": "", "page": "gate", "current_mode": "dashboard", "current_ai_plan": "", "current_ai_quiz": "", "current_ai_quiz_answers": "", "current_ai_consult_q": "", "current_ai_consult_a": "", "timer_running": False})
            st.rerun()
            
        with st.sidebar.expander("🎫 워크스페이스 초대코드"):
            st.code(data['invite_code'])

        # =========================================================================
        # MODE 1: 대시보드 모드
        # =========================================================================
        if st.session_state.current_mode == 'dashboard':
            
            if menu == " 내 학습 보드 (메인)":
                st.markdown("<div class='notion-header'>📊 전 과목 진행도 대시보드</div>", unsafe_allow_html=True)
                st.markdown("<div class='notion-sub'>각 과목 카드를 클릭하여 펼치면, 수직선 마일스톤 점과 동기화된 일차별 AI 계획을 바로 확인할 수 있습니다.</div>", unsafe_allow_html=True)
                
                my_subs = data['subjects'].get(st.session_state.my_name, [])
                
                if my_subs:
                    raw_lines = st.session_state.current_ai_plan.split('\n') if st.session_state.current_ai_plan else []
                    parsed_all_missions = {}
                    for row_line in raw_lines:
                        if "Day" in row_line and ":" in row_line:
                            try:
                                for s_item in my_subs:
                                    if s_item['name'] in row_line:
                                        day_part, mission_part = row_line.split(":", 1)
                                        day_num = int(''.join(filter(str.isdigit, day_part)))
                                        if s_item['name'] not in parsed_all_missions:
                                            parsed_all_missions[s_item['name']] = {}
                                        parsed_all_missions[s_item['name']][day_num] = mission_part.strip()
                            except:
                                pass

                    st.markdown("### 📂 현재 학습 진행 상황")
                    
                    for idx, sub in enumerate(my_subs):
                        sub_name = sub['name']
                        total_days = sub.get('total_days', 7)
                        current_day = sub.get('current_day', 1)
                        
                        progress_ratio = min(current_day / total_days, 1.0)
                        progress_percent = int(progress_ratio * 100)
                        
                        task_week = sub.get('task_week', '3주차')
                        exam_week = sub.get('exam_week', '8주차 중간고사')
                        
                        with st.container():
                            st.markdown(f"""
                            <div class='subject-block'>
                                <div class='subject-title'>📚 {sub_name} <span style='font-size:13px; color:#238387; font-weight:normal;'>— 이수율 {progress_percent}% (Day {current_day}/{total_days}일차)</span></div>
                                <div class='schedule-box'>
                                    <div class='schedule-item'>📅 과제 제출 기한: {task_week}</div>
                                    <div class='schedule-item'>📝 정기 시험 주차: {exam_week}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.progress(progress_ratio)
                            
                            sub_missions = parsed_all_missions.get(sub_name, {})
                            with st.expander(f"🔍 {sub_name} 전체 일차별 수직선 로드맵 펼치기", expanded=True):
                                st.markdown("<div class='vertical-timeline'>", unsafe_allow_html=True)
                                
                                for d_i in range(1, total_days + 1):
                                    mission_desc = sub_missions.get(d_i, f"{sub_name} 해당 차시 교안 핵심 텍스트 분석 및 모의평가 수행")
                                    
                                    if d_i < current_day:
                                        dot_class = "dot-done"
                                        badge_class = "nb-done"
                                        status_label = "✅ 완수"
                                    elif d_i == current_day:
                                        dot_class = "dot-active"
                                        badge_class = "nb-active"
                                        status_label = "🔥 진행 중"
                                    else:
                                        dot_class = ""
                                        badge_class = "nb-waiting"
                                        status_label = "🔒 대기"
                                        
                                    st.markdown(f"""
                                    <div class='timeline-node'>
                                        <div class='timeline-dot {dot_class}'></div>
                                        <div class='node-header'>
                                            <span class='node-badge {badge_class}'>Day {d_i}</span>
                                            <span style='font-size:12px; font-weight:600; color:#7c7b77;'>{status_label}</span>
                                        </div>
                                        <div class='node-text'>{mission_desc}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                st.markdown("</div>", unsafe_allow_html=True)
                            st.markdown("<div style='margin-bottom:30px;'></div>", unsafe_allow_html=True)
                else:
                    st.info("현재 등록된 학습 과목이 없습니다. 아래 컴포넌트에서 과목을 추가하고 AI 맞춤 플랜을 생성해 보세요!")

                st.divider()

                c_left, c_right = st.columns([1, 1])

                with c_left:
                    st.markdown("### ➕ 신규 과목 및 주요 학사 일정 등록")
                    ns = st.text_input("새로 추가할 과목명", placeholder="예: TOEIC 영어, 로봇공학개론")
                    ntask = st.text_input("과제 제출일 설정", placeholder="예: 3주차 금요일, 매주 일요일")
                    nexam = st.text_input("시험 일정/주차 설정", placeholder="예: 8주차 중간고사, Day 7 테스트")
                    
                    if st.button("과목 보드에 등록", use_container_width=True):
                        if ns:
                            my_subs.append({
                                "name": ns, 
                                "total_days": 7, 
                                "current_day": 1,
                                "task_week": ntask if ntask else "3주차",
                                "exam_week": nexam if nexam else "8주차 중간고사"
                            })
                            all_s = data['subjects']
                            all_s[st.session_state.my_name] = my_subs
                            supabase.table("team").update({"subjects": all_s}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()
                            
                    if my_subs:
                        st.write("")
                        st.markdown("### 🗑️ 등록된 과목 보드 삭제")
                        delete_target = st.selectbox("보드에서 삭제할 과목 선택", [s['name'] for s in my_subs], key="delete_selector")
                        if st.button("선택한 과목 영구 삭제", type="primary", use_container_width=True):
                            updated_subs = [s for s in my_subs if s['name'] != delete_target]
                            all_s = data['subjects']
                            all_s[st.session_state.my_name] = updated_subs
                            supabase.table("team").update({"subjects": updated_subs}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()

                with c_right:
                    if my_subs:
                        st.markdown("### ⚙️ AI 맞춤형 플랜 생성기")
                        target_sub = st.selectbox("AI 관리 타겟 과목 선택", [s['name'] for s in my_subs])
                        st.session_state.input_manual_text = st.text_area("학습 교안 본문 및 AI 세부 지시문 입력", value=st.session_state.input_manual_text, height=100, placeholder="여기에 요약할 텍스트를 붙여넣거나 세부 지시 사항을 입력하세요.")
                        
                        up_files = st.file_uploader(f"{target_sub} 자료 업로드 (여러 개 선택 가능)", type=['pdf', 'txt'], key="uploader_dash", accept_multiple_files=True)
                        
                        extracted = "".join([extract_text(f) for f in up_files]) if up_files else ""
                        combined_content = f"{st.session_state.input_manual_text}\n{extracted}".strip()
                        
                        cd1, cd2 = st.columns(2)
                        days = cd1.number_input("목표 학습 기간 (일)", 1, 100, value=st.session_state.input_days)
                        st.session_state.input_days = days
                        grade = cd2.selectbox("달성 목표 학점 레벨", ["A+", "B+", "Pass"], index=["A+", "B+", "Pass"].index(st.session_state.input_grade))
                        st.session_state.input_grade = grade
                        
                        if st.button("🤖 AI 맞춤형 일차별 계획 설계", type="primary", use_container_width=True):
                            if combined_content:
                                st.session_state[f"saved_doc_{target_sub}"] = combined_content
                                
                                for s in my_subs:
                                    if s['name'] == target_sub:
                                        s['total_days'] = days
                                        s['current_day'] = 1
                                        
                                ml = data['members']
                                for m_block in ml:
                                    if m_block['name'] == st.session_state.my_name: 
                                        m_block['grade'] = grade
                                        m_block['days'] = f"{days}일"
                                supabase.table("team").update({"members": ml, "subjects": data['subjects']}).eq("invite_code", st.session_state.invite_code).execute()
                                run_ai_engine("plan", sub_name=target_sub, grade=grade, days=days, content=combined_content)
                                del combined_content
                                gc.collect()
                            else:
                                st.warning("일정을 설계할 텍스트 본문이나 지시사항을 채워넣어 주세요.")

                if my_subs:
                    st.divider()
                    st.markdown("### 🚀 오늘자 미션 집중 포화 및 몰입 런처")
                    
                    cl1, cl2, cl3 = st.columns([1.5, 1, 1])
                    with cl1:
                        selected_sub_to_study = st.selectbox("오늘 완전히 몰입하여 파괴할 과목 고르기", [s['name'] for s in my_subs], key="study_selector")
                    
                    matched_sub = next((s for s in my_subs if s['name'] == selected_sub_to_study), my_subs[0])
                    current_sub_day = matched_sub.get('current_day', 1)
                    max_sub_day = matched_sub.get('total_days', 7)
                    
                    with cl2:
                        chosen_day = st.selectbox("진행할 목표 일차 체크", [i for i in range(1, max_sub_day + 1)], index=min(current_sub_day - 1, max_sub_day - 1))
                    
                    with cl3:
                        st.write("")
                        st.write("")
                        if st.button("🔥 몰입 모드 화면 가동", type="primary", use_container_width=True):
                            st.session_state.active_subject = selected_sub_to_study
                            st.session_state.active_day = chosen_day
                            st.session_state.current_mode = 'focus'
