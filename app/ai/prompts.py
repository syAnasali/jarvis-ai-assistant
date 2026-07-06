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
            "STRICT EXTRACTION POLICY:\n"
            "1. A requested technology in a task instruction is NOT a preference. (e.g., 'Fix my Python code' or 'Write a Python function' does NOT infer 'The user prefers Python').\n"
            "2. A requested format or one-turn instruction is NOT a durable preference. (e.g., 'Generate a concise summary' does NOT infer a general preference for conciseness).\n"
            "3. A current task or temporary instruction is NOT automatically a long-term project.\n"
            "4. A question topic or search query is NOT a user fact. (e.g., 'Explain Docker' does NOT infer the user is learning Docker).\n"
            "5. An entity mentioned in a task is NOT associated with or owned by the user unless explicitly stated. (e.g., 'Create a website for Sire Media' does NOT infer the user owns Sire Media).\n"
            "6. Only extract a PREFERENCE when preference, liking, habitual choice, default choice, or durable working style is explicitly stated.\n"
            "7. Only extract a PROJECT when the user explicitly identifies the project as something they are building, developing, working on, maintaining, planning, or pursuing.\n"
            "8. Only extract educational context when the user explicitly identifies themselves as studying, learning, preparing for a long-lived course or program, or being enrolled in something.\n"
            "9. Do not infer durable memory from imperative task requests or conversational noise.\n\n"
            "DO NOT EXTRACT:\n"
            "- Conversational noise, greetings, or thanks (e.g. 'Hello', 'Thanks').\n"
            "- Secrets, passwords, API keys, private keys, bearer tokens, or government/financial IDs.\n\n"
            "OUTPUT FORMAT:\n"
            "You must return ONLY a raw JSON object with a single 'memories' key containing a list of extracted memories. "
            "Do not wrap in markdown block formatting (no ```json). Do not add explanations, reasoning, chain-of-thought, or conversational filler. "
            "If no durable information is found, return {\"memories\": []}.\n\n"
            "EVIDENCE RULE:\n"
            "For each candidate, you MUST provide the 'evidence' field. The evidence MUST contain a short exact supporting fragment copied verbatim from the user message that explicitly supports the claim. Do not paraphrase or fabricate the evidence.\n\n"
            "JSON SCHEMA:\n"
            "{\n"
            "  \"memories\": [\n"
            "    {\n"
            "      \"content\": \"The user prefers Python for personal projects.\", (Represent the user in third person: 'The user prefers...', 'The user is...')\n"
            "      \"memory_type\": \"FACT\" | \"PREFERENCE\" | \"PROJECT\" | \"CONTEXT\",\n"
            "      \"importance\": 0.0 to 1.0,\n"
            "      \"confidence\": 0.0 to 1.0,\n"
            "      \"evidence\": \"I prefer Python for personal projects.\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )
