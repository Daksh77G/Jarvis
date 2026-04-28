import os
from groq import Groq

# --- Config ---
ASSISTANT_NAME = "Jarvis"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
conversation_history = []

def speak(text):
    print(f"\n{ASSISTANT_NAME}: {text}\n")

def ask_llm(user_input):
    conversation_history.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": f"You are {ASSISTANT_NAME}, a helpful desktop AI assistant. Be concise."},
            *conversation_history
        ]
    )
    reply = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": reply})
    return reply

if __name__ == "__main__":
    speak(f"Hello! I am {ASSISTANT_NAME}. Type your message below. Type 'exit' to quit.")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["exit", "goodbye", "quit"]:
            speak("Goodbye!")
            break
        reply = ask_llm(user_input)
        speak(reply)