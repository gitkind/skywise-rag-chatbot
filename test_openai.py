import config
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model=config.LLM_MODEL,
    input="Reply with: FlyWise API connection successful."
)

print(response.output_text)