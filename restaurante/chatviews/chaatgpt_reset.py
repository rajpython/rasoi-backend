from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_chat_context(request):
    """
    Clears chat/order/booking/lang/mode context for the normalized session_id.
    Keys cleared:
      - chat_history_{session_id}
      - booking_context_{session_id}
      - order_context_{session_id}
      - lang_pref_{session_id}
      - current_mode_{session_id}
    """
    user = request.user
    guest_id = request.headers.get("X-Guest-Id")

    # Recreate the same normalized session_id you use everywhere else
    if user.is_authenticated:
        session_id = f"user_{user.id}"
    elif guest_id:
        session_id = f"guest_{guest_id}"
    else:
        if not request.session.session_key:
            request.session.create()
        session_id = f"session_{request.session.session_key}"

    keys = [
        f"chat_history_{session_id}",
        f"booking_context_{session_id}",
        f"order_context_{session_id}",
        f"lang_pref_{session_id}",
        f"chat_mode_{session_id}",
    ]
    cache.delete_many(keys)

    

    return Response({"status": "ok", "message": "Chat and contexts cleared."})

