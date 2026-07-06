"""Diagnostic script verifying conversation context policy bounding limits."""

from datetime import datetime, timezone, timedelta
from app.agent.messages import Message, MessageRole
from app.conversation.policy import ContextWindowPolicy


def run_bounds_diagnostic():
    print("==========================================================")
    print("RUNNING CONTEXT BOUNDING DIAGNOSTIC")
    print("==========================================================")

    # Configure limits: max 5 messages, max 55 characters
    policy = ContextWindowPolicy(max_messages=5, max_characters=55)

    now = datetime.now(timezone.utc)
    # Generate 10 messages of 12 characters each. Total characters = 120 (exceeds character budget)
    # Total count = 10 (exceeds count budget)
    messages = []
    for i in range(10):
        # We alternate roles: user, assistant
        role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
        messages.append(
            Message(
                id=f"msg_{i}",
                role=role,
                content=f"Msg content {i}",  # 12 characters
                timestamp=now + timedelta(seconds=i),
                metadata={}
            )
        )

    # Let's run selection
    selected = policy.select_history(messages)

    # Calculate statistics
    total_history_count = len(messages)
    selected_count = len(selected)

    total_history_chars = sum(len(m.content) for m in messages)
    selected_chars = sum(len(m.content) for m in selected)

    selected_ids = [m.id for m in selected]
    oldest_selected = selected[0].id if selected else None
    newest_selected = selected[-1].id if selected else None

    # Verification checks
    # 1. Bounding limits respected (selected count <= 5, selected chars <= 55)
    # Wait, the latest message is Msg 9 (13 chars). Adding Msg 8 makes 26 chars. Adding Msg 7 makes 39 chars.
    # Adding Msg 6 makes 52 chars. Adding Msg 5 would make 65 chars (> 55 limit).
    # So it should select: Msg 6, Msg 7, Msg 8, Msg 9 (4 messages, 52 characters).
    # 2. Chronological order preserved: MSG 6 -> MSG 7 -> MSG 8 -> MSG 9
    # 3. Latest message retained: MSG 9 is present
    # 4. Complete messages: no partial content truncation
    count_ok = selected_count <= 5
    chars_ok = selected_chars <= 55
    order_ok = selected_ids == ["msg_6", "msg_7", "msg_8", "msg_9"]
    latest_retained = "msg_9" in selected_ids

    passed = count_ok and chars_ok and order_ok and latest_retained

    print(f"Total history messages:       {total_history_count}")
    print(f"Selected context messages:    {selected_count}")
    print(f"Total history characters:     {total_history_chars}")
    print(f"Selected context characters:  {selected_chars}")
    print(f"Selected message IDs:         {selected_ids}")
    print(f"Oldest selected message:      {oldest_selected}")
    print(f"Newest selected message:      {newest_selected}")

    print("\n----------------------------------------------------------")
    print(f"Context Bounding Diagnostic:  {'PASS' if passed else 'FAIL'}")
    print("==========================================================")


if __name__ == "__main__":
    run_bounds_diagnostic()
