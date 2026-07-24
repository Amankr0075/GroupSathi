from google import genai
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
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
- Help users with anything related to GroupSathi features (groups, loans, notifications, meetings).
- Provide personalized responses using authenticated user data.
- Be friendly, conversational, concise, and professional.
- Support English, Hindi, and Gujarati.

STRICT RULE: You MUST ONLY answer questions related to the GroupSathi platform, Self Help Groups, micro-loans, and app usage. 
If the user asks ANY question about general knowledge, science, history, coding, or any other unrelated topic (e.g., photosynthesis), you MUST refuse to answer it. Simply reply with: "I am only programmed to assist with the GroupSathi platform. I cannot answer questions about outside topics." Do NOT provide the answer to their off-topic question under any circumstances."""

@api_view(['POST'])
@throttle_classes([UserRateThrottle])
def ai_summarize_view(request):
    """Summarize text using AI, mainly for broadcast titles/summaries."""
    text = request.data.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'No text provided'}, status=400)
    
    try:
        from core.ai_manager import AIManager
        prompt = f"Please provide a very short, concise, and catchy title (max 6 words) for the following broadcast message:\n\n{text}"
        response_text = AIManager.generate_response("system_summarizer", prompt)
        return JsonResponse({'summary': response_text.strip().strip('"')})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def post(self, request):
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
        
        # Fetch custom admin instructions
        chatbot_config = get_collection('chatbot_config')
        config = chatbot_config.find_one({'_id': 'config'})
        custom_instructions = config.get('instructions', '') if config else ''
        
        system_prompt_final = SYSTEM_PROMPT
        if custom_instructions:
            system_prompt_final += f"\n\n--- Admin Custom Instructions ---\n{custom_instructions}"

        # Build Full Prompt
        full_prompt = (
            f"{system_prompt_final}\n\n"
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
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        user_message = request.data.get('message')
        if not user_message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

        public_system_prompt = """You are the public GroupSathi AI Assistant. 
You answer questions ONLY about the GroupSathi platform, Self Help Groups (SHGs), finance, and community building.
You are speaking to an unregistered visitor. You do NOT have access to any personal data, so do not attempt to provide personalized information. 

STRICT RULE: You MUST NOT answer general knowledge questions, science questions, or anything outside the scope of GroupSathi. If asked about an unrelated topic, reply exactly with: "I am only programmed to assist with the GroupSathi platform. I cannot answer questions about outside topics." Do NOT answer their unrelated question."""

        # Fetch recent public chat history from request (optional, usually landing page bots are stateless or keep state in frontend)
        history = request.data.get('history', [])
        
        # Fetch custom admin instructions
        chatbot_config = get_collection('chatbot_config')
        config = chatbot_config.find_one({'_id': 'config'})
        custom_instructions = config.get('instructions', '') if config else ''
        
        system_prompt_final = public_system_prompt
        if custom_instructions:
            system_prompt_final += f"\n\n--- Admin Custom Instructions ---\n{custom_instructions}"

        # Build prompt
        full_prompt = f"{system_prompt_final}\n\n"
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

@api_view(['POST'])
@throttle_classes([UserRateThrottle])
def ai_generate_message_view(request):
    """Generate a professional broadcast message based on a scenario."""
    scenario = request.data.get('scenario', '').strip()
    if not scenario:
        return JsonResponse({'error': 'No scenario provided'}, status=400)
    
    try:
        from core.ai_manager import AIManager
        prompt = f"Please write a professional, clear, and engaging broadcast message based on this scenario: {scenario}. Make it suitable for a push notification or announcement in the GroupSathi app."
        response_text = AIManager.generate_response("system_message_generator", prompt)
        return JsonResponse({'message': response_text.strip()})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@throttle_classes([UserRateThrottle])
def ai_generate_image_view(request):
    """Generate an image using an external API and overlay the GroupSathi logo."""
    title = request.data.get('title', '').strip()
    message = request.data.get('message', '').strip()
    
    if not title and not message:
        return JsonResponse({'error': 'Title or message required for image generation'}, status=400)
        
    prompt = f"A professional, high-quality, abstract or symbolic image representing: {title}. {message[:100]}"
    
    try:
        import requests
        import os
        import uuid
        from io import BytesIO
        from PIL import Image
        from django.conf import settings
        import urllib.parse
        
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=400&nologo=True&seed={uuid.uuid4().int % 100000}"
        
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content)).convert('RGBA')
        
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'GroupSathi.png')
        if os.path.exists(logo_path):
            from PIL import ImageDraw, ImageFont
            logo = Image.open(logo_path).convert('RGBA')
            base_width = 80  # smaller logo
            wpercent = (base_width / float(logo.size[0]))
            hsize = int((float(logo.size[1]) * float(wpercent)))
            logo = logo.resize((base_width, hsize), Image.LANCZOS)
            
            padding = 20
            
            # Draw text
            draw = ImageDraw.Draw(img)
            text = "GroupSathi"
            # Try to get a font
            try:
                # use a basic truetype font if available on windows
                font = ImageFont.truetype("arialbd.ttf", 36)
            except IOError:
                font = ImageFont.load_default()
            
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            total_width = base_width + 10 + text_width
            max_height = max(hsize, text_height)
            
            # Position at bottom right
            x_pos = img.size[0] - total_width - padding
            y_pos = img.size[1] - max_height - padding
            
            # Draw a subtle background for text readability
            bg_bbox = [x_pos - 10, y_pos - 10, x_pos + total_width + 10, y_pos + max_height + 10]
            draw.rounded_rectangle(bg_bbox, radius=10, fill=(0, 0, 0, 160))
            
            # Paste Logo
            img.paste(logo, (x_pos, y_pos), logo)
            
            # Draw Text
            text_y = y_pos + (hsize - text_height) // 2
            draw.text((x_pos + base_width + 10, text_y), text, font=font, fill=(255, 255, 255, 255))
            
        final_img = img.convert('RGB')
        filename = f"{uuid.uuid4().hex}.jpg"
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'broadcasts')
        os.makedirs(upload_dir, exist_ok=True)
        final_path = os.path.join(upload_dir, filename)
        
        final_img.save(final_path, 'JPEG', quality=85)
        image_db_path = f"broadcasts/{filename}"
        image_url = f"{settings.MEDIA_URL}{image_db_path}"
        
        return JsonResponse({'image_url': image_url, 'image_path': image_db_path})
        
    except Exception as e:
        print(f"Error generating image: {e}")
        return JsonResponse({'error': str(e)}, status=500)
