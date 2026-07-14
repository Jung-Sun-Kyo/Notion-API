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
        return None # 에러 발생 시 None 반환

    pages = response.json().get("results", [])
    matched_posts = []

    for page in pages:
        properties = page.get("properties", {})
        
        # '이름', '제목', 'Name' 모두 대응하도록 수정
        title_prop = properties.get("이름") or properties.get("제목") or properties.get("Name") or {}
        title_title = title_prop.get("title", [])
        title = title_title[0].get("plain_text", "제목 없음") if title_title else "제목 없음"
        
        date_prop = properties.get("작성일") or properties.get("Created time") or {}
        
        date_str = None
        if date_prop.get("type") == "created_time":
            date_str = date_prop.get("created_time")
        elif date_prop.get("type") == "date" and date_prop.get("date"):
            date_str = date_prop.get("date", {}).get("start")
            
        if not date_str:
            continue
            
        try:
            post_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(KST)
        except Exception:
            continue
            
        if post_date.year < current_year and post_date.strftime("%m-%d") == target_md:
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
    KST = timezone(timedelta(hours=9))
    today_str = datetime.now(KST).strftime("%m월 %d일")
    
    if posts is None:
        text = "❌ 노션 데이터베이스 연결에 에러가 발생했습니다."
    elif not posts:
        # 테스트용: 과거의 오늘 글이 없어도 시스템이 정상 작동 중임을 알림
        text = f"📅 *{today_str}* 연동 테스트 성공!\n과거의 오늘 작성한 글이 데이터베이스에 없습니다."
    else:
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
    
    requests.post(telegram_url, json=payload)

if __name__ == "__main__":
    posts = get_past_today_posts()
    send_telegram_message(posts)
