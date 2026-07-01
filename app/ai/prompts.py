"""Manages standard system and user prompt templates."""


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
