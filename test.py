from groq import Groq

client = Groq(
    api_key="SENING_GSK_KEYING"
)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "user", "content": "Salom"}
    ]
)

print(response.choices[0].message.content)