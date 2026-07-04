"""Verification script to test native model-driven tool calling with Ollama."""

import sys
from app.core.application import Application
from app.agent.models import AgentRequest
from app.utils.id_generator import generate_request_id
from datetime import datetime, timezone


def main():
    """Bootstraps application and verifies tool execution loop with model."""
    print("Initializing Jarvis AI Assistant application abstractions...")
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
        app._initialize_agent()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        sys.exit(1)

    controller = app.container.get("controller")
    prompts = [
        "What is the current local time?",
        "Tell me basic information about this computer's operating system."
    ]

    for prompt in prompts:
        print("\n" + "=" * 60)
        print(f"User: {prompt}")
        print("=" * 60)
        
        request = AgentRequest(
            request_id=generate_request_id(),
            text=prompt,
            source="test_script",
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        
        try:
            response = controller.process_request(request)
            print(f"Jarvis: {response.text}")
        except Exception as e:
            print(f"Error processing request: {e}")


if __name__ == "__main__":
    main()
