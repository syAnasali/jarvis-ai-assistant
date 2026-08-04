"""StreamingHandler updating real-time StreamingBubble tokens."""

from typing import Optional
from app.gui.chat.message import MessageListWidget, StreamingBubble


class StreamingHandler:
    """Manages creation and token updating for active StreamingBubble instances."""

    def __init__(self, message_list: MessageListWidget) -> None:
        self.message_list = message_list
        self.active_bubble: Optional[StreamingBubble] = None

    def start_streaming(self) -> StreamingBubble:
        """Instantiates a new StreamingBubble in the message list."""
        bubble = StreamingBubble(parent=self.message_list.container)
        self.message_list.add_widget(bubble)
        self.active_bubble = bubble
        return bubble

    def on_token(self, token: str) -> None:
        """Appends streaming token to active bubble."""
        if self.active_bubble:
            self.active_bubble.append_token(token)
            self.message_list.scroll_to_bottom()

    def finish_streaming(self) -> str:
        """Finalizes active streaming bubble and returns accumulated text."""
        text = ""
        if self.active_bubble:
            text = self.active_bubble.get_text()
            self.active_bubble.deleteLater()
            self.active_bubble = None
        return text
