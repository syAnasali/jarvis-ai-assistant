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
