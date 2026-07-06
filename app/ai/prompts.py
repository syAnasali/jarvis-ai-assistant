"""Manages standard system and user prompt templates."""

TOOL_USE_POLICY_MARKER = "POLICY FOR USING TRUSTED TOOLS"


class PromptManager:
    """Stores and serves default prompt templates for LLM instruction contexts."""

    def system_prompt(self) -> str:
        """Returns the main assistant behavior system prompt.

        Returns:
            str: System instruction template.
        """
        return "You are Jarvis, a helpful desktop AI assistant."

    def developer_prompt(self) -> str:
        """Returns instructions for developer tasks.

        Returns:
            str: Developer helper template.
        """
        return "Provide clear, well-structured, and compliant code outputs."

    def tool_prompt(self) -> str:
        """Returns instructions on how to use tools.

        Returns:
            str: Tool calling guidance template.
        """
        return "Utilize available tools when requested to retrieve accurate data."

    def safety_prompt(self) -> str:
        """Returns constraints and behavioral safety instructions.

        Returns:
            str: Safety constraint instruction template.
        """
        return "Ensure all user inputs are handled safely and respect user privacy."

    def tool_use_policy(self) -> str:
        """Returns the policy guiding the model on when and how to call tools.

        Returns:
            str: Tool use policy instructions.
        """
        return (
            f"{TOOL_USE_POLICY_MARKER}:\n"
            "- Available tools provide trusted external, runtime, environment, or system state.\n"
            "- When answering requires current factual state that cannot be reliably known "
            "from conversation context, use an available tool capable of retrieving that state.\n"
            "- Prefer trusted tool output over assumptions.\n"
            "- Never fabricate current external, runtime, environment, or machine state.\n"
            "- Do not call tools for general knowledge that can be answered reliably without "
            "current external state.\n"
            "- After a successful tool result, ground the answer in that result.\n"
            "- Do not contradict successful tool output."
        )

    def memory_extraction_prompt(self) -> str:
        """Returns the system instructions for extracting durable memories from user input.

        Returns:
            str: System instruction prompt template.
        """
        return (
            "You are a precise information extraction system. Analyze the provided USER MESSAGE "
            "and extract any genuinely durable user facts, preferences, projects, or context that should "
            "be remembered for future conversations.\n\n"
            "ELIGIBILITY CRITERIA:\n"
            "- Facts: Stable personal details explicitly stated (e.g. name, location, occupation).\n"
            "- Preferences: Explicit user choices or style habits (e.g. 'I prefer Python', 'Answer concisely').\n"
            "- Projects: Long-lived ongoing goals or tasks (e.g. 'I am building a local assistant').\n"
            "- Context: Durable context that will matter in future sessions.\n\n"
            "DO NOT EXTRACT:\n"
            "- Conversational noise, greetings, or thanks (e.g. 'Hello', 'Thanks').\n"
            "- Generic questions, coding requests, or search queries (e.g. 'Explain photosynthesis', 'Write a function').\n"
            "- Transient request-specific comments (e.g. 'I am typing right now').\n"
            "- Secrets, passwords, API keys, private keys, bearer tokens, or government/financial IDs.\n\n"
            "OUTPUT FORMAT:\n"
            "You must return ONLY a raw JSON object with a single 'memories' key containing a list of extracted memories. "
            "Do not wrap in markdown block formatting (no ```json). Do not add explanations or conversational filler. "
            "If no durable information is found, return {\"memories\": []}.\n\n"
            "JSON SCHEMA:\n"
            "{\n"
            "  \"memories\": [\n"
            "    {\n"
            "      \"content\": \"The user's name is Anas.\", (Represent the user in third person: 'The user prefers...', 'The user is...')\n"
            "      \"memory_type\": \"FACT\" | \"PREFERENCE\" | \"PROJECT\" | \"CONTEXT\",\n"
            "      \"importance\": 0.0 to 1.0 (proposed priority rating),\n"
            "      \"confidence\": 0.0 to 1.0 (how sure you are of this fact)\n"
            "    }\n"
            "  ]\n"
            "}"
        )
