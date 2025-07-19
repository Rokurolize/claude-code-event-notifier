import anthropic

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="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",
)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=20000,
    temperature=1,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "2+2="
                }
            ]
        }
    ]
)
print(message.content)
