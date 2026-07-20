import os
os.environ["LLM_API_KEY"] = ""

from app.config import settings
print(f"LLM_API_KEY from settings: '{settings.LLM_API_KEY}'")

from app.services.ai_service import AIService, AIServiceNotConfigured

service = AIService()
print(f"Service api_key: '{service.api_key}'")

try:
    service.chat("test", "test")
except AIServiceNotConfigured as e:
    print(f"AIServiceNotConfigured raised: {e}")
except Exception as e:
    print(f"Other exception: {type(e).__name__}: {e}")
