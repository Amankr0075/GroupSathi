from google import genai
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from django.http import JsonResponse
from core.db import get_collection
from core.ai_manager import AIManager
from bson.objectid import ObjectId
from datetime import datetime

SYSTEM_PROMPT = """You are GroupSathi AI Assistant.

You are the official support assistant for the GroupSathi platform.

Your responsibilities:
- Help users with anything related to GroupSathi.
- Explain features and guide users step-by-step.
- Answer questions about notifications, meetings, groups, profiles, and announcements.
- Provide personalized responses using authenticated user data.
- Be friendly, concise, and professional.
- Support English, Hindi, and Gujarati.
- If a user asks something unrelated to GroupSathi, politely inform them that you are specialized in assisting with the GroupSathi platform."""

@api_view(['GET'])
def get_jwt_token_view(request):
    """
    Endpoint for Flutter to exchange a session cookie for a JWT token.
    Checks if `user_id` exists in the session.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Not authenticated via session'}, status=401)
    
    # We must create a mock user object or directly generate token for simplejwt
    # SimpleJWT usually expects a Django User model instance. We can subclass Token to inject user_id manually.
    
    class CustomUser:
        def __init__(self, uid):
            self.id = uid
            self.pk = uid
    
    user = CustomUser(user_id)
    refresh = RefreshToken.for_user(user)
    
    return JsonResponse({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    })

def _get_user_context(user_id):
    """Fetch user's personalized context from MongoDB"""
    context = []
    
    # Profile
    profiles = get_collection('profiles')
    profile = profiles.find_one({'user_id': user_id})
    if profile:
        context.append(f"User Name: {profile.get('full_name', 'Unknown')}")
        context.append(f"Member ID: {profile.get('member_id', 'Unknown')}")
    
    # Notifications
    notifications = get_collection('notifications')
    unread_count = notifications.count_documents({'user_id': user_id, 'is_read': False})
    if unread_count > 0:
        context.append(f"Unread Notifications: {unread_count}")
        latest_notifs = list(notifications.find({'user_id': user_id, 'is_read': False}).sort('created_at', -1).limit(3))
        for n in latest_notifs:
            context.append(f"- {n.get('title')}: {n.get('message')}")
    else:
        context.append("Unread Notifications: 0")
        
    # Groups
    group_members = get_collection('group_members')
    user_groups = list(group_members.find({'user_id': user_id}))
    if user_groups:
        groups = get_collection('groups')
        group_names = []
        for g_member in user_groups:
            group = groups.find_one({'group_id': g_member['group_id']})
            if group:
                group_names.append(group.get('name', 'Unnamed Group'))
        context.append(f"Member of Groups: {', '.join(group_names)}")
    else:
        context.append("Member of Groups: None")
        
    return "\n".join(context)

class ChatbotAskView(APIView):
    permission_classes = [AllowAny] # We handle auth manually in post()

    def post(self, request):
        if not settings.GEMINI_API_KEY:
            return Response({'error': 'Gemini API not configured'}, status=500)
            
        user_message = request.data.get('message', '').strip()
        if not user_message:
            return Response({'error': 'Message is required'}, status=400)
            
        # Try to get user_id from session (Web) or from JWT (Mobile)
        user_id = request.session.get('user_id')
        if not user_id and request.user and request.user.is_authenticated:
            user_id = str(request.user.id)
            
        if not user_id:
            return Response({'error': 'Authentication required'}, status=401)
        
        # Build Context
        user_context = _get_user_context(user_id)
        
        chat_histories = get_collection('chat_histories')
        
        # Fetch last few messages for history context
        history_docs = list(chat_histories.find({'user_id': user_id}).sort('timestamp', 1).limit(10))
        history_context = []
        for doc in history_docs:
            if doc['sender'] == 'user':
                history_context.append(f"User: {doc['text']}")
            else:
                history_context.append(f"Bot: {doc['text']}")
        
        full_history = "\n".join(history_context)
        
        # Build Full Prompt
        full_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"--- User Context ---\n{user_context}\n\n"
            f"--- Conversation History ---\n{full_history}\n\n"
            f"User: {user_message}\nBot:"
        )

        try:
            bot_reply = AIManager.generate_response(user_id, full_prompt)
            
            # Save to DB
            chat_histories.insert_one({
                'user_id': user_id,
                'sender': 'user',
                'text': user_message,
                'timestamp': datetime.now()
            })
            
            chat_histories.insert_one({
                'user_id': user_id,
                'sender': 'bot',
                'text': bot_reply,
                'timestamp': datetime.now()
            })
            
            return Response({'reply': bot_reply})
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PublicChatbotAskView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_message = request.data.get('message')
        if not user_message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

        public_system_prompt = """You are the public GroupSathi AI Assistant. 
You answer general questions about the GroupSathi platform, its features, and its goals to help Self Help Groups. 
You are speaking to an unregistered visitor. You do NOT have access to any personal data, so do not attempt to provide personalized information. 
Keep your responses helpful, encouraging, and relatively concise. Encourage the user to register or login to unlock full capabilities."""

        # Fetch recent public chat history from request (optional, usually landing page bots are stateless or keep state in frontend)
        history = request.data.get('history', [])
        
        # Build prompt
        full_prompt = f"{public_system_prompt}\n\n"
        if history:
            full_prompt += "Recent Conversation:\n"
            for msg in history:
                role = "User" if msg['is_user'] else "GroupSathi AI"
                full_prompt += f"{role}: {msg['text']}\n"
            full_prompt += "\n"
        
        full_prompt += f"User: {user_message}\nGroupSathi AI:"

        try:
            bot_reply = AIManager.generate_response("public", full_prompt)
            
            return Response({
                'reply': bot_reply,
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatbotHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.id)
        chat_histories = get_collection('chat_histories')
        docs = list(chat_histories.find({'user_id': user_id}).sort('timestamp', 1))
        
        history = []
        for doc in docs:
            history.append({
                'sender': doc['sender'],
                'text': doc['text'],
                'timestamp': doc['timestamp'].isoformat()
            })
            
        return Response({'history': history})
