from openai import OpenAI
from django.conf import settings
from typing import Optional, Tuple
from django.core.cache import cache

client = OpenAI(api_key=settings.OPENAI_API_KEY)

LANG_KEY_FMT = "lang_pref_{session_id}"  # values: "en" or "hn"



def get_detect_intent_prompt():
    return """
🎯 Classify the user's **explicit intent** or language switch request.

Return exactly one token:
- booking
- ordering
- none
- switch_to_en
- switch_to_h

Use the brief recent conversation (below) to disambiguate short replies like
“aap hi kar do”, “order shuru karo”, “please do it for me”, etc.

📦 Examples that mean ORDERING:
- "please order for me"
- "start the order"
- "order shuru karo"
- "4 aloo puri chahiye", "2 samosa dena"

📅 Examples that mean BOOKING:
- "book a table"
- "table book kar do"
- "kal 7 baje 4 logon ke liye table"

❓ Examples that mean NONE:
- "how does ordering work?"
- "can I reserve online?"
- "what is there in menu?"
- "what are your hours?"

Language: The user may write in English, Hindi, or Hinglish. Infer intent or language switch accordingly.
👥 LANGUAGE SWITCHING: User may switch language between English or Hindi/Hinglish as following exampls indicate:
- If user says "switch to Hindi", "let's talk in Hindi", "change to Hinglish", or similar, return `switch_to_h`
- If user says "switch to English", "please talk in English", "change to English", etc., return `switch_to_en`

Final Guidelines:
- If the user clearly wants to **order**  return `ordering` or `booking`.
- If the user clearly wants to **book**  return `booking`.
- If they're asking how the process works, return `none`.
- If they ask to **switch to English**, return `switch_to_en`.
- If they ask to **switch to Hinglish or Hindi**, return `switch_to_h`.

Return with one of these exact tokens: booking, ordering, none, switch_to_en, or switch_to_h. Do NOT invent or shorten tokens.
""".strip()


def detect_intent(user_message: str, session_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Returns (intent, language, prompt_to_send_now)

    - language: "en" (English) or "hn" (Hinglish) once chosen or switched
    - prompt_to_send_now:
        * If language not set → ask for it.
        * If user just chose or switched language → confirm and ask for next step.
        * Otherwise None (continue normal flow).
    """
    text = (user_message or "").strip().lower()
    lang_key = LANG_KEY_FMT.format(session_id=session_id)
    lang_pref = cache.get(lang_key)  # "en" | "hn" | None
    print(f"🧭 Current language preference: {lang_pref}")

    # --- Step 1: First-time language handshake (no LLM involved) ---
    if not lang_pref:

        if "english" in text:
            cache.set(lang_key, "en", timeout=60 * 60 * 24)
            return (None, "en", 
            "Great, English it is! 🇬🇧\n"
            "You can still switch to Hinglish later if you’d like. I’m flexible like that! 😄\n"
            "BUT — once we start booking your table or placing your food order, please don’t switch languages midway... my British agent gets confused in Hinglish and starts uttering filthy Bollywood dialogues! 🎭😂\n"
            "Now, how can I help today? Would you like to book a table, order food, browse the menu, or ask a general question?")
        
        if "hinglish" in text or "hindi" in text:
            cache.set(lang_key, "hn", timeout=60 * 60 * 24)
            return (None, "hn", 
            "Waah kya baat hai! Hinglish chosen, boss! 😎\n"
            "Agar mann badal jaaye toh aap baad mein English mein bhi baat kar sakte hain — main har rang mein taiyaar hoon! 🎨\n"
            "Lekin ek baat yaad rahe — jaise hi booking ya food order shuru ho jaaye, language mat badalna... English me hamare Hinglishiya agent ke paseene chhootne lagte hain aur woh bahtroom bhag jaata hai! ☕🤯\n"
            "Toh boliye, kya seva karoon: table book karoon, khana mangwa doon, menu dikhaoon, ya koi general sawaal?")

        # Ask the preference first
        return (None, None, 
        "Let's first decide if you want me to talk in English or Hinglish? 🤔\n"
        "And then we can chat about our menu 🍽️, order food 😋, book a table 📅, or anything else you need help with!")

    # --- Step 2: Language is known → run LLM for intent or switch detection ---
    system_message = {"role": "system", "content": get_detect_intent_prompt()}
    user_input = {"role": "user", "content": (user_message or "").strip()}

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[system_message, user_input],
            temperature=0,
            max_tokens=3,
        )
        raw = resp.choices[0].message.content or ""
        reply = raw.splitlines()[0].strip().strip('"').lower()
        print(f"🎯 detect_intent raw reply: {reply}")

        # --- Step 2a: Handle language switch requests ---
        if reply == "switch_to_en" and lang_pref != "en":
            cache.set(lang_key, "en", timeout=60 * 60 * 24)
            return (None, "en", "✅ Switched to English! Now what?")
        if reply == "switch_to_h" and lang_pref != "hn":
            cache.set(lang_key, "hn", timeout=60 * 60 * 24)
            return (None, "hn", "✅ Hinglish mein baat shuru karte hain! Farmaiye Janaab!")

        # --- Step 2b: Handle actual intent detection ---
        if reply in {"booking", "ordering"}:
            return (reply, lang_pref, None)

        # --- Step 2c: No clear intent ---
        return (None, lang_pref, None)

    except Exception as e:
        print(f"❌ detect_intent failed: {e}")
        return (None, lang_pref, None)
