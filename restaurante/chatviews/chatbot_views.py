
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from openai import OpenAI
import json
from django.conf import settings
from .prompt_context import (build_menu_context, 
                             get_base_prompt_context, 
                             get_dynamic_booking_context, 
                             get_dynamic_order_context)
from .detect_intent import detect_intent
from .agent_tools import (AGENTIC_TOOLS, 
                                     ORDER_AGENTIC_TOOLS)
from django.core.cache import cache
from restaurante.utils import (
    get_user_context, 
    get_chat_history, 
    save_chat_turn, 
    save_to_db_conversation)
from .booking_logic import handle_booking_logic
from .order_logic import handle_order_logic


client = OpenAI(api_key=settings.OPENAI_API_KEY)

@csrf_exempt
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

    # 💡 Check if user is already in a mode (booking or ordering)
    mode_key = f"chat_mode_{session_id}"
    current_mode = cache.get(mode_key, None)
    print(f"🧭 Current chat mode: {current_mode}")


    # history and user context
    user_context = get_user_context(user)
    menu_context = build_menu_context()
    system_prompt = get_base_prompt_context(user_context, menu_context)
    history_messages = get_chat_history(user, session_id)
    

    if current_mode == "booking":
        print("🔁 Continuing existing booking flow")
        booking_context = cache.get(f"booking_context_{session_id}", {})
        dynamic_booking_prompt = get_dynamic_booking_context(booking_context)
        booking_prompt = system_prompt + "\n\n" + dynamic_booking_prompt
        messages = [
            {"role": "system", "content": booking_prompt}
        ] + history_messages + [
            {"role": "user", "content": message}
        ]
        response=client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools= AGENTIC_TOOLS,
            tool_choice="auto"
        )
        return handle_booking_logic(
            response,
            user=user,
            session_id=session_id,
            booking_context=booking_context,
            history_messages=history_messages,
            message=message
        )
        
    elif current_mode == "ordering":
        # 🚧 Re-gate: if user is not authenticated, exit ordering mode immediately
        if not user.is_authenticated:
            block_msg = (
                "Online ordering ke liye login zaroori hai. "
                "Pehle login kijiye aur 'done' likhiye. "
                "Chahein to 'book table' keh kar reservation kar sakte hain, ya general baat cheet bhi kar sakte hain."
            )
            cache.delete(mode_key)  # reset current_mode to None

            # Nudge the model & keep logs consistent
            history_messages.append({
                "role": "function",
                "name": "login_required",
                "content": json.dumps({"requires_login": True, "message": block_msg})
            })
            save_chat_turn(user, session_id, "function", block_msg, name="login_required")
            save_to_db_conversation(user, session_id, "function", f"login_required: {block_msg}")

            return StreamingHttpResponse(iter([block_msg]), content_type="text/plain")
        #############
        print("🔁 Continuing existing ordering flow")
        order_context = cache.get(f"order_context_{session_id}", {})
        dynamic_order_prompt = get_dynamic_order_context(order_context)
        auth_status = "LOGGED_IN" if (user and user.is_authenticated) else "GUEST"

        login_fact = f"""🔒 AUTH STATUS: {auth_status}
        - Treat this as ground truth. If AUTH STATUS == LOGGED_IN: never ask the user to log in.
        - If AUTH STATUS == LOGGED_IN AND CURRENT ORDER CONTEXT has no `order_id`, call `start_order()` immediately.
        - If AUTH STATUS == GUEST: ask them to log in and do not call tools until they confirm login.
        """

        order_prompt = system_prompt + "\n\n" + login_fact + "\n\n" + dynamic_order_prompt
        # order_prompt = system_prompt + "\n\n" + dynamic_order_prompt
        messages = [
            {"role": "system", "content": order_prompt}
        ] + history_messages + [
            {"role": "user", "content": message}
        ]
        response=client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools = ORDER_AGENTIC_TOOLS,
            tool_choice="auto"
        )
        return handle_order_logic(
            response=response,
            user=user,
            session_id=session_id,
            order_context=order_context,
            order_prompt = order_prompt,
            history_messages=history_messages,
            client=client,
            message=message
        )


    # 🧭 Detect intent (booking or ordering)
    intent = detect_intent(message)
    if intent == "booking":
        cache.set(mode_key, "booking", timeout=600)
        print("🔍 Intent detected: Booking")
        booking_key = f"booking_context_{session_id}"
        booking_context = cache.get(booking_key, {
        "selected_date": None,
        "available_slots": None,
        "selected_time": None,
        "no_of_guests": None,
        "occasion": None,
        "email": getattr(user, "email", None),
        "slots_fetched": False
        })
        print(f"🚀 LOADED CONTEXT FOR {booking_key}: {booking_context}")
        dynamic_booking_prompt = get_dynamic_booking_context(booking_context)
        booking_prompt = system_prompt + "\n\n" + dynamic_booking_prompt

        messages = [
            {"role": "system", "content": booking_prompt}
        ] + history_messages + [
            {"role": "user", "content": message}
        ]
        
        response=client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools= AGENTIC_TOOLS,
            tool_choice="auto"
        )

        return handle_booking_logic(
            response,
            user=user,
            session_id=session_id,
            booking_context=booking_context,
            history_messages=history_messages,
            message=message
        )

    elif intent == "ordering":
        ######
        # 🚧 Auth gate: do not enter ordering mode unless logged in
        if not user.is_authenticated:
            block_msg = (
                "Online ordering ke liye login zaroori hai. "
                "Pehle login kijiye aur 'done' likhiye. "
                "Aap 'book table' keh kar reservation bhi kar sakte hain, ya general baat cheet kar sakte hain."
            )
            # Ensure we are NOT stuck in ordering mode
            cache.delete(mode_key)  # defensive reset

            history_messages.append({
                "role": "function",
                "name": "login_required",
                "content": json.dumps({"requires_login": True, "message": block_msg})
            })
            save_chat_turn(user, session_id, "function", block_msg, name="login_required")
            save_to_db_conversation(user, session_id, "function", f"login_required: {block_msg}")

            return StreamingHttpResponse(iter([block_msg]), content_type="text/plain")
         ##########
         # (leave the rest of your existing ordering code unchanged)

        # ✅ Authenticated → proceed exactly as you already do
        cache.set(mode_key, "ordering", timeout=600)
        print("🔍 Intent detected: Ordering")
        order_key = f"order_context_{session_id}"
        order_context = cache.get(order_key, {
        "order_id": None,
        "items": [],
        "delivery_date": None,
        "delivery_time_slot": None,
        "delivery_type": None,
        "delivery_address": None,
        "delivery_city": None,
        "delivery_pin": None,
        "payment_method": None, 
        "is_confirmed": False
        })
        # ✅ Diagnostic: Cache Check
        raw_value = cache.get(order_key)
        if raw_value is None:
            print(f"❌ Cache missing for key: {order_key}")
        else:
            print(f"✅ Cache hit for key: {order_key}")
            print(f"🧠 Existing order_context from cache: {raw_value}")

        dynamic_order_prompt = get_dynamic_order_context(order_context)
        auth_status = "LOGGED_IN" if (user and user.is_authenticated) else "GUEST"

        login_fact = f"""🔒 AUTH STATUS: {auth_status}
        - Treat this as ground truth. If AUTH STATUS == LOGGED_IN: never ask the user to log in.
        - If AUTH STATUS == LOGGED_IN AND CURRENT ORDER CONTEXT has no `order_id`, call `start_order()` immediately.
        - If AUTH STATUS == GUEST: ask them to log in and do not call tools until they confirm login.
        """

        order_prompt = system_prompt + "\n\n" + login_fact + "\n\n" + dynamic_order_prompt

        # order_prompt = system_prompt + "\n\n" + dynamic_order_prompt

        messages = [
            {"role": "system", "content": order_prompt}
        ] + history_messages + [
            {"role": "user", "content": message}
        ]

        response=client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools = ORDER_AGENTIC_TOOLS,
            tool_choice="auto"
        )
        return handle_order_logic(
            response=response,
            user=user,
            session_id=session_id,
            order_context=order_context,
            order_prompt=order_prompt,
            history_messages=history_messages,
            client=client,
            message=message
        )
    
    else:
            print("🤷 Unclear intent — continuing chat normally.")

            messages = [
                {"role": "system", "content": system_prompt}
            ] + history_messages + [
                {"role": "user", "content": message}
            ]

            # Regular GPT chat (no tools)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=[],  # No function call for now
                tool_choice="none"
            )
            reply = response.choices[0].message.content or "🤖 Sorry, kuch samajh nahi aaya! Can you repeat?"

            # 💾 Save
            save_chat_turn(user, session_id, "user", message)
            save_chat_turn(user, session_id, "assistant", reply)
            save_to_db_conversation(user, session_id, "user", message)
            save_to_db_conversation(user, session_id, "assistant", reply)

            return StreamingHttpResponse(iter([reply]), content_type='text/plain')
    