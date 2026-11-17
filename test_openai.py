from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

response = client.responses.create(
    model="gpt-5.5",
    input="Reply with: FlyWise API connection successful."
)

print(response.output_text)