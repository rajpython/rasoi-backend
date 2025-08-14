from openai import OpenAI
from django.conf import settings
from typing import Optional

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def get_detect_intent_prompt():
    return """
🎯 Classify the user's **explicit intent**.

Return exactly one token:
- booking
- ordering
- none

Use the brief recent conversation (below) to disambiguate short replies like
“aap hi kar do”, “order shuru karo”, “please do it for me”, etc.
If the current topic is clearly ordering or booking, classify accordingly.
If ambiguous or purely informational, i.e., just asking asking how to order or book, return none.
Treat IMPERATIVE commands as explicit intent, even if the user doesn't say "do it for me".

Examples that mean ORDERING:
- "please order for me"
- "start the order"
- "order shuru karo"
- "mere liye order kar do"
- "aap hi kar do"  (when context is about ordering)
- "4 aloo puri chahiye", "2 samosa dena" (items/quantities imply ordering)

Examples that mean BOOKING:
- "book a table", "reserve a table"
- "table book kar do", "kal 7 baje 4 logon ke liye table"

Examples that mean NONE (just info):
- "how does ordering work?"
- "can I reserve online?"
- "what is there in menu/specials/categories?"
- "what are your hours?"

Language: The user may write in English, Hindi, or Hinglish. Infer intent accordingly.

Answer with exactly one token: booking, ordering, or none.
""".strip()


def detect_intent(user_message: str) -> Optional[str]:
    """
    Determines whether the user is explicitly asking the bot to 'book' a table or 'order' food.
    Returns 'booking', 'ordering', or None (when the model answers 'none' or anything else).
    """
    system_message = {"role": "system", "content": get_detect_intent_prompt()}
    user_input = {"role": "user", "content": (user_message or "").strip()}

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[system_message, user_input],
            temperature=0,
            max_tokens=3,  # keep it to a single token
        )
        raw = resp.choices[0].message.content or ""
        reply = raw.splitlines()[0].strip().strip('"').lower()

        if reply in {"booking", "ordering"}:
            return reply
        # treat anything else (including "none") as None so your caller's else branch runs
        return None
    except Exception as e:
        print(f"❌ detect_intent failed: {e}")
        return None
