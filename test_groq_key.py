from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# response = client.chat.completions.create(
#     model="gpt-5.4-nano",  # fast + cheap
#     messages=[
#         {"role": "user", "content": "Say nice in one sentence"}
#     ],
# )

# with client.chat.completions.with_streaming_response.create(
#     messages=[
#         {
#             "role": "user",
#             "content": "Say this is a test",
#         }
#     ],
#     model="gpt-5.4-nano",  # fast + cheap
# ) as response:
#     print(response.headers.get("X-My-Header"))

# for line in response.iter_lines():
#         print(line)
# print(response.choices[0].message.content)
# print("\nTokens used:", response.usage)

