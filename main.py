import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
from collections import Counter
import os

# 💡 [핵심] 스트림릿 클라우드(리눅스) 환경에서 자바(JVM) 경로 자동 매칭
if not os.environ.get("JAVA_HOME"):
    possible_java_paths = [
        "/usr/lib/jvm/default-java",
        "/usr/lib/jvm/java-11-openjdk-amd64",
        "/usr/lib/jvm/java-17-openjdk-amd64",
        "/usr/lib/jvm/java-8-openjdk-amd64"
    ]
    for path in possible_java_paths:
        if os.path.exists(path):
            os.environ["JAVA_HOME"] = path
            break

# 자바 설정 후 KoNLPy 로드
from konlpy.tag import Okt

# 1. 페이지 설정
st.set_page_config(page_title="YouTube Comment Analyzer", layout="wide", page_icon="📊")

st.title("📊 유튜브 댓글 심층 분석 대시보드")
st.markdown("유튜브 영상 링크를 입력하면 댓글을 수집하고 한글 워드클라우드 및 주요 키워드를 분석합니다.")

# 2. 유튜브 API 키 로드
try:
    YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
except Exception:
    st.sidebar.error("🔑 API 키를 찾을 수 없습니다. 사이드바에 직접 입력하거나 Streamlit Secrets 설정을 확인해주세요.")
    YOUTUBE_API_KEY = st.sidebar.text_input("YouTube API Key 입력:", type="password")

# 3. 유튜브 영상 ID 추출 함수
def extract_video_id(url):
    pattern = r'(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

# 4. 유튜브 댓글 수집 함수
@st.cache_data(show_spinner=False)
def get_youtube_comments(video_id, api_key, max_results=100):
    if not api_key:
        return []
    
    youtube = build('youtube', 'v3', developerKey=api_key)
    comments = []
    
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            textFormat="plainText",
            maxResults=min(max_results, 100)
        )
        
        while request and len(comments) < max_results:
            response = request.execute()
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                comments.append(comment)
                
            if 'nextPageToken' in response and len(comments) < max_results:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    textFormat="plainText",
                    pageToken=response['nextPageToken'],
                    maxResults=min(max_results - len(comments), 100)
                )
            else:
                break
    except Exception as e:
        st.error(f"유튜브 API 호출 중 오류 발생: {e}")
        return []
        
    return comments

# 5. 한글 형태소 분석 및 명사 추출 함수
def process_korean_text(comments):
    okt = Okt()
    all_nouns = []
    
    # 💡 SyntaxError가 났던 불용어(stopwords) 리스트 선언을 한 줄로 안전하게 묶었습니다.
    stopwords = ['진짜', '보고', '영상', '이거', '완전', '대박', '유튜브', '구독', '좋아요', '인간', '사람', '생각', '때문', '댓글', '진짜로']
    
    for comment in comments:
        clean_comment = re.sub(r'[^가-힣a-zA-Z\s]', '', comment)
        nouns = okt.nouns(clean_comment)
        filtered_nouns = [n for n in nouns if len(n) > 1 and n not in stopwords]
        all_nouns.extend(filtered_nouns)
        
    return all_nouns

# ----------------- 사이드바 설정 -----------------
st.sidebar.header("⚙️ 분석 설정 컨트롤러")
video_url = st.sidebar.text_input("유튜브 영상 URL 입력:", placeholder="https://www.youtube.com/watch?v=...")
max_comments = st.sidebar.slider("수집할 댓글 수", min_value=20, max_value=50
