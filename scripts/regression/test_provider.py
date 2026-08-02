import time
from app.ai.providers.ollama import OllamaProvider
from app.config.settings import settings

def run_regression() -> dict:
    start_time = time.perf_counter()
    try:
        # Load host and model from app settings
        provider = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
        
        # Test is_available (safe, does not throw if connection fails)
        available = provider.is_available()
        
        # If available, try initialization sequence
        reason = ""
        if available:
            provider.initialize()
            reason = f"Ollama service is available and model '{settings.ollama_model}' initialized successfully."
        else:
            reason = f"Ollama service is currently unavailable at host '{settings.ollama_host}'. Provider test skipped (graceful recovery)."
            
        duration = time.perf_counter() - start_time
        return {
            "name": "test_provider.py",
            "status": "PASS" if available else "SKIP",
            "duration": duration,
            "reason": reason
        }
    except Exception as e:
        duration = time.perf_counter() - start_time
        return {
            "name": "test_provider.py",
            "status": "FAIL",
            "duration": duration,
            "reason": f"Provider test failed: {e}"
        }
