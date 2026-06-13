import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from wordcloud import WordCloud
from konlpy.tag import Okt
import matplotlib.pyplot as plt
import re
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="YouTube Comment Analyzer", layout="wide", page_icon="📊")

st.title("📊 유튜브 댓글 심층 분석 대시보드")
st.markdown("유튜브 영상 링크를 입력하면 댓글을 수집하고 한글 워드클라우드 및 주요 키워드를 분석합니다.")

# 2. 유튜브 API 키 로드 (Streamlit Secrets 활용)
# 로컬 테스트 시에는 .streamlit/secrets.toml 파일에 입력하거나 아래 주석을 해제하세요.
# YOUTUBE_API_KEY = "YOUR_ACTUAL_API_KEY"
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
            maxResults=min(max_results, 100) # 한 번에 최대 100개
        )
        
        while request and len(comments) < max_results:
            response = request.execute()
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                comments.append(comment)
                
            # 다음 페이지가 있고, 목표 개수보다 적으면 계속 수집
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
    
    # 불용어 정의 (분석에서 제외할 의미 없는 단어들)
    stopwords = ['진짜', '진짜', '보고', '영상', '진짜', '이거', '완전', '대박', '유튜브', '구독', '좋아요', '인간', '사람', '생각', '때문']
    
    for comment in comments:
        # 한글, 영문, 공백만 남기고 특수문자 제거
        clean_comment = re.sub(r'[^가-힣a-zA-Z\s]', '', comment)
        # 명사 추출
        nouns = okt.nouns(clean_comment)
        # 2글자 이상이고 불용어가 아닌 단어만 필터링
        filtered_nouns = [n for n in nouns if len(n) > 1 and n not in stopwords]
        all_nouns.extend(filtered_nouns)
        
    return all_nouns

# ----------------- 사이드바 설정 -----------------
st.sidebar.header("⚙️ 분석 설정 컨트롤러")
video_url = st.sidebar.text_input("유튜브 영상 URL 입력:", placeholder="https://www.youtube.com/watch?v=...")
max_comments = st.sidebar.slider("수집할 댓글 수", min_value=20, max_value=500, value=100, step=20)

# ----------------- 메인 로직 -----------------
if video_url:
    video_id = extract_video_id(video_url)
    
    if not video_id:
        st.error("❌ 올바른 유튜브 URL 형식이 아닙니다. 다시 확인해주세요.")
    elif not YOUTUBE_API_KEY:
        st.warning("⚠️ 유튜브 API 키가 입력되지 않았습니다. 사이드바를 확인해주세요.")
    else:
        if st.sidebar.button("📊 심층 분석 시작", use_container_width=True):
            with st.spinner("유튜브 서버에서 댓글을 수집하고 명사를 분석하는 중..."):
                comments = get_youtube_comments(video_id, YOUTUBE_API_KEY, max_comments)
                
            if not comments:
                st.warning("수집된 댓글이 없거나 API 키가 올바르지 않습니다.")
            else:
                st.success(f"✅ 성공적으로 {len(comments)}개의 댓글을 수집했습니다!")
                
                # 데이터 가공
                nouns_list = process_korean_text(comments)
                word_counts = Counter(nouns_list)
                
                # 레이아웃 나누기 (2단 구조)
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("🔤 빈도수 높은 TOP 15 키워드")
                    if word_counts:
                        df_words = pd.DataFrame(word_counts.most_common(15), columns=['키워드', '빈도수'])
                        st.dataframe(df_words.set_index('키워드'), use_container_width=True)
                    else:
                        st.info("추출된 키워드가 없습니다.")
                        
                    st.subheader("💬 수집된 원본 댓글 (샘플)")
                    st.dataframe(pd.DataFrame(comments, columns=['댓글 내용']).head(20), use_container_width=True)

                with col2:
                    st.subheader("☁️ 한글 워드 클라우드 (Word Cloud)")
                    if word_counts:
                        # 리눅스 기반 스트림릿 클라우드에서도 깨지지 않는 나눔 폰트 경로 지정 예외처리
                        import platform
                        system_platform = platform.system()
                        
                        if system_platform == 'Windows':
                            font_path = 'malgun.ttf' # 윈도우 맑은고딕
                        elif system_platform == 'Darwin':
                            font_path = '/System/Library/Fonts/Supplemental/AppleGothic.ttf' # 맥 애플고딕
                        else:
                            # 스트림릿 클라우드(Linux 환경) 대응 내장 폰트 리스트 순회
                            import os
                            possible_fonts = [
                                '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
                                '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
                                '/usr/share/fonts/fonts-go/Go-Regular.ttf'
                            ]
                            font_path = None
                            for pf in possible_fonts:
                                if os.path.exists(pf):
                                    font_path = pf
                                    break
                        
                        # 워드클라우드 개체 생성
                        wc = WordCloud(
                            font_path=font_path,
                            background_color="white",
                            width=800,
                            height=600,
                            max_words=100,
                            colormap="inferno"
                        )
                        
                        # 그래프 그리기
                        fig, ax = plt.subplots(figsize=(10, 8))
                        wc.generate_from_frequencies(word_counts)
                        ax.imshow(wc, interpolation='bilinear')
                        ax.axis("off")
                        
                        # 스트림릿에 이미지 플롯 전달
                        st.pyplot(fig)
                    else:
                        st.info("워드클라우드를 생성할 키워드가 부족합니다.")
else:
    st.info("💡 왼쪽 사이드바에 유튜브 영상 주소를 입력하고 '심층 분석 시작' 버튼을 눌러주세요.")
