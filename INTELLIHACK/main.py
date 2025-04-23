import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

class AITrackerBot:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.perplexity.ai")
        self.conversation_log = []
        self.system_prompt = (
            "You are an AI assistant that answers questions by performing real-time web searches. "
            "Provide clear, concise answers with citations from trustworthy sources."
        )

    def ask(self, user_input):
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]
        try:
            response = self.client.chat.completions.create(
                model="sonar-pro",
                messages=messages,
                temperature=0.7
            )
            answer = response.choices[0].message.content
            self.log_interaction(user_input, answer)
            return answer
        except Exception as e:
            error_msg = f"Error communicating with Perplexity API: {e}"
            self.log_interaction(user_input, error_msg)
            return error_msg

    def log_interaction(self, query, response):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response
        }
        self.conversation_log.append(entry)
        self.save_log()

    def save_log(self):
        with open("perplexity_conversation_log.json", "w", encoding="utf-8") as f:
            json.dump(self.conversation_log, f, indent=2, ensure_ascii=False)

    def get_summary(self):
        summary = f"Conversation History ({len(self.conversation_log)} interactions):\n"
        for i, entry in enumerate(self.conversation_log, 1):
            q = entry['query']
            summary += f"{i}. {q[:75]}{'...' if len(q) > 75 else ''}\n"
        return summary

    def chat_interface(self):
        print("Perplexity AI Tracker Bot - type 'summary' to view history, 'exit' to quit.")
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() == "exit":
                print("Goodbye!")
                break
            elif user_input.lower() == "summary":
                print("\n" + self.get_summary())
                continue

            response = self.ask(user_input)
            print(f"\nAI: {response}")

if __name__ == "__main__":
    bot = AITrackerBot()
    bot.chat_interface()
    from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for local development

bot = AITrackerBot()

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message")
    if not user_message:
        return jsonify({"response": "No message provided"}), 400

    response = bot.ask(user_message)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
