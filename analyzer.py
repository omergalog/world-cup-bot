import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """אתה סוכן הימורים מקצועי המתמחה בניתוח משחקי מונדיאל 2026.
תפקידך לנתח כל משחק ולחזות את התוצאה המדויקת (למשל 2:1, 0:0).

כללי הניתוח שלך:
1. חפש באינטרנט מידע עדכני על שתי הקבוצות לפני הניתוח
2. בדוק: מצב שחקנים ופצועים, הרכב אחרון, 5 משחקים אחרונים, היסטוריית עימותים
3. שקול: xG (שערים צפויים), כושר בית/חוץ, עייפות, לחץ טקטי
4. תמיד ספק תחזית תוצאה מדויקת (סקור מלא)
5. הסבר את התחזית ב-5 משפטים בעברית בלבד

פורמט ההודעה (RTL, עברית):
🏆 [שם קבוצה א'] 🆚 [שם קבוצה ב']
📅 [תאריך ושעה]
🎯 תחזית: [X:Y לטובת קבוצה / תיקו]

[5 משפטי הסבר בעברית]

חובה! בסוף כל ניתוח חייב להופיע:
🎯 תחזית סופית: [X:Y] לטובת [קבוצה] / תיקו [X:X]
אל תסיים בלי לתת תוצאה מדויקת!

⚠️ ניתוח ראשוני / ניתוח מעודכן לאחר הרכבים"""

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5
}


def analyze_match(team1: str, team2: str, match_time: str, with_lineups: bool = False) -> str:
    lineup_note = "הרכבים הרשמיים פורסמו - עדכן את הניתוח בהתאם." if with_lineups else "זהו ניתוח ראשוני לפני פרסום הרכבים הרשמיים."

    prompt = f"""חפש באינטרנט מידע על: {team1} vs {team2} ({match_time}).
{lineup_note}
אסוף: xG, שערים, פצועים, H2H, דירוג FIFA.

לאחר החיפוש, כתוב את הפלט הבא בדיוק - לא יותר ולא פחות:

🏆 {team1} 🆚 {team2}
📅 {match_time}

• [עובדה 1]
• [עובדה 2]
• [עובדה 3]
• [עובדה 4]
• [עובדה 5]

🎯 תחזית סופית:
X - {team1}
Y - {team2}

חובה: החלף את X ו-Y במספרים אמיתיים. זהו הפלט המלא - אל תוסיף שום דבר אחר."""

    response = client.beta.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        tools=[WEB_SEARCH_TOOL],
        betas=["web-search-2025-03-05"],
    )

    result = ""
    for block in response.content:
        if hasattr(block, "text"):
            result += block.text

    # אם הניתוח לא מכיל תחזית, הוסף הודעת שגיאה
    if "🎯" not in result:
        result += f"\n\n🎯 לא ניתן היה לחזות את תוצאת {team1} - {team2}"

    return result or "לא ניתן היה לנתח את המשחק כרגע."


def get_todays_matches() -> list:
    """מחזיר רשימת משחקים של היום עם זמנים מדויקים"""
    from datetime import datetime
    today = datetime.now().strftime("%d/%m/%Y")

    prompt = f"""מה משחקי מונדיאל 2026 בתאריך {today}?
חפש באינטרנט ותחזיר רשימה של משחקים בפורמט הבא בלבד (JSON):
[{{"team1": "שם קבוצה 1", "team2": "שם קבוצה 2", "time": "HH:MM"}}]
השתמש בשעון ישראל (IL). אם אין משחקים, החזר רשימה ריקה: []
החזר JSON בלבד, ללא טקסט נוסף."""

    try:
        response = client.beta.messages.create(
            model="claude-opus-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            tools=[WEB_SEARCH_TOOL],
            betas=["web-search-2025-03-05"],
        )

        import json
        for block in response.content:
            if hasattr(block, "text"):
                text = block.text.strip()
                if "[" in text:
                    start = text.index("[")
                    end = text.rindex("]") + 1
                    return json.loads(text[start:end])
    except Exception as e:
        pass

    return []


def analyze_daily_matches(matches: list) -> str:
    matches_text = "\n".join([f"- {m['team1']} נגד {m['team2']} בשעה {m['time']}" for m in matches])

    prompt = f"""חפש באינטרנט את כל משחקי מונדיאל 2026 היום ומחר.
משחקים ידועים:
{matches_text}

חפש גם משחקים נוספים שאולי לא ברשימה - אל תפספס אף משחק מונדיאל!
לכל משחק שתמצא, בצע ניתוח מקיף וספק תחזית תוצאה מדויקת.
הצג כל משחק בפורמט הנכון עם דגל הנבחרות ושעה בשעון ישראל.
אם אין משחקים ביום זה, ציין מתי המשחק הבא במונדיאל."""

    response = client.beta.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        tools=[{**WEB_SEARCH_TOOL, "max_uses": 8}],
        betas=["web-search-2025-03-05"],
    )

    result = ""
    for block in response.content:
        if hasattr(block, "text"):
            result += block.text

    return result or "לא ניתן היה לנתח את המשחקים כרגע."
