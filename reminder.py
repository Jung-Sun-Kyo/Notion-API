import os
import requests
from datetime import datetime, timezone, timedelta

# 환경 변수에서 Secret 값 가져오기
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def get_past_today_posts():
    # 한국 시간(UTC+9) 기준으로 오늘 월-일 구하기
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)
    target_md = now.strftime("%m-%d") # 예: "07-14"
    current_year = now.year

    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # 데이터베이스의 모든 글 가져오기 (매년 같은 날짜 비교를 위해 전체 쿼리 후 코드에서 필터링)
    # 만약 데이터가 너무 많다면 작성일 속성 기준으로 정렬하거나 페이지네이션이 필요할 수 있습니다.
    response = requests.post(url, headers=headers)
    if response.status_code != 200:
        print(f"Notion API 에러: {response.text}")
        return []

    pages = response.json().get("results", [])
    matched_posts = []

    for page in pages:
        properties = page.get("properties", {})
        
        # 1. 제목 가져오기 (속성명이 '제목' 또는 'Name'일 수 있으므로 체크)
        title_prop = properties.get("제목") or properties.get("Name") or {}
        title_title = title_prop.get("title", [])
        title = title_title[0].get("plain_text", "제목 없음") if title_title else "제목 없음"
        
        # 2. 작성일 가져오기 (속성명이 '작성일' 또는 'Created time' 확인)
        # 생성 시간 속성(created_time) 형태인 경우와 날짜 속성(date) 형태인 경우를 모두 대응
        date_prop = properties.get("작성일") or properties.get("Created time") or {}
        
        date_str = None
        if date_prop.get("type") == "created_time":
            date_str = date_prop.get("created_time")
        elif date_prop.get("type") == "date" and date_prop.get("date"):
            date_str = date_prop.get("date", {}).get("start")
            
        if not date_str:
            continue
            
        # 노션 날짜 파싱 (ISO 포맷 대응)
        try:
            post_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(KST)
        except Exception:
            continue
            
        # 과거의 오늘인지 비교 (연도는 다르고, 월-일은 같은 경우)
        if post_date.year < current_year and post_date.strftime("%m-%d") == target_md:
            # 방문용 노션 웹 주소 변환 (notion.so 형식)
            page_id = page.get("id").replace("-", "")
            notion_url = f"https://www.notion.so/{page_id}"
            
            matched_posts.append({
                "title": title,
                "year_diff": current_year - post_date.year,
                "url": notion_url,
                "date": post_date.strftime("%Y-%m-%d")
            })
            
    return matched_posts

def send_telegram_message(posts):
    if not posts:
        # 과거의 오늘 쓴 글이 없으면 알림을 보내지 않거나 안내 메시지를 보낼 수 있습니다.
        # 여기서는 글이 있을 때만 보냅니다. 원하시면 주석을 해제하세요.
        # text = "📅 과거의 오늘 작성한 글이 없습니다."
        return

    KST = timezone(timedelta(hours=9))
    today_str = datetime.now(KST).strftime("%m월 %d일")
    
    text = f"📜 *과거의 오늘 ({today_str}) 내가 쓴 글*\n\n"
    for post in posts:
        text += f"▪️ *{post['year_diff']}년 전 오늘* ({post['date']})\n"
        text += f"🔗 [{post['title']}]({post['url']})\n\n"
        
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    res = requests.post(telegram_url, json=payload)
    if res.status_code != 200:
        print(f"텔레그램 발송 실패: {res.text}")

if __name__ == "__main__":
    posts = get_past_today_posts()
    send_telegram_message(posts)
