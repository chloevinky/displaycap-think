"""
Anthropic API client for analyzing screenshots and providing assistance.
"""

from typing import List, Optional
import anthropic


# Claude 4.5 Haiku model ID
MODEL_ID = "claude-haiku-4-5-20241022"

SYSTEM_PROMPT = """You are a quick, helpful AI assistant that analyzes screenshots of a user's computer screen to understand what they're working on and provide brief, actionable assistance.

Your role:
1. Quickly identify what task or activity the user is engaged in
2. Understand the context from multiple screenshots (showing progression)
3. Provide a SHORT, helpful response that assists with their current task

Guidelines:
- Keep responses concise (2-4 sentences max)
- Be specific to what you see on screen
- Offer actionable tips, shortcuts, or next steps
- If you see an error, explain it briefly and suggest a fix
- If you see code, provide relevant tips or spot issues
- If you see a document, help with formatting or content suggestions
- Be direct and practical - the user wants quick help, not lengthy explanations

Remember: The user pressed a hotkey for quick assistance, so be fast and useful."""


def create_client(api_key: str) -> anthropic.Anthropic:
    """Create an Anthropic API client."""
    return anthropic.Anthropic(api_key=api_key)


def analyze_screenshots(
    client: anthropic.Anthropic,
    screenshots_base64: List[str],
    user_context: Optional[str] = None
) -> str:
    """
    Send screenshots to Claude for analysis and get assistance.

    Args:
        client: Anthropic API client
        screenshots_base64: List of base64-encoded screenshot images
        user_context: Optional additional context from the user

    Returns:
        Claude's response with assistance
    """
    # Build the message content with images
    content = []

    # Add each screenshot as an image
    for i, img_base64 in enumerate(screenshots_base64):
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": img_base64,
            },
        })

    # Add the analysis request
    prompt_text = "Analyze these screenshots taken moments apart and provide quick, helpful assistance for what I'm working on."

    if user_context:
        prompt_text += f"\n\nAdditional context: {user_context}"

    content.append({
        "type": "text",
        "text": prompt_text
    })

    # Make the API call
    message = client.messages.create(
        model=MODEL_ID,
        max_tokens=300,  # Keep responses short
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )

    # Extract the text response
    response_text = ""
    for block in message.content:
        if block.type == "text":
            response_text += block.text

    return response_text.strip()
