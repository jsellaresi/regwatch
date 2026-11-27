def message_text(message) -> str:
    """Plain text of a chat model reply.

    `content` is a string for some models and a list of blocks (text, thinking, ...) for
    others, such as the current Claude models; only the text blocks count."""
    content = message.content
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)
