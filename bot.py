import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from analyzer import analyze_match, analyze_daily_matches

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))


async def send_message(bot: Bot, text: str):
    await bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        parse_mode="Markdown"
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏆 *בוט ניתוח מונדיאל 2026 מוכן!*\n\n"
        "פקודות זמינות:\n"
        "/analyze [קבוצה1] vs [קבוצה2] [שעה] - ניתוח משחק ספציפי\n"
        "/today - ניתוח כל משחקי היום\n"
        "/tomorrow - ניתוח משחקי מחר\n"
        "/lineups [קבוצה1] vs [קבוצה2] - עדכון אחרי פרסום הרכבים",
        parse_mode="Markdown"
    )


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args)
    if "vs" not in args.lower():
        await update.message.reply_text("שימוש: /analyze ברזיל vs ארגנטינה 22:00")
        return

    parts = args.split("vs", 1)
    team1 = parts[0].strip()
    rest = parts[1].strip().split()
    team2 = rest[0] if rest else ""
    time = rest[1] if len(rest) > 1 else "לא צוין"

    await update.message.reply_text(f"🔍 מנתח: {team1} נגד {team2}...\nזה יקח כ-30 שניות")

    result = analyze_match(team1, team2, time)
    await send_message(context.bot, result)


async def cmd_lineups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args)
    if "vs" not in args.lower():
        await update.message.reply_text("שימוש: /lineups ברזיל vs ארגנטינה")
        return

    parts = args.split("vs", 1)
    team1 = parts[0].strip()
    team2 = parts[1].strip()

    await update.message.reply_text(f"🔄 מעדכן ניתוח עם הרכבים רשמיים:\n{team1} נגד {team2}")

    result = analyze_match(team1, team2, "כפי שנקבע", with_lineups=True)
    await send_message(context.bot, result)


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 מחפש משחקי היום ומנתח... זה יקח כדקה")

    today = datetime.now().strftime("%d/%m/%Y")
    matches = [{"team1": "לפי לוח המשחקים", "team2": "של היום", "time": today}]

    result = analyze_daily_matches(matches)
    await send_message(context.bot, result)


async def cmd_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 מנתח משחקי מחר...")

    from datetime import timedelta
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    matches = [{"team1": "לפי לוח המשחקים", "team2": "של מחר", "time": tomorrow}]

    result = analyze_daily_matches(matches)
    await send_message(context.bot, result)


async def morning_briefing(context: ContextTypes.DEFAULT_TYPE):
    logger.info("שולח ניתוח בוקר...")
    from datetime import timedelta
    today = datetime.now().strftime("%d/%m/%Y")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")

    intro = (
        "☀️ *בוקר טוב! ניתוח מונדיאל יומי*\n"
        f"📅 {today}\n\n"
        "מחפש ומנתח את כל המשחקים של היום ומחר..."
    )
    await context.bot.send_message(chat_id=CHAT_ID, text=intro, parse_mode="Markdown")

    matches = [
        {"team1": "משחקי היום", "team2": f"{today}", "time": today},
        {"team1": "משחקי מחר", "team2": f"{tomorrow}", "time": tomorrow},
    ]
    result = analyze_daily_matches(matches)
    await send_message(context.bot, result)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("lineups", cmd_lineups))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("tomorrow", cmd_tomorrow))

    # ניתוח בוקר בשעה 08:00 כל יום
    app.job_queue.run_daily(
        morning_briefing,
        time=datetime.strptime("08:00", "%H:%M").time(),
        name="morning_briefing"
    )

    logger.info("🚀 הבוט פועל!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
