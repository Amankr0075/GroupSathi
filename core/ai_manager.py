import time
import datetime
from django.conf import settings
from google import genai
import groq
from core.db import get_db

class GeminiProvider:
    def __init__(self, model_name: str = 'gemini-2.0-flash'):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return response.text

class GroqProvider:
    def __init__(self, model_name: str = 'llama-3.3-70b-versatile'):
        self.client = groq.Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

class AIManager:
    @staticmethod
    def _log_interaction(user_id: str, provider: str, status: str, response_time: float):
        db = get_db()
        try:
            db.ai_logs.insert_one({
                "user_id": user_id,
                "provider": provider,
                "status": status,
                "response_time": f"{response_time:.2f}s",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            })
        except Exception as e:
            print("Failed to log AI interaction:", e)

    @staticmethod
    def generate_response(user_id: str, full_prompt: str) -> str:
        providers = []
        if getattr(settings, 'GEMINI_API_KEY', None):
            providers.append(("gemini-2.0", GeminiProvider('gemini-2.0-flash')))
        if getattr(settings, 'GROQ_API_KEY', None):
            providers.append(("groq", GroqProvider('llama-3.3-70b-versatile')))
            
        if not providers:
            return "GroupSathi AI Assistant is currently unconfigured. Please contact support."
        
        # Fast retry to avoid UI latency
        delays = [0.5]

        for provider_name, provider in providers:
            # We have len(delays) retries, meaning len(delays) + 1 total attempts
            attempts = len(delays) + 1
            for attempt in range(attempts):
                start_time = time.time()
                try:
                    reply = provider.generate(full_prompt)
                    response_time = time.time() - start_time
                    AIManager._log_interaction(user_id, provider_name, "success", response_time)
                    return reply
                except Exception as e:
                    response_time = time.time() - start_time
                    AIManager._log_interaction(user_id, provider_name, f"failed_attempt_{attempt+1}", response_time)
                    print(f"[{provider_name}] Attempt {attempt+1} failed: {e}")
                    
                    if attempt < len(delays):
                        time.sleep(delays[attempt])
                    else:
                        break # Exhausted retries for this provider

        # If both fail completely
        AIManager._log_interaction(user_id, "all", "total_failure", 0)
        return "GroupSathi AI Assistant is temporarily unavailable. Please try again in a few moments."
