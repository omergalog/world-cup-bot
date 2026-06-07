import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """אתה סוכן הימורים מקצועי המתמחה בניתוח משחקי כדורגל - מונדיאל 2026 וכל משחקי נבחרות אחרים.
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

    prompt = f"""משחק: {team1} נגד {team2} | {match_time}
{lineup_note}

חפש באינטרנט את הנתונים הבאים:
- ממוצע שערים שהובקעו וספוגים ל-5 משחקים אחרונים
- xG (שערים צפויים) ל-5 משחקים אחרונים
- פצועים ונעדרים עכשוויים
- היסטוריית עימותים ישירים (H2H)
- הרכב משוער / רשמי

לאחר החיפוש, ענה בפורמט הזה בדיוק בעברית:

🏆 {team1} 🆚 {team2}
📅 {match_time}

1. [ממוצע שערים + xG של {team1}]
2. [ממוצע שערים + xG של {team2}]
3. [פצועים/נעדרים חשובים]
4. [היסטוריית עימותים - מי מנצח יותר]
5. [הגורם המכריע לתוצאה]

🎯 תחזית סופית: [X:Y]"""

    response = client.beta.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        tools=[WEB_SEARCH_TOOL],
        betas=["web-search-2025-03-05"],
    )

    result = ""
    for block in response.content:
        if hasattr(block, "text"):
            result += block.text

    return result or "לא ניתן היה לנתח את המשחק כרגע."


def get_todays_matches() -> list:
    """מחזיר רשימת משחקים של היום עם זמנים מדויקים"""
    from datetime import datetime
    today = datetime.now().strftime("%d/%m/%Y")

    prompt = f"""מה המשחקים של נבחרות לאום בתאריך {today}? כולל מונדיאל 2026, משחקי ידידות, ליגת האומות, וכל תחרות נבחרות.
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

    prompt = f"""חפש באינטרנט את כל משחקי הנבחרות היום ומחר - כולל מונדיאל 2026, משחקי ידידות, ליגת האומות וכל תחרות נבחרות:
{matches_text}

לכל משחק שתמצא, בצע ניתוח מקיף וספק תחזית תוצאה מדויקת.
הצג כל משחק בפורמט הנכון עם דגל הנבחרות ושעה בשעון ישראל.
אם אין משחקים ביום זה, ציין מתי המשחק הבא."""

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
