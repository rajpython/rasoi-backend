# order_logic.py
import json
import inspect
from django.conf import settings
from django.core.cache import cache
from django.http import StreamingHttpResponse
from restaurante.utils import (
    save_chat_turn, 
    save_to_db_conversation, 
    set_order_context, 
    resolve_date_keyword)

from restaurante.models import Order
from .agent_tools import ORDER_TOOL_FUNCTION_MAP
from .agent_tools.order_functions import get_order_context

iframe_url_example = "__IFRAME_URL__:https://frontend.com/order-confirmation__"


def handle_order_logic(response, user, session_id, order_context, order_prompt, history_messages, client, message):
    
    try:
        
        choice = response.choices[0]
        assistant_reply = getattr(choice.message, "content", "")
        tool_calls = getattr(choice.message, "tool_calls", []) or []

        # ✅ Persist assistant message that requested tools
        assistant_with_tools = {"role": "assistant", "content": assistant_reply or ""}
        history_messages.append(assistant_with_tools)
        save_chat_turn(user, session_id, "assistant", assistant_reply or "")
        save_to_db_conversation(user, session_id, "assistant", assistant_reply or "")

        
        print(f"\n=== 📝 GPT REPLY (text) ===\n{assistant_reply}")
        print(f"\n=== 🛠 TOOL CALLS === {tool_calls}")

        for tool_call in tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            # 🔍 If is_confirmed is missing or False in context, check DB just in case
            if not order_context.get("is_confirmed"):
                cached_order_id = order_context.get("order_id")
                if cached_order_id:
                    try:
                        db_order = Order.objects.get(id=cached_order_id)
                        if db_order.is_confirmed:
                            print(f"⚠️ Fallback: Order #{cached_order_id} confirmed in DB. Updating cache.")
                            order_context["is_confirmed"] = True
                            set_order_context(session_id, order_context)
                    except Order.DoesNotExist:
                        pass

            # if func_name not in ("get_order_context", "start_order") and order_context.get("is_confirmed"):
            if func_name != "start_order" and order_context.get("is_confirmed"):
             
                warning = f"⚠️ Order #{order_context.get('order_id')} is already confirmed. Further changes are not allowed."
                print(warning)
                save_chat_turn(user, session_id, "assistant", warning)
                save_to_db_conversation(user, session_id, "assistant", warning)
                return StreamingHttpResponse(iter([warning]), content_type="text/plain")

            # Handle stale or duplicate start_order calls
            if func_name == "start_order" and order_context.get("order_id"):
                existing_id = order_context["order_id"]
                try:
                    existing_order = Order.objects.get(id=existing_id)
                    if existing_order.is_confirmed:
                        print(f"⚠️ Existing order #{existing_id} confirmed. Starting fresh.")
                        order_context.clear()
                    else:
                        print(f"⚠️ Order already started: {existing_id}")
                        continue
                except Order.DoesNotExist:
                    print(f"⚠️ Stale order_id in cache. Clearing.")
                    order_context.clear()

            # Always override GPT's order_id with the cached one
            if func_name != "start_order":
                cached_order_id = order_context.get("order_id")
                if cached_order_id:
                    args["order_id"] = cached_order_id
                    print(f"🧠 Injected order_id: {cached_order_id}")
                else:
                    print(f"⚠️ No order_id found in context for {func_name}")


            # Normalize delivery_date
            if "delivery_date" in args:
                original = args["delivery_date"]
                resolved = resolve_date_keyword(original)
                if resolved != original:
                    print(f"📅 Resolved date: '{original}' ➡️ '{resolved}'")
                args["delivery_date"] = resolved

            # Get the tool function
            func = ORDER_TOOL_FUNCTION_MAP.get(func_name)
            if not func:
                print(f"❌ Tool function not found: {func_name}")
                continue

            # Execute the function
            try:
                if "user" in inspect.signature(func).parameters:
                    result = func(user=user, **args)
                else:
                    result = func(**args)
            except Exception as e:
                print(f"❌ Exception calling {func_name}: {e}")
                return StreamingHttpResponse(iter([f"⚠️ Error occurred: {str(e)}"]), content_type='text/plain')

            # Handle context updates
            if isinstance(result, dict):
                # Set order_id after start_order
                if func_name == "start_order" and "order_id" in result:
                    order_context["order_id"] = result["order_id"]
                    print(f"💾 Stored order_id: {result['order_id']}")

                expected_keys = {
                    "start_order": ["order_id"],
                    "add_order_item": ["items"],
                    "revise_order_item": ["items"],   
                    "available_delivery_slots_today": [],  # just lists; no state change
                    "set_delivery_date": ["delivery_date"],
                    "set_delivery_time_slot": ["delivery_time_slot"],
                    "set_delivery_type": ["delivery_type"],
                    "set_delivery_details": ["delivery_address", "delivery_city", "delivery_pin"],
                    "set_payment_method": ["payment_method"],
                    "checkout_order": [
                        "delivery_type","delivery_address","delivery_city","delivery_pin",
                        "delivery_date","delivery_time_slot","payment_method","items"
                    ],
                }.get(func_name, [])

                # After expected_keys update, add:
                if func_name == "set_delivery_date":
                    # Clear any previously selected time slot so the model must ask again
                    if order_context.get("delivery_time_slot"):
                        order_context["delivery_time_slot"] = None
                        print("🧼 Cleared stale delivery_time_slot due to date change.")

                for key in expected_keys:
                    if key in result:
                        val = resolve_date_keyword(result[key]) if key == "delivery_date" else result[key]
                        order_context[key] = val
                        print(f"✅ Context updated: {key} = {val}")

                # Inject confirmation link
                if func_name == "checkout_order" and "order_id" in result:
                    frontend_url = settings.FRONTEND_URL.rstrip("/")
                    iframe_url = f"__IFRAME_URL__:{frontend_url}/bot-orders?order_id={result['order_id']}__"
                    if result.get("payment_method", "").lower() == "cod":
                        result["message"] += f"\n\nHere is your checkout form:\n{iframe_url}"
                    else:
                        result["message"] += f"Here is your checkout form:\n{iframe_url}\n\nOnce payment is successful, you’ll get a confirmation email! 📧"

                    try:
                        updated_context = get_order_context(result["order_id"])
                        order_context["is_confirmed"] = updated_context.get("is_confirmed", False)
                    except Exception as e:
                        print(f"⚠️ Failed to update is_confirmed from get_order_context: {e}")
                        order_context["is_confirmed"] = False  # fallback

                # cache.set(order_key, order_context)
                set_order_context(session_id, order_context)

                print(f"🧠 Updated order_context: {order_context}")

                # Save and stream
                # Save function result into history
                function_message = {"role": "function", "name": func_name, "content": json.dumps(result)}
                history_messages.append(function_message)
                save_chat_turn(user, session_id, "function", json.dumps(result), name=func_name)
                save_to_db_conversation(user, session_id, "function", f"{func_name}: {result}")

                # 🚨 Short-circuit if checkout_order — stream iframe message directly
                if func_name == "checkout_order":
                    # 🧹 Clear chat mode — flow complete
                    cache.delete(f"chat_mode_{session_id}")
                    print(f"🧹 Cleared mode after confirmed order.")
                    return StreamingHttpResponse(iter([result["message"]]), content_type="text/plain")


                # Re-run GPT with updated history
                system_message = [{"role": "system", "content": order_prompt}
        ]
                messages_with_result = system_message + history_messages  # system prompt
                

                # Run GPT again to summarize the function result
                followup = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages_with_result,
                    tools=[],  # ✅ Add this
                    tool_choice="none"  # ✅ Allowed only if tools is explicitly []
                )
                followup_reply = followup.choices[0].message.content or "🤖 Summary not available!"

                save_chat_turn(user, session_id, "assistant", followup_reply)
                save_to_db_conversation(user, session_id, "assistant", followup_reply)

                return StreamingHttpResponse(iter([followup_reply]), content_type='text/plain')


        # Normal conversation
        save_chat_turn(user, session_id, "user", message)

        # Fix missing assistant reply
        if assistant_reply is None:
            assistant_reply = "🤖 Sorry, kuch samajh nahi aaya! Can you repeat?"

        save_chat_turn(user, session_id, "assistant", assistant_reply)
        save_to_db_conversation(user, session_id, "user", message)
        save_to_db_conversation(user, session_id, "assistant", assistant_reply)

        return StreamingHttpResponse(iter([assistant_reply]), content_type='text/plain')

    except Exception as e:
        print(f"❌ Exception: {e}")
        return StreamingHttpResponse(iter([f"⚠️ Error occurred: {str(e)}"]), content_type='text/plain')


