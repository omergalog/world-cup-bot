import os
import time
import requests
import schedule
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from analyzer import analyze_daily_matches, analyze_match

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.ok:
            logger.info("הודעה נשלחה בהצלחה")
        else:
            logger.error(f"שגיאה בשליחה: {r.text}")
    except Exception as e:
        logger.error(f"שגיאה: {e}")

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=35)
        return r.json().get("result", [])
    except:
        return []

def handle_command(text, chat_id):
    text = text.strip().lower()

    if text == "/start":
        send_message(
            "🏆 *בוט הימורי מונדיאל 2026 מוכן!*\n\n"
            "פקודות זמינות:\n"
            "*/today* - ניתוח משחקי היום\n"
            "*/tomorrow* - ניתוח משחקי מחר\n"
            "*/analyze ברזיל vs ארגנטינה 22:00* - ניתוח משחק ספציפי\n"
            "*/lineups ברזיל vs ארגנטינה* - עדכון אחרי הרכבים"
        )

    elif text == "/today":
        send_message("🔍 מנתח משחקי היום... זה יקח כדקה")
        today = datetime.now().strftime("%d/%m/%Y")
        matches = [{"team1": "משחקי היום", "team2": today, "time": today}]
        result = analyze_daily_matches(matches)
        send_message(result)

    elif text == "/tomorrow":
        send_message("🔍 מנתח משחקי מחר...")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
        matches = [{"team1": "משחקי מחר", "team2": tomorrow, "time": tomorrow}]
        result = analyze_daily_matches(matches)
        send_message(result)

    elif text.startswith("/analyze "):
        args = text[9:].strip()
        if "vs" in args:
            parts = args.split("vs", 1)
            team1 = parts[0].strip()
            rest = parts[1].strip().split()
            team2 = rest[0] if rest else ""
            match_time = rest[1] if len(rest) > 1 else "לא צוין"
            send_message(f"🔍 מנתח: {team1} נגד {team2}...")
            result = analyze_match(team1, team2, match_time)
            send_message(result)

    elif text.startswith("/lineups "):
        args = text[9:].strip()
        if "vs" in args:
            parts = args.split("vs", 1)
            team1 = parts[0].strip()
            team2 = parts[1].strip()
            send_message(f"🔄 מעדכן עם הרכבים רשמיים: {team1} נגד {team2}...")
            result = analyze_match(team1, team2, "כפי שנקבע", with_lineups=True)
            send_message(result)

def morning_briefing():
    logger.info("שולח ניתוח בוקר...")
    today = datetime.now().strftime("%d/%m/%Y")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")

    send_message(
        f"☀️ *בוקר טוב! ניתוח מונדיאל יומי*\n"
        f"📅 {today}\n\n"
        "מחפש ומנתח את כל המשחקים..."
    )

    matches = [
        {"team1": "משחקי היום ומחר", "team2": f"{today} + {tomorrow}", "time": today}
    ]
    result = analyze_daily_matches(matches)
    send_message(result)

def get_latest_offset():
    """קבל את ה-offset האחרון כדי לדלג על הודעות ישנות"""
    updates = get_updates()
    if updates:
        return updates[-1]["update_id"] + 1
    return None

def main():
    logger.info("🚀 בוט מונדיאל 2026 מתחיל...")

    # ניתוח בוקר בשעה 09:00
    schedule.every().day.at("09:00").do(morning_briefing)

    # דלג על הודעות ישנות
    offset = get_latest_offset()
    logger.info(f"מתחיל מ-offset: {offset}")
    last_schedule_check = time.time()

    while True:
        # בדיקת הודעות נכנסות
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            if text and chat_id:
                logger.info(f"פקודה: {text}")
                handle_command(text, chat_id)

        # בדיקת משימות מתוזמנות כל דקה
        if time.time() - last_schedule_check >= 60:
            schedule.run_pending()
            last_schedule_check = time.time()

        time.sleep(2)

if __name__ == "__main__":
    main()
