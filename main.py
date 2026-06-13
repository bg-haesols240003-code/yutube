import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
from collections import Counter
import os

# ⭐ [오류 해결 핵심] 스트림릿 클라우드(리눅스) 환경에서 자바(JVM) 경로를 강제로 지정합니다.
# 이 코드는 konlpy를 import하기 전에 반드시 실행되어야 합니다.
if not os.environ.get("JAVA_HOME"):
    # 스트림릿 클라우드의 기본 자바 설치 경로를 탐색하여 등록합니다.
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

# 자바 환경 변수 설정 후 KoNLPy를 안전하게 불러옵니다.
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
    stopwords =
