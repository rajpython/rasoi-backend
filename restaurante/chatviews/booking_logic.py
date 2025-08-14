# booking_logic.py
import json
from django.core.cache import cache
from django.http import StreamingHttpResponse
from restaurante.utils import save_chat_turn, save_to_db_conversation
from .agent_tools import TOOL_FUNCTION_MAP


def handle_booking_logic(response, user, session_id, booking_context, history_messages, message):
    booking_key = f"booking_context_{session_id}"  # reconstructed here
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

        get_available_times = TOOL_FUNCTION_MAP.get("get_available_booking_times")


        for tool_call in tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments) or {}
            print(f"⚙️ Handling function call: {func_name} with args: {args}")

            func = TOOL_FUNCTION_MAP.get(func_name)

            if func_name == "get_available_booking_times":
                # user changed date, so update date and reset time
                result = func(**args)
                booking_context["selected_date"] = args.get("selected_date")
                booking_context["available_slots"] = result.get("available_slots")
                booking_context["selected_time"] = None  # clear old time because new date needs new time
                booking_context["slots_fetched"] = True
                cache.set(booking_key, booking_context, timeout=600)
                print(f"✅ UPDATED CONTEXT AFTER NEW DATE: {booking_context}")

                # safe to call function

            elif func_name == "validate_booking_time":
                
                # Step 1: Extract selected_time and selected_date from function call
                new_date = args.get("selected_date")
                new_time = args.get("selected_time")

                # Step 2: Check if a new date is provided
                if new_date and new_date != booking_context.get("selected_date"):
                    print(f"📅 Detected NEW DATE in validate_booking_time: {new_date}")
                    
                    # Forcefully re-fetch available slots for new date
                    updated_slots = get_available_times(new_date)
                    booking_context["selected_date"] = new_date
                    booking_context["available_slots"] = updated_slots.get("available_slots", [])
                    booking_context["selected_time"] = None  # Clear selected_time
                    booking_context["slots_fetched"] = True

                    cache.set(booking_key, booking_context, timeout=600)
                    print(f"✅ CONTEXT UPDATED due to implicit date change: {booking_context}")

                    # Don't proceed with validation now. Let LLM handle next step with fresh slots.
                    return  # ⛔ Important: Stop here to avoid using wrong validation
                
                result = func(**args)
                    
                # Step 3: Only if no new date, proceed with validation result
                if isinstance(result, dict) and result.get("valid"):
                    booking_context["selected_time"] = new_time
                    cache.set(booking_key, booking_context, timeout=600)
                    print(f"✅ UPDATED CONTEXT AFTER TIME VALIDATION: {booking_context}")

            elif func_name == "create_booking":
                # Merge args with context before calling the function
                args["selected_date"] = args.get("selected_date") or booking_context.get("selected_date")
                args["selected_time"] = args.get("selected_time") or booking_context.get("selected_time")
                args["no_of_guests"] = args.get("no_of_guests") or booking_context.get("no_of_guests")
                args["occasion"] = args.get("occasion") or booking_context.get("occasion")
                args["email"] = args.get("email") or booking_context.get("email")


                print(f"🚀 FINAL CONTEXT FOR CREATE_BOOKING: {args}")

                result = func(**args, user=user)

                cache.delete(booking_key)
                print(f"✅ CONTEXT CLEARED AFTER BOOKING")
                # 🧹 Clear mode too
                cache.delete(f"chat_mode_{session_id}")
                print(f"🧹 Cleared mode after successful booking.")
            
            elif func_name == "cancel_booking":
                # Inject session_id (schema need not expose it)
                result = func(cancel=args.get("cancel", False), session_id=session_id)

                # (Optional) also clear local variables if you cache them elsewhere
                # booking_context = {...}  # not required; the tool already clears cache

                # Record the tool result as usual (history_messages append below)

            else:
                # All other tools
                result = func(**args)

                #################

                # Persist fields from setter tools into booking_context
                if isinstance(result, dict):
                    expected_keys = {
                        "set_no_of_guests": ["no_of_guests"],
                        "set_occasion": ["occasion"],
                        "set_email": ["email"],
                        # keep these here for completeness; they don't update context directly:
                        "cancel_booking": [],
                        "get_available_booking_times": [],
                        "validate_booking_time": [],
                        "create_booking": [],
                    }.get(func_name, [])

                    for key in expected_keys:
                        if key in result:
                            booking_context[key] = result[key]
                            print(f"✅ Context updated: {key} = {result[key]}")

                    # Save context if anything changed
                    if expected_keys:
                        cache.set(booking_key, booking_context, timeout=600)
                        print(f"💾 CONTEXT SAVED ({func_name}): {booking_context}")

                ##############

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

        print(f"✅ CONTEXT after assistant turn saved: {booking_context}")
        return StreamingHttpResponse(iter([assistant_reply]), content_type='text/plain')

    except Exception as e:
        print(f"❌ Exception: {e}")
        return StreamingHttpResponse(iter([f"⚠️ Error occurred: {str(e)}"]), content_type='text/plain')

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    