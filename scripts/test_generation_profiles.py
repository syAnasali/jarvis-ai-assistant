"""Script to verify that GenerationProfile adaptation changes provider execution behaviour."""

import sys
import time
from app.core.application import Application
from app.ai.models import GenerationProfile


def main() -> int:
    """Executes verification tests for GenerationProfile settings."""
    print("=" * 60)
    print("Profile Verification Diagnostic")
    print("=" * 60)
    print("Initializing Jarvis AI Assistant application abstractions...")
    
    app = Application()
    try:
        app.initialize()
        app._initialize_llm()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return 1

    llm_manager = app.container.get("llm_manager")
    prompt = [{"role": "user", "content": "Respond with exactly: OK"}]

    profiles = [
        GenerationProfile.FAST,
        GenerationProfile.BALANCED,
        GenerationProfile.REASONING
    ]

    for profile in profiles:
        print("\n" + "-" * 60)
        print(f"Testing Profile: {profile.name}")
        print("-" * 60)
        
        start_time = time.perf_counter()
        try:
            gen_result = llm_manager.generate(prompt, profile=profile)
            total_duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract content from result
            from app.ai.parser import ResponseParser
            parser = ResponseParser()
            agent_response = parser.parse_response(gen_result)
            
            metrics = gen_result.metrics
            print(f"Profile:             {profile.name}")
            print(f"Final Visible:       {agent_response.text}")
            print(f"Total Provider Dur:  {metrics.total_duration_ms} ms")
            print(f"Generation Dur:      {metrics.generation_duration_ms} ms")
            print(f"Generated Tokens:    {metrics.generated_tokens}")
            print(f"Tokens Per Second:   {metrics.tokens_per_second}")
            print(f"Calculated Latency:  {total_duration_ms:.2f} ms")
        except Exception as e:
            print(f"Failed generation for profile {profile.name}: {e}")

    print("\n" + "=" * 60)
    print("Profile Verification Complete")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
