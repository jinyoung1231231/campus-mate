import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import random
import string
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh
from PyPDF2 import PdfReader

# 1. 스타일 리뉴얼 (CSS 주입 - 에러 수정 완료)
st.markdown("""
<style>
    /* 전체 앱 배경 및 기본 글꼴 부드럽게 */
    .stApp {
        background-color: #f8f9fa;
    }
    /* 타이머 카드 디자인 */
    .timer-container {
        background: linear-gradient(135deg, #1e3a8a, #3b82f6);
        color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    /* 일반 일정 카드 디자인 */
    .plan-card {
        background-color: white;
        border-left: 5px solid #cbd5e1;
        padding: 15px;
        border-radius: 4px 8px 8px 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 12px;
        color: #334155;
    }
    /* 현재 진행 중인 하이라이트 일정 카드 디자인 */
    .active-plan-card {
        background-color: #fff7ed;
        border-left: 5px solid #f97316;
        padding: 18px;
        border-radius: 4px 8px 8px 4px;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.15);
        margin-bottom: 1
