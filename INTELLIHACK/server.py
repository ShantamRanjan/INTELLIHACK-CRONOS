import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# AI Logic
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


# Flask API
app = Flask(__name__)
CORS(app)
bot = AITrackerBot()

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get("message")
    if not message:
        return jsonify({"error": "No message provided"}), 400

    response = bot.ask(message)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True)