import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# 1. 노션 스타일 및 동적 타임라인 전용 CSS 주입
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
    .subject-card {
        background-color: #fbfbfa;
        border: 1px solid #ededeb;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .subject-title {
        font-size: 16px;
        font-weight: 600;
        color: #37352f;
        margin-bottom: 8px;
    }
    .progress-text {
        font-size: 12px;
        color: #7c7b77;
        margin-top: 4px;
    }
    .schedule-box {
        background-color: #f7f7f5;
        border-radius: 6px;
        padding: 10px 14px;
        margin-top: 10px;
        border-left: 3px solid #60a5fa;
    }
    .schedule-item {
        font-size: 12px;
        color: #4b5563;
        margin-bottom: 4px;
    }
    
    /* [신규 설계] 노션 스타일 타임라인 마일스톤 보드 인터페이스 디자인 */
    .timeline-container {
        background-color: #ffffff;
        border: 1px solid #e3e2e0;
        border-radius: 8px;
        padding: 20px;
        margin-top: 16px;
        margin-bottom: 24px;
    }
    .timeline-title {
        font-size: 16px;
        font-weight: 700;
        color: #37352f;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .timeline-row {
        display: flex;
        align-items: flex-start;
        padding: 12px 0;
        border-bottom: 1px solid #f1f1ef;
    }
    .timeline-row:last-child {
        border-bottom: none;
    }
    .timeline-day-badge {
        min-width: 80px;
        font-weight: 700;
        font-size: 13px;
        color: #37352f;
        padding: 2px 6px;
        border-radius: 4px;
        text-align: center;
    }
    .badge-waiting { background-color: #f1f1ef; color: #7c7b77; }
    .badge-active { background-color: #e2f3f5; color: #238387; border: 1px solid #238387; }
    .badge-done { background-color: #eaf5ea; color: #2e7d32; }
    
    .timeline-content {
        padding-left: 16px;
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
    'current_ai_consult_q': '', 
    'current_ai_consult_a': '', 
    'input_manual_text': '',
    'input_days': 7,
    'input_grade': 'A+',
    'refresh_lock': False  
}

for key, default in session_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default

# 4. 파일 본문 텍스트 파싱 유틸리티
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([p.extract_text() for p in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except:
        return ""

# 5. 제미나이 AI 백엔드 오케스트레이션 함수
def run_ai_engine(prompt_type, **kwargs):
    st.session_state.refresh_lock = True
    with st.spinner("AI가 핵심 데이터를 분석하고 있습니다... 📝"):
        try:
            today_str = datetime.now().strftime("%Y년 %m월 %d일")
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            
            valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if not valid_models:
                st.error("API 키가 유효하지 않거나 모델 목록을 불러올 수 없습니다.")
                st.session_state.refresh_lock = False
                return
            
            target_model = next((m for kw in ['flash-latest', '2.5-flash', '2.0-flash', '1.5-flash', 'flash'] for m in valid_models if kw in m and 'vision' not in m and 'lite' not in m), valid_models[0])
            model_instance = genai.GenerativeModel(target_model)

            if prompt_type == "plan":
                p = f"""오늘 날짜는 {today_str}입니다. 목표 성적: {kwargs['grade']}, 남은 기간: {kwargs['days']}일.
제공된 학습 자료를 바탕으로, 사용자가 매일 성실히 공부할 수 있도록 각 일차별 학습 미션을 명확히 구분하여 계획표를 짜주세요.

[작성 수칙]
반드시 하루의 스케줄은 한 줄로 끝나야 하며, 앞에 다른 수식어 없이 무조건 문장의 시작을 'Day 1:', 'Day 2:', 'Day 3:' 형태로 시작해야 합니다. 대시(-) 기호나 추가 줄바꿈을 쓰지 마세요.
예시:
Day 1: 로봇 센서 개론 기초 용어 정리 및 핵심 개념 3개 요약하기
Day 2: 적외선 센서 및 초음파 센서 데이터 연동 코드 정독하기

[학습 자료]
{kwargs['content'][:4000]}"""
                res = model_instance.generate_content(p)
                st.session_state.current_ai_plan = res.text
                st.session_state.current_ai_quiz = "" 
                
                # DB 원격 서버에 생성된 타임라인 텍스트 동기화 보존
                res_db = supabase.table("team").select("ai_plans").eq("invite_code", st.session_state.invite_code).execute()
                current_plans = res_db.data[0].get('ai_plans', {}) if res_db.data else {}
                if not current_plans: current_plans = {}
                current_plans[st.session_state.my_name] = res.text
                supabase.table("team").update({"ai_plans": current_plans}).eq("invite_code", st.session_state.invite_code).execute()

            elif prompt_type == "quiz":
                p = f"""아래 학습 자료를 바탕으로, 사용자의 목표 학점인 [{kwargs['grade']}] 수준에 맞는 핵심 변별력 퀴즈 3개를 정답 및 해설과 함께 출제해주세요.
질문 형식은 명확히 무조건 '문제 1:', '문제 2:', '문제 3:' 으로 시작해야 하며, 각 문제 아래에 정답과 정밀 해설을 배치하되 실전 모의고사 형태를 유지해 주세요.

[학습 자료]
{kwargs['content'][:4000]}"""
                res = model_instance.generate_content(p)
                st.session_state.current_ai_quiz = res.text

            elif prompt_type == "consult":
                p = f"학업 및 진로 고민 상담 내용입니다: {kwargs['q']}\n학생의 상황에 진심으로 공감하며 향후 진로 설계와 동기부여에 도움이 될 수 있는 구체적인 가이드와 솔루션을 제공해주세요."
                res = model_instance.generate_content(p)
                st.session_state.current_ai_consult_q = kwargs['q']
                st.session_state.current_ai_consult_a = res.text
            
            st.session_state.refresh_lock = False
            st.rerun()
                
        except Exception as e:
            st.session_state.refresh_lock = False
            st.error(f"AI 통신 및 데이터 연동 중 오류 발생: {e}")

# 6. 사용자 인증 및 팀 게이트웨이 렌더링
if st.session_state.page == 'gate':
    st.title("Check-Mate")
    
    un = st.text_input("사용자 닉네임 입력 (로그인)")
    
    if un:
        try:
            all_teams = supabase.table("team").select("*").execute().data
            my_teams = [t for t in all_teams if any(m['name'] == un for m in t['members'])]
            
            if my_teams:
                st.write(" 내 스터디 팀 목록")
                for t in my_teams:
                    if st.button(f"🏠 {t['team_name']} 입장하기", key=f"t_{t['invite_code']}"):
                        st.session_state.update({"invite_code": t['invite_code'], "my_name": un, "page": "dashboard"})
                        st.rerun()
            else:
                st.info("가입된 스터디 팀이 없습니다. 아래에서 팀을 생성하거나 초대 코드를 입력해 동시 접속하세요.")
        except:
            st.warning("데이터베이스 연결 상태를 점검 중입니다...")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(" 워크스페이스 팀 신규 생성")
            tn = st.text_input("새로운 스터디 팀 이름")
            if st.button("신규 워크스페이스 생성"):
                if tn and un:
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    supabase.table("team").insert({
                        "invite_code": code, "team_name": tn,
                        "members": [{"name": un, "status": "대기", "grade": "-", "days": "-", "total_time": 0}],
                        "subjects": {un: []}, "posts": [], "ai_plans": {un: ""}
                    }).execute()
                    st.session_state.update({"invite_code": code, "my_name": un, "page": "dashboard"})
                    st.rerun()
        with c2:
            st.subheader(" 기존 팀 워크스페이스 참여")
            ci = st.text_input("발급받은 초대 코드 입력")
            if st.button("공유 워크스페이스 입장"):
                res = supabase.table("team").select("*").eq("invite_code", ci).execute()
                if res.data:
                    d = res.data[0]; ml = d['members']; sl = d.get('subjects', {}) or {}; ap = d.get('ai_plans', {}) or {}
                    if not any(m['name'] == un for m in ml):
                        ml.append({"name": un, "status": "대기", "grade": "-", "days": "-", "total_time": 0})
                        sl[un] = []
                        if un not in ap: ap[un] = ""
                        supabase.table("team").update({"members": ml, "subjects": sl, "ai_plans": ap}).eq("invite_code", ci).execute()
                    st.session_state.update({"invite_code": ci, "my_name": un, "page": "dashboard"})
                    st.rerun()

# 7. 핵심 메인 워크스페이스 렌더링 
elif st.session_state.page == 'dashboard':
    if not st.session_state.invite_code: 
        st.session_state.page = 'gate'; st.rerun()

    if not st.session_state.refresh_lock:
        st_autorefresh(interval=2000, key="global_refresh_engine")
    
    res = supabase.table("team").select("*").eq("invite_code", st.session_state.invite_code).execute()
    data = res.data[0] if res.data else None
    
    if data:
        db_plans = data.get('ai_plans', {}) or {}
        if db_plans.get(st.session_state.my_name) and not st.session_state.current_ai_plan:
            st.session_state.current_ai_plan = db_plans.get(st.session_state.my_name)

        st.sidebar.markdown(f"<div class='notion-header' style='font-size:20px;'>📂 {data['team_name']}</div>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<div class='notion-sub'>사용자: {st.session_state.my_name} 님</div>", unsafe_allow_html=True)
        
        if st.session_state.current_mode in ['dashboard', 'result']:
            menu = st.sidebar.radio("내비게이션", [" 내 학습 보드 (메인)", "👥 팀원 실시간 페이스", " 공유 게시판", " AI 진로 및 학업 상담"])
        else:
            st.sidebar.warning("⚠️ 현재 공부/시험이 진행 중입니다. 메뉴 이동이 제한됩니다.")
            menu = " 내 학습 보드 (메인)"
            
        if st.sidebar.button("🚪 워크스페이스 로그아웃"):
            st.session_state.update({"invite_code": "", "page": "gate", "current_mode": "dashboard", "current_ai_plan": "", "current_ai_quiz": "", "current_ai_consult_q": "", "current_ai_consult_a": "", "timer_running": False})
            st.rerun()
            
        with st.sidebar.expander("🎫 워크스페이스 초대코드"):
            st.code(data['invite_code'])

        # =========================================================================
        # MODE 1: 대시보드 모드
        # =========================================================================
        if st.session_state.current_mode == 'dashboard':
            
            if menu == " 내 학습 보드 (메인)":
                st.markdown("<div class='notion-header'>📊 전 과목 진행도 대시보드</div>", unsafe_allow_html=True)
                st.markdown("<div class='notion-sub'>등록된 모든 과목의 러닝 페이스와 학사 일정을 한눈에 파악하고 즉시 몰입 모드로 진입하세요.</div>", unsafe_allow_html=True)
                
                my_subs = data['subjects'].get(st.session_state.my_name, [])
                
                if my_subs:
                    st.markdown("### 📂 현재 학습 진행 상황")
                    cols = st.columns(3)
                    for idx, sub in enumerate(my_subs):
                        col_target = cols[idx % 3]
                        with col_target:
                            sub_name = sub['name']
                            total_days = sub.get('total_days', 7)
                            current_day = sub.get('current_day', 1)
                            
                            progress_ratio = min(current_day / total_days, 1.0)
                            progress_percent = int(progress_ratio * 100)
                            
                            task_week = sub.get('task_week', '3주차')
                            exam_week = sub.get('exam_week', '8주차 중간고사')
                            
                            st.markdown(f"""
                            <div class='subject-card'>
                                <div class='subject-title'>📚 {sub_name}</div>
                                <div style='font-size: 13px; color:#37352f;'><b>현재 진행:</b> Day {current_day} / {total_days}일 구성</div>
                                <div class='progress-text'>과정 이수율: {progress_percent}%</div>
                                <div class='schedule-box'>
                                    <div class='schedule-item'>📅 <b>과제 제출일:</b> {task_week}</div>
                                    <div class='schedule-item'>📝 <b>시험 주차:</b> {exam_week}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.progress(progress_ratio)
                else:
                    st.info("현재 등록된 학습 과목이 없습니다. 아래 컴포넌트에서 과목을 추가하고 AI 맞춤 플랜을 생성해 보세요!")

                # -----------------------------------------------------------------
                # [핵심 리뉴얼] 노션식 타임라인 보드 시각화 빌드 영역
                # -----------------------------------------------------------------
                if my_subs and st.session_state.current_ai_plan:
                    st.write("")
                    st.markdown("### 🗓️ AI 생성 동적 타겟 타임라인 보드")
                    
                    # 파싱 전용 전처리 (줄바꿈 단위 분할)
                    raw_lines = st.session_state.current_ai_plan.split('\n')
                    parsed_missions = {}
                    
                    for row_line in raw_lines:
                        if "Day" in row_line and ":" in row_line:
                            try:
                                day_part, mission_part = row_line.split(":", 1)
                                # 숫자 추출
                                day_num = int(''.join(filter(str.isdigit, day_part)))
                                parsed_missions[day_num] = mission_part.strip()
                            except:
                                pass
                    
                    # 카드에서 고른 현재 몰입 대상 타겟 과목 매칭 조회
                    active_sub_name = st.session_state.active_subject if st.session_state.active_subject else my_subs[0]['name']
                    matched_sub = next((s for s in my_subs if s['name'] == active_sub_name), my_subs[0])
                    sub_curr_day = matched_sub.get('current_day', 1)
                    sub_max_days = matched_sub.get('total_days', 7)
                    
                    st.markdown(f"""
                    <div class='timeline-container'>
                        <div class='timeline-title'>📋 <b>{active_sub_name}</b> 과목 일차별 핵심 트래킹 라인</div>
                    """, unsafe_allow_html=True)
                    
                    # 기간 스케줄 인덱스에 따라 동적 그리드 한 칸씩 하단 하강 조립
                    for d_i in range(1, sub_max_days + 1):
                        mission_desc = parsed_missions.get(d_i, "교안 핵심 텍스트 정독 및 일차별 학습 과제 완수")
                        
                        # 상태 평가 분기 처리
                        if d_i < sub_curr_day:
                            badge_class = "badge-done"
                            status_label = "✅ 완료"
                        elif d_i == sub_curr_day:
                            badge_class = "badge-active"
                            status_label = "🔥 진행"
                        else:
                            badge_class = "badge-waiting"
                            status_label = "🔒 대기"
                            
                        st.markdown(f"""
                        <div class='timeline-row'>
                            <div class='timeline-day-badge {badge_class}'>Day {d_i} ({status_label})</div>
                            <div class='timeline-content'>{mission_desc}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    st.markdown("</div>", unsafe_allow_html=True)

                st.divider()

                c_left, c_right = st.columns([1, 1])
                with c_left:
                    st.markdown("#### ➕ 신규 과목 및 주요 학사 일정 등록")
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
                            all_s = data['subjects']; all_s[st.session_state.my_name] = my_subs
                            supabase.table("team").update({"subjects": all_s}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()
                            
                    if my_subs:
                        st.write("")
                        st.markdown("#### 🗑️ 등록된 과목 보드 삭제")
                        delete_target = st.selectbox("보드에서 삭제할 과목 선택", [s['name'] for s in my_subs], key="delete_selector")
                        if st.button("선택한 과목 영구 삭제", type="primary", use_container_width=True):
                            updated_subs = [s for s in my_subs if s['name'] != delete_target]
                            all_s = data['subjects']
                            all_s[st.session_state.my_name] = updated_subs
                            supabase.table("team").update({"subjects": all_s}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()
                
                with c_right:
                    if my_subs:
                        target_sub = st.selectbox("⚙️ AI 관리 타겟 과목 선택", [s['name'] for s in my_subs])
                        st.session_state.input_manual_text = st.text_area("학습 교안 본문 및 AI 세부 지시문 입력", value=st.session_state.input_manual_text, height=100, placeholder="여기에 요약할 텍스트를 붙여넣거나 세부 지시 사항을 입력하세요.")
                        up_file = st.file_uploader("교안 파일 로드 (PDF/TXT)", type=['pdf', 'txt'], key="uploader_dash")
                        
                        extracted = extract_text(up_file) if up_file else ""
                        combined_content = f"{st.session_state.input_manual_text}\n{extracted}".strip()
                        
                        cd1, cd2 = st.columns(2)
                        days = cd1.number_input("목표 학습 기간 (일)", 1, 100, value=st.session_state.input_days)
                        st.session_state.input_days = days
                        grade = cd2.selectbox("달성 목표 학점 레벨", ["A+", "B+", "Pass"], index=["A+", "B+", "Pass"].index(st.session_state.input_grade))
                        st.session_state.input_grade = grade
                        
                        if st.button("🤖 AI 맞춤형 일차별 계획 설계", type="primary", use_container_width=True):
                            if combined_content:
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
                                run_ai_engine("plan", grade=grade, days=days, content=combined_content)
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
                            
                            st.session_state.timer_running = True
                            st.session_state.start_time = time.time()
                            
                            ml = data['members']
                            for m_block in ml:
                                if m_block['name'] == st.session_state.my_name: 
                                    m_block['status'] = f"🎯 {selected_sub_to_study} (Day {chosen_day}) 공부 중"
                            supabase.table("team").update({"members": ml}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()

            elif menu == "👥 팀원 실시간 페이스":
                st.markdown("<div class='notion-header'>👥 스터디 팀원 실시간 러닝 페이스</div>", unsafe_allow_html=True)
                st.markdown("<div class='notion-sub'>함께 몰입하는 팀원들의 현재 모드, 학습 상태 및 오늘 누적 공부 시간을 실시간으로 공유합니다.</div>", unsafe_allow_html=True)
                
                room_owner = data['members'][0]['name'] if data['members'] else ""
                
                for idx_m, m_block in enumerate(data['members']):
                    owner_badge = "👑 방장" if m_block['name'] == room_owner else "👤 팀원"
                    
                    st.markdown(f"""
                    <div class='subject-card' style='border-left: 4px solid #238387;'>
                        <span style='font-size:16px; font-weight:700;'>{owner_badge} : {m_block['name']}님</span> | 
                        <span style='color:#238387; font-weight:600;'>현재 상태: {m_block['status']}</span>
                        <div style='margin-top:8px; font-size:13px; color:#7c7b77;'>
                            🎯 목표 레벨: {m_block.get('grade', '-')} | 설정 기간: {m_block.get('days', '-')} | ⏱️ 오늘 누적 집중 시간: <b>{m_block.get('total_time', 0)}분</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    sub_list = data['subjects'].get(m_block['name'], [])
                    if sub_list:
                        sub_badges = " | ".join([f"📚 {s['name']} (Day {s.get('current_day', 1)})" for s in sub_list])
                        st.markdown(f"<div style='font-size:12px; color:#7c7b77; padding-left:12px;'>가동 중인 보드: {sub_badges}</div>", unsafe_allow_html=True)
                    st.write("")

            elif menu == " 공유 게시판":
                st.markdown("<div class='notion-header'>📌 팀 공유 작업 게시판</div>", unsafe_allow_html=True)
                with st.form("b_form_notion"):
                    t, c = st.text_input("게시글 제목"), st.text_area("내용 공유")
                    if st.form_submit_button("보드에 포스팅 등록"):
                        if t and c:
                            ps = data['posts']; ps.append({"title": t, "content": c, "author": st.session_state.my_name})
                            supabase.table("team").update({"posts": ps}).eq("invite_code", st.session_state.invite_code).execute()
                            st.rerun()
                
                for idx, p in enumerate(reversed(data['posts'])):
                    real_idx = len(data['posts']) - 1 - idx
                    with st.expander(f"📄 {p['title']} — [작성자: {p['author']}]"):
                        st.write(p['content'])
                        if p['author'] == st.session_state.my_name:
                            if st.button("🗑️ 포스팅 삭제", key=f"del_{real_idx}"):
                                current_posts = data['posts']
                                current_posts.pop(real_idx)
                                supabase.table("team").update({"posts": current_posts}).eq("invite_code", st.session_state.invite_code).execute()
                                st.rerun()

            elif menu == " AI 진로 및 학업 상담":
                st.markdown("<div class='notion-header'>🔮 AI 1:1 진로 및 학업 전용 상담소</div>", unsafe_allow_html=True)
                user_query = st.text_area("현재 학업 설계나 진로 선택, 슬럼프 고민에 대해 자유롭게 입력해 주세요.", height=150, placeholder="예: 전공 공부가 적성에 안 맞는 것 같아요. / 학점 관리 요령을 알고 싶어요.")
                
                if st.button("멘토 AI에게 정밀 고민 솔루션 신청", type="primary", use_container_width=True):
                    if user_query:
                        run_ai_engine("consult", q=user_query)
                            
                if st.session_state.current_ai_consult_a:
                    st.markdown(f"""
                    <div class='consult-container'>
                        <div style='font-size: 16px; font-weight: 700; color: #37352f; margin-bottom: 12px;'>🔮 AI 멘토의 1:1 비밀 맞춤 솔루션</div>
                        <div class='consult-user-q'>👤 <b>제출한 고민 내역:</b><br>{st.session_state.current_ai_consult_q}</div>
                        <div class='consult-ai-a'>🤖 <b>AI 마인드 조언 가이드:</b><br><br>{st.session_state.current_ai_consult_a.replace('\n', '<br>')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.write("")
                    st.info("💡 위 입력창에 고민을 작성하고 신청 버튼을 누르시면, AI 멘토가 분석한 1:1 맞춤 피드백 보고서가 바로 이 자리에 출력됩니다.")

        # =========================================================================
        # MODE 2: 몰입 모드
        # =========================================================================
        elif st.session_state.current_mode == 'focus':
            st.markdown(f"<div class='notion-header'>⚡ IMMERSION FOCUS MODE</div>", unsafe_allow_html=True)
