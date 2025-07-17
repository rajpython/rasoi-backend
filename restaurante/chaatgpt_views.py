from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from django.conf import settings
from openai import OpenAI
from restaurante.models import Category, MenuItem, Order, Booking, TIME_SLOTS, DELIVERY_TIME_SLOTS
from restaurante.agent_tools import AGENTIC_TOOLS, TOOL_FUNCTION_MAP
from restaurante.utils import get_user_context, get_chat_history, save_chat_turn, save_to_db_conversation
import json
import inspect

client = OpenAI(api_key=settings.OPENAI_API_KEY)

@api_view(["POST"])
@permission_classes([AllowAny])
def chaatgpt_view(request):
    user = request.user
    message = request.data.get("message", "").strip()
    guest_id = request.headers.get("X-Guest-Id")
    if user.is_authenticated:
        session_id = f"user_{user.id}"
    elif guest_id:
        session_id = f"guest_{guest_id}"
    else:
        if not request.session.session_key:
            request.session.create()
        session_id = f"session_{request.session.session_key}"

    print(f"🚀 Using session_id: {session_id}")

    booking_key = f"booking_context_{session_id}"

    # history and user context
    history_messages = get_chat_history(user, session_id)
    user_context = get_user_context(user)

    # prepare static restaurant context
    categories = Category.objects.all()
    category_str = ", ".join([c.title for c in categories]) or "No categories."
    menu_items = MenuItem.objects.all()
    menu_context = "\n".join([f"{item.title} (${item.price}) - {item.description or 'No description'}" for item in menu_items]) or "No menu data."
    specials = MenuItem.objects.filter(featured=True)
    specials_context = "\n".join([f"{item.title} (${item.price}) - {item.description or 'No description'}" for item in specials]) or "No specials."
    booking_slots = ", ".join([slot[0] for slot in TIME_SLOTS])
    delivery_slots = ", ".join([slot[0] for slot in DELIVERY_TIME_SLOTS])
    delivery_types = ", ".join([c[0] for c in Order._meta.get_field('delivery_type').choices])
    payment_methods = ", ".join([c[0] for c in Order._meta.get_field('payment_method').choices])

    MENU_STATIC_CONTEXT = f"""
🍽️ OUR MENU CATEGORIES:
{category_str}

🌟 FEATURED SPECIALS:
{specials_context}

📜 FULL MENU ITEMS:
{menu_context}

⌚ RESERVATION TIME SLOTS:
{booking_slots}
🚚 DELIVERY TIME SLOTS:
{delivery_slots}

✅ PAYMENT OPTIONS: Stripe or COD. Pickup & Delivery available!
"""
    context = cache.get(booking_key, {
        "selected_date": None,
        "selected_time": None,
        "no_of_guests": None,
        "occasion": None,
        "email": getattr(user, "email", None),
        "slots_fetched": False
    })
    print(f"🚀 LOADED CONTEXT FOR {booking_key}: {context}")

    context_str = f"""
    CURRENT BOOKING CONTEXT:
    - Selected date: {context.get("selected_date") or 'not yet'}
    - Selected time: {context.get("selected_time") or 'not yet'}
    - Guests: {context.get("no_of_guests") or 'not yet'}
    - Occasion: {context.get("occasion") or 'not yet'}
    - Email: {context.get("email") or 'not yet'}
    - Slots fetched? {context.get("slots_fetched")}
    """
  
    dynamic_booking_context = f"""
    {context_str}

    ✅ HOW TO HANDLE BOOKINGS — STRICT RULES:

    1️⃣ **Always confirm the reservation date explicitly.**
    - If the user says something like '20' or '20 ka', politely ask if this means the 20th of this month (July) or another month.
    - Never assume. Always get a clear confirmation like "20th July, or 20th August?" before proceeding.
    - If user does not specify a year, ALWAYS assume it means the **next upcoming occurrence in the future**. 
    - For example, if today is 15th July 2025 and user says "22nd July", it means 22nd July 2025. 
    - Never suggest or talk about a past year like 2023. Always move forward in time.

    2️⃣ Once the date is confirmed, **IMMEDIATELY call `get_available_booking_times` for that date.**
    - Do NOT try to guess availability. Always call the function to get real slots.
    - Present slots in friendly Hinglish like: 
    "✅ 27th July, 2025 ke liye available slots hain: 11am, 11:30am, ..., 2:30pm. Kya aap ek time batayenge jo aapko theek lage?"

    3️⃣ When the user gives you a time like "8 baje ka" or "7 baje" or "6", interpret in pm by default, and always call `validate_booking_time` to confirm.
    - Check the result of the validation:
        - If `valid = true`, confirm it cheerfully with Hinglish & emoji, then proceed to ask for number of guests.
        - If `valid = false`, say: "Arey sorry yaar 😅, woh time available nahi hai. Koi aur time try karo?" and wait for another time.

    4️⃣ After the time is confirmed, ask for **number of guests**.

    5️⃣ Then ask about the **occasion** (Birthday, Anniversary, Other) in your usual light playful style.

    6️⃣ Finally, if email is not already available, ask for the **email address**.
    - Once all data is collected (date, time, guests, occasion, email), **call `create_booking` to finalize.**
    - Then tell the user: 
    "✅ Booking confirm ho gayi 🎉! Enjoy karna, aur koi sawaal ho toh pucho."

    ✅ HANDLING CORRECTIONS
    - If at any point the user changes or corrects earlier info (like date or time), always adjust the booking context and smoothly go back and restart from that step.
    - For example:
        - If they change the date, **immediately call `get_available_booking_times` for the new date**.
        - If they change the time, **immediately call `validate_booking_time` again for the new time**.

    ✅ VERY IMPORTANT: 
    - Never hesitate or reason by yourself about whether slots might be open or not. 
    - For ANY date the user mentions (even casually), **always immediately call `get_available_booking_times` for that date.**
    - Similarly, for ANY time slot the user picks for the last confirmed date, **always immediately call `validate_booking_time`.**
    - Never hold back function calls. Always trust the functions to give you the truth.

    ✅ HANDLING STYLE
    - Always keep it short, playful, with a local Eastern UP Benarasi-Awadhi Hinglish vibe, sprinkled with ~25% emoji.
    - Only greet by name and ask about weather the **first time in the session**. After that, continue normal friendly Hinglish.

    ✅ DO NOT repeat already confirmed info unnecessarily. 
    - If something changes, only reconfirm the changed part and smoothly continue.

    ✅ FINAL REMINDER:
    - Never suggest or talk about a past year like 2023. Always move forward in time.
    - Always call `get_available_booking_times` or `validate_booking_time` instead of reasoning yourself.
    """
    messages = [
        {
            "role": "system",
            "content": f"""
    You are चाटGPT, a witty Indian street food assistant.
    Your style is Eastern UP Benarasi-Awadhi Hinglish with light street food jokes (approx 25% frequency), 
    but always serious and specific when user asks about booking, ordering, delivery, or payments.

    ✅ Rules for personalization:
    - ONLY greet the user by name and optionally ask about the weather in their city the **first time in the session**. 
    Do not repeat this greeting or weather question again in the same chat.
    - After that, use normal friendly Hinglish without repeatedly using the user's name.
    - Keep responses short, conversational, and lightly sprinkled with emojis.

✅ Responsibilities:
- Chat about menu, bookings, delivery, specials.
- Guide step by step for booking: confirm date ➡️ time ➡️ guests ➡️ occasion ➡️ finalize.
- When ready, call functions.

{dynamic_booking_context}

USER CONTEXT:
{user_context}

MENU:
{MENU_STATIC_CONTEXT}
"""
        }
    ] + history_messages + [{"role": "user", "content": message}]

    print("\n=== 📨 Sending GPT-4 prompt ===")
    print(json.dumps(messages[-3:], indent=2)[:700] + "...\n")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=AGENTIC_TOOLS,
            tool_choice="auto"
        )
        choice = response.choices[0]
        assistant_reply = getattr(choice.message, "content", "")
        tool_calls = getattr(choice.message, "tool_calls", []) or []

        print(f"\n=== 📝 GPT REPLY (text) ===\n{assistant_reply}")
        print(f"\n=== 🛠 TOOL CALLS === {tool_calls}")


        for tool_call in tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments) or {}
            print(f"⚙️ Handling function call: {func_name} with args: {args}")

            func = TOOL_FUNCTION_MAP.get(func_name)
            if func:
                result = func(**args)

                # --- context updates with smart resets ---
                if func_name == "get_available_booking_times":
                    # user changed date, so update date and reset time
                    context["selected_date"] = args.get("reservation_date")
                    context["selected_time"] = None  # clear old time because new date needs new time
                    context["slots_fetched"] = True
                    cache.set(booking_key, context, timeout=600)
                    print(f"✅ UPDATED CONTEXT AFTER NEW DATE: {context}")

                elif func_name == "validate_booking_time":
                    # if result.get("valid"):
                    if isinstance(result, dict) and result.get("valid"):
                        context["selected_time"] = args.get("chosen_time")
                        cache.set(booking_key, context, timeout=600)
                        print(f"✅ UPDATED CONTEXT AFTER TIME VALIDATION: {context}")

                elif func_name == "create_booking":
                    # Always merge context to ensure latest user flow
                    final_date = args.get("reservation_date", context.get("selected_date"))
                    final_time = args.get("reservation_time", context.get("selected_time"))
                    final_guests = args.get("no_of_guests", context.get("no_of_guests"))
                    final_occasion = args.get("occasion", context.get("occasion"))
                    final_email = args.get("email", context.get("email"))

                    print(f"🚀 FINAL CONTEXT FOR CREATE_BOOKING: date={final_date}, time={final_time}, guests={final_guests}, occasion={final_occasion}, email={final_email}")
                    
                    result = func(
                        reservation_date=final_date,
                        reservation_time=final_time,
                        no_of_guests=final_guests,
                        occasion=final_occasion,
                        email=final_email,
                        user=user
                    )
                    cache.delete(booking_key)
                    print(f"✅ CONTEXT CLEARED AFTER BOOKING")

                # --- reply to GPT ---

            history_messages.append({
                "role": "function",
                "name": func_name,
                "content": json.dumps(result)
            })

            save_chat_turn(user, session_id, role="function", message=f"{result}", name=func_name)
            save_to_db_conversation(user, session_id, role="function", message=f"{func_name}: {result}")
            # return StreamingHttpResponse(iter([str(result)]), content_type='text/plain')
            if isinstance(result, dict) and "message" in result:
                return StreamingHttpResponse(iter([result["message"]]), content_type='text/plain')
            else:
                return StreamingHttpResponse(iter([str(result)]), content_type='text/plain')


        # normal conversation branch
        save_chat_turn(user, session_id, "user", message)
        save_chat_turn(user, session_id, "assistant", assistant_reply)
        save_to_db_conversation(user, session_id, "user", message)
        save_to_db_conversation(user, session_id, "assistant", assistant_reply)

        print(f"✅ CONTEXT after assistant turn saved: {context}")
        return StreamingHttpResponse(iter([assistant_reply]), content_type='text/plain')

    except Exception as e:
        print(f"❌ Exception: {e}")
        return StreamingHttpResponse(iter([f"⚠️ Error occurred: {str(e)}"]), content_type='text/plain')
