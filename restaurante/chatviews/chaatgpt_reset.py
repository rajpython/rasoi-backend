from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(["POST"])
@permission_classes([AllowAny])
def reset_chat_context(request):
    """
    Clears the chat history and booking context for this user or session.
    """
    user = request.user
    session_id = request.session.session_key or request.session.create()

    chat_key = f"chat_history_user_{user.id}" if user and user.is_authenticated else f"chat_history_guest_{session_id}"
    booking_key = f"booking_context_user_{user.id}" if user and user.is_authenticated else f"booking_context_guest_{session_id}"

    cache.delete(chat_key)
    cache.delete(booking_key)

    return Response({"status": "ok", "message": "Chat history and booking context have been cleared."})
