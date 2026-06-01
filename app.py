import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# 1. 스타일 리뉴얼 (CSS 주입 오타 완전 수정)
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .timer-container {
        background: linear-gradient(135deg, #1e3a8a, #3b82f6);
        color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    .plan-card {
        background-color: white;
        border-left: 5px solid #cbd5e1;
        padding: 15px;
        border-radius: 4px 8px 8px 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 12px;
        color: #334155;
    }
    .active-plan-card {
        background-color: #fff7ed;
        border-left: 5px solid #f97316;
        padding: 18px;
        border-radius: 4px 8px 8px 4px;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.15);
        margin-bottom: 15px;
        color: #431407;
    }
</style>
""", unsafe_allow_html=True)

# 2. DB 연결
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# 3. 세션 상태 관리 (휘발 방지 세션 맵)
session_keys = {
    'page': 'gate',
    'my_name': '',
    'invite_code': '',
    'timer_running': False,
    'start_time': None,
    'elapsed_time': 0,
    'current_ai_plan': '',
    'current_ai_quiz': '',
    'current_ai_consult': '',
    'input_manual_text': '',
    'input_days': 7,
    'input_grade': 'A+'
}

for key, default in session_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default

# 4. 파일 텍스트 추출 함수
def extract_text(uploaded_file):
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            return "".join([p.extract_text() for p in reader.pages])
        return uploaded_file.getvalue().decode("utf-8")
    except:
        return ""

# 5. AI 핵심 구동 함수
def run_ai_engine(prompt_type, **kwargs):
    with st.spinner("AI가 분석 중입니다... 잠시만 기다려주세요. 📝"):
        try:
            today_str = datetime.now().strftime("%Y년 %m월 %d일")
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            
            valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if not valid_models:
                st.error("API 키가 올바르지 않습니다.")
                return
            
            target_model = next((m for kw in ['flash-latest', '2.5-flash', '2.0-flash', '1.5-flash', 'flash'] for m in valid_models if kw in m and 'vision' not in m and 'lite' not in m), valid_models[0])
            model_instance = genai.GenerativeModel(target_model)

            if prompt_type == "plan":
                p = f"""오늘 날짜는 {today_str}입니다. 목표 성적: {kwargs['grade']}, 남은 기간: {kwargs['days']}일.
아래 제공된 학습 자료를 바탕으로, 각 일차별 학습 내용을 명확히 구분하여 작성해주세요.
반드시 각 일차의 시작은 'Day 1:', 'Day 2:' 와 같은 형식으로 작성해야 하며, 표를 만들지 말고 줄글 형식으로 작성하되 일차별 구분을 확실히 해주세요.

[학습 자료]
{kwargs['content'][:4000]}"""
                res = model_instance.generate_content(p)
                st.session_state.current_ai_plan = res.text
                st.session_state.current_ai_quiz = "" 
                
                res_db = supabase.table("team").select("ai_plans").eq("invite_code", st.session_state.invite_code).execute()
                current_plans = res_db.data[0].get('ai_plans', {}) if res_db.data else {}
                if not current_plans: current_plans = {}
                current_plans[st.session_state.my_name] = res.text
                supabase.table("team").update({"ai_plans": current_plans}).eq("invite_code", st.session_state.invite_code).execute()

            elif prompt_type == "quiz":
                p = f"""아래 학습 자료를 바탕으로, 사용자의 목표
