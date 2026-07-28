import os
import requests
from datetime import datetime, timezone, timedelta

NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def get_past_today_posts():
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)
    target_md = now.strftime("%m-%d") 
    current_year = now.year

    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers)
    if response.status_code != 200:
        print(f"Notion API 에러: {response.text}")
        return None

    pages = response.json().get("results", [])
    matched_posts = []

    for page in pages:
        properties = page.get("properties", {})
        
        # 제목 속성 찾기
        title_prop = properties.get("이름") or properties.get("제목") or properties.get("Name") or {}
        title_title = title_prop.get("title", [])
        title = title_title[0].get("plain_text", "제목 없음") if title_title else "제목 없음"
        
        # 날짜 속성 찾기
        date_prop = properties.get("작성일") or properties.get("Created time") or properties.get("날짜") or {}
        
        date_str = None
        if date_prop.get("type") == "created_time":
            date_str = date_prop.get("created_time")
        elif date_prop.get("type") == "date" and date_prop.get("date"):
            date_str = date_prop.get("date", {}).get("start")
            
        if not date_str:
            continue
            
        try:
            # ISO 날짜 형식 변환 (YYYY-MM-DD만 있는 경우 처리 추가)
            if len(date_str) == 10:
                post_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=KST)
            else:
                post_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(KST)
        except Exception as e:
            print(f"날짜 변환 에러 ({title}): {e}")
            continue
            
        # [핵심 수정] 월-일만 맞으면 일단 감지하도록 수정 (오늘 테스트용 글 포함)
        if post_date.strftime("%m-%d") == target_md:
            year_diff = current_year - post_date.year
            page_id = page.get("id").replace("-", "")
            notion_url = f"https://www.notion.so/{page_id}"
            
            matched_posts.append({
                "title": title,
                "year_diff": year_diff,
                "url": notion_url,
                "date": post_date.strftime("%Y-%m-%d")
            })
            
    return matched_posts

def send_telegram_message(posts):
    KST = timezone(timedelta(hours=9))
    today_str = datetime.now(KST).strftime("%m월 %d일")
    
    if posts is None:
        text = "❌ 노션 데이터베이스 연결에 에러가 발생했습니다."
    elif not posts:
        text = f"📅 *{today_str}* 연동 테스트 성공!\n오늘 또는 과거의 오늘 작성한 글이 데이터베이스에 없습니다."
    else:
        text = f"📜 *오늘/과거의 오늘 ({today_str}) 내가 쓴 글*\n\n"
        for post in posts:
            label = "오늘 작성" if post['year_diff'] == 0 else f"{post['year_diff']}년 전 오늘"
            text += f"▪️ *{label}* ({post['date']})\n"
            text += f"🔗 [{post['title']}]({post['url']})\n\n"
        
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    requests.post(telegram_url, json=payload)

if __name__ == "__main__":
    posts = get_past_today_posts()
    send_telegram_message(posts)
