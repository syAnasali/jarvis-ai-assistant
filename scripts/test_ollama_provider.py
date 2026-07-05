"""Script to verify the OllamaProvider integration in an isolated environment."""

import sys
import json
from datetime import datetime, timezone
from app.config.settings import settings
from app.core.exceptions import LLMError, ConfigurationError
from app.ai.providers.ollama import OllamaProvider
from app.agent.messages import Message, MessageRole
from app.ai.formatter import MessageFormatter


def run_test() -> int:
    """Executes verification tests for the OllamaProvider.

    Returns:
        int: 0 if verification succeeded, 1 if any stage failed.
    """
    print("========================================")
    print("Jarvis AI Assistant")
    print("Ollama Provider Test")
    print("========================================")
    print()

    print("Configuration")
    print("-------------")
    print(f"Application Name:    {settings.app_name}")
    print(f"Application Version: {settings.app_version}")
    print(f"Configured Model:    {settings.ollama_model}")
    print(f"Configured Host:     {settings.ollama_host}")
    print()

    provider = None
    try:
        # 1. Initialization
        print("Initialization")
        print("--------------")
        provider = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
        provider.initialize()
        print("✓ Initialization succeeded.")
        print()

        # 2. Health Check
        print("Health Check")
        print("------------")
        health = provider.health_check()
        print("Health Check Info:")
        print(json.dumps(health, indent=2))
        print()

        # 3. Payload Construction
        print("Payload")
        print("-------")
        message = Message(
            id="test_msg_01",
            role=MessageRole.USER,
            content="Hello! Introduce yourself in one sentence.",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        
        formatter = MessageFormatter()
        formatted_messages = formatter.format_history([message])
        print(f"Formatted Payload: {formatted_messages}")
        print()

        # 4. Generation
        print("Generation")
        print("----------")
        print("Sending chat generation request...")
        gen_result = provider.generate(formatted_messages)
        raw_response = gen_result.raw_response
        print(f"Response Type: {type(raw_response)}")
        print(f"Load duration: {gen_result.metrics.load_duration_ms} ms")
        print(f"Prompt eval duration: {gen_result.metrics.prompt_eval_duration_ms} ms")
        print(f"Generation duration: {gen_result.metrics.generation_duration_ms} ms")
        print(f"Total duration: {gen_result.metrics.total_duration_ms} ms")
        print(f"Prompt tokens: {gen_result.metrics.prompt_tokens}")
        print(f"Generated tokens: {gen_result.metrics.generated_tokens}")
        print(f"Tokens per second: {gen_result.metrics.tokens_per_second}")
        print()

        # 5. Assistant Response Output
        print("Assistant Response")
        print("------------------")
        
        content = ""
        if isinstance(raw_response, dict):
            # Dict-like response structure
            msg = raw_response.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = getattr(msg, "content", "")
        else:
            # SDK-object response structure
            msg = getattr(raw_response, "message", None)
            if msg is not None:
                content = getattr(msg, "content", "")

        # Fallback if content was not resolved
        if not content:
            content = str(raw_response)

        print(content)
        print()

        # 6. Shutdown
        print("Shutdown")
        print("--------")
        provider.shutdown()
        # Verify idempotent shutdown
        provider.shutdown()
        print("✓ Idempotent shutdown succeeded.")
        print()
        
        print("========================================")
        print("Provider Test Complete")
        print("========================================")
        return 0

    except (LLMError, ConfigurationError) as e:
        print(f"\n❌ Configuration/LLM Error: {e}")
        if settings.log_level in ("DEBUG", "TRACE"):
            import traceback
            traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if settings.log_level in ("DEBUG", "TRACE"):
            import traceback
            traceback.print_exc()
        return 1
    finally:
        if provider is not None:
            try:
                provider.shutdown()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(run_test())
