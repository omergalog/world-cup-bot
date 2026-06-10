import os
import time
import requests
import schedule
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from analyzer import analyze_daily_matches, analyze_match, get_todays_matches

load_dotenv()

# שעון ישראל אחיד לכל הבוט (השרת רץ ב-UTC)
IL_TZ = ZoneInfo("Asia/Jerusalem")


def now_il():
    """הזמן הנוכחי בשעון ישראל"""
    return datetime.now(IL_TZ)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# שמירת משחקי היום עם הזמנים שלהם
todays_matches = []
lineup_alerts_sent = set()  # כדי לא לשלוח פעמיים


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
            "*/analyze ברזיל vs ארגנטינה 22:00* - ניתוח משחק ספציפי\n\n"
            "🤖 כל בוקר בשעה 10:00 תקבל ניתוח אוטומטי\n"
            "🔄 חצי שעה לפני כל משחק תקבל ניתוח מעודכן עם ההרכבים"
        )

    elif text == "/today":
        send_message("🔍 מנתח משחקי היום... זה יקח כדקה")
        today = now_il().strftime("%d/%m/%Y")
        matches = [{"team1": "משחקי היום", "team2": today, "time": today}]
        result = analyze_daily_matches(matches)
        send_message(result)

    elif text == "/tomorrow":
        send_message("🔍 מנתח משחקי מחר...")
        tomorrow = (now_il() + timedelta(days=1)).strftime("%d/%m/%Y")
        matches = [{"team1": "משחקי מחר", "team2": tomorrow, "time": tomorrow}]
        result = analyze_daily_matches(matches)
        send_message(result)

    elif text.startswith("/lineups "):
        args = text[9:].strip()
        if "vs" in args:
            parts = args.split("vs", 1)
            team1 = parts[0].strip()
            rest = parts[1].strip().split()
            team2 = rest[0] if rest else ""
            match_time = rest[1] if len(rest) > 1 else "לא צוין"
            send_message(f"🔄 מנתח עם הרכבים: {team1} נגד {team2}...")
            result = analyze_match(team1, team2, match_time, with_lineups=True)
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


def morning_briefing():
    global todays_matches, lineup_alerts_sent
    lineup_alerts_sent = set()  # איפוס התראות הרכבים ליום חדש

    logger.info("שולח ניתוח בוקר...")
    today = now_il().strftime("%d/%m/%Y")
    tomorrow = (now_il() + timedelta(days=1)).strftime("%d/%m/%Y")

    send_message(
        f"☀️ *בוקר טוב! ניתוח מונדיאל יומי*\n"
        f"📅 {today}\n\n"
        "מחפש ומנתח את כל המשחקים..."
    )

    matches = [{"team1": "משחקי היום ומחר", "team2": f"{today} + {tomorrow}", "time": today}]
    result = analyze_daily_matches(matches)
    send_message(result)

    # עדכן את רשימת המשחקים לצורך התראות הרכבים — היום + מחר
    # (כדי לתפוס גם משחקי לילה אחרי חצות שמתחילים לפנות בוקר בשעון ישראל)
    todays_matches = get_todays_matches(today) + get_todays_matches(tomorrow)
    logger.info(f"נמצאו {len(todays_matches)} משחקים (היום + מחר)")


def check_lineup_alerts():
    """בדוק אם צריך לשלוח ניתוח מעודכן עם הרכבים (חצי שעה לפני כל משחק)"""
    global lineup_alerts_sent

    now = now_il()

    for match in todays_matches:
        match_id = f"{match['team1']}_vs_{match['team2']}"

        if match_id in lineup_alerts_sent:
            continue

        try:
            # בנה את מועד המשחק המלא (תאריך + שעה) בשעון ישראל
            match_date = match.get('date') or now.strftime("%d/%m/%Y")
            match_time = datetime.strptime(
                f"{match_date} {match['time']}", "%d/%m/%Y %H:%M"
            ).replace(tzinfo=IL_TZ)
            time_until = (match_time - now).total_seconds() / 60  # בדקות

            # שלח 30 דקות לפני המשחק
            if 0 <= time_until <= 35:
                lineup_alerts_sent.add(match_id)
                logger.info(f"שולח ניתוח הרכבים: {match_id}")

                send_message(
                    f"🔄 *ניתוח מעודכן עם הרכבים*\n"
                    f"⚽ {match['team1']} נגד {match['team2']}\n"
                    f"🕐 המשחק בעוד ~30 דקות\n\n"
                    "מחפש הרכבים רשמיים ומנתח..."
                )

                result = analyze_match(
                    match['team1'],
                    match['team2'],
                    match['time'],
                    with_lineups=True
                )
                send_message(result)

        except Exception as e:
            logger.error(f"שגיאה בבדיקת הרכבים: {e}")


def get_latest_offset():
    updates = get_updates()
    if updates:
        return updates[-1]["update_id"] + 1
    return None


def main():
    logger.info("🚀 בוט מונדיאל 2026 מתחיל...")

    # ניתוח בוקר בשעה 10:00 שעון ישראל (07:00 UTC, השרת ב-UTC + ישראל בשעון קיץ = UTC+3)
    schedule.every().day.at("07:00").do(morning_briefing)

    # בדיקת הרכבים כל 5 דקות
    schedule.every(5).minutes.do(check_lineup_alerts)

    # דלג על הודעות ישנות
    offset = get_latest_offset()
    logger.info(f"מתחיל מ-offset: {offset}")
    last_schedule_check = time.time()

    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            if text and chat_id:
                logger.info(f"פקודה: {text}")
                handle_command(text, chat_id)

        if time.time() - last_schedule_check >= 60:
            schedule.run_pending()
            last_schedule_check = time.time()

        time.sleep(2)


if __name__ == "__main__":
    main()
