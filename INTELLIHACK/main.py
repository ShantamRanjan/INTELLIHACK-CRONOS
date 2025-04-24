import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import uuid
import time
import glob
import email
import imaplib
import re
from email.header import decode_header

class AITaskTrackerBot:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.perplexity.ai")
        self.conversation_log = []
        self.tasks = {}
        
        # Create task_data directory if it doesn't exist
        os.makedirs("task_data", exist_ok=True)
        
        # Load tasks from task_data folder
        self.load_tasks_from_folder()
        self.load_conversation_log()
        
        # Enhanced system prompt to handle task tracking
        self.system_prompt = (
            "You are an AI assistant that answers questions by performing real-time web searches "
            "and helps manage tasks. When asked about a task, you will provide updates on its progress. "
            "You retrieve task data from email and JSON files in the task_data folder. "
            "Provide clear, concise answers with helpful details about task progress when available."
        )

    def load_conversation_log(self):
        """Load conversation logs from file"""
        try:
            if os.path.exists("perplexity_conversation_log.json"):
                with open("perplexity_conversation_log.json", "r", encoding="utf-8") as f:
                    self.conversation_log = json.load(f)
        except Exception as e:
            print(f"Error loading conversation log: {e}")
            self.conversation_log = []

    def load_tasks_from_folder(self):
        """Load all task JSON files from the task_data folder"""
        self.tasks = {}
        task_files = glob.glob("task_data/*.json")
        
        for file_path in task_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    task_data = json.load(f)
                    # Extract task ID from filename (task_123abc.json -> 123abc)
                    filename = os.path.basename(file_path)
                    task_id = filename.replace("task_", "").replace(".json", "")
                    
                    # If the task data has its own ID field, use that instead
                    if "id" in task_data:
                        task_id = task_data["id"]
                        
                    self.tasks[task_id] = task_data
                    print(f"Loaded task {task_id} from {file_path}")
            except Exception as e:
                print(f"Error loading task from {file_path}: {e}")

    def save_task(self, task_id):
        """Save a specific task to its JSON file"""
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        filename = f"task_data/task_{task_id}.json"
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(task, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving task {task_id}: {e}")
            return False

    def fetch_tasks_from_email(self):
        """Fetch tasks from email and save them to task_data folder"""
        # Load email configuration from .env
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASS")
        email_server = os.getenv("EMAIL_SERVER", "imap.gmail.com")
        
        if not email_user or not email_password:
            return "Email configuration not set. Please set EMAIL_USER and EMAIL_PASSWORD in .env file."
            
        try:
            # Connect to the email server
            mail = imaplib.IMAP4_SSL(email_server)
            mail.login(email_user, email_password)
            mail.select("inbox")
            
            # Search for emails with "task" in subject
            status, messages = mail.search(None, 'SUBJECT "task"')
            if status != "OK":
                return "Failed to search for emails"
                
            email_ids = messages[0].split()
            if not email_ids:
                return "No task emails found"
                
            tasks_found = 0
            
            # Process each email
            for e_id in email_ids:
                status, msg_data = mail.fetch(e_id, "(RFC822)")
                if status != "OK":
                    continue
                    
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                
                # Extract subject and sender
                subject = decode_header(email_message["subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                    
                sender = decode_header(email_message["from"])[0][0]
                if isinstance(sender, bytes):
                    sender = sender.decode()
                
                # Extract email body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = email_message.get_payload(decode=True).decode()
                
                # Parse task details from email
                task_description = subject.replace("task:", "").replace("Task:", "").strip()
                
                # Extract deadline if present in the email body
                deadline_match = re.search(r"deadline:?\s*(\d{4}-\d{2}-\d{2})", body, re.IGNORECASE)
                deadline = deadline_match.group(1) if deadline_match else None
                
                # Extract priority if present
                priority_match = re.search(r"priority:?\s*(high|medium|low)", body, re.IGNORECASE)
                priority = priority_match.group(1).lower() if priority_match else "medium"
                
                # Create task from email
                task_id = str(uuid.uuid4())[:8]
                now = datetime.now().isoformat()
                
                task = {
                    "id": task_id,
                    "description": task_description,
                    "status": "pending",
                    "progress": 0,
                    "created_at": now,
                    "updated_at": now,
                    "deadline": deadline,
                    "priority": priority,
                    "source": "email",
                    "sender": sender,
                    "email_id": e_id.decode(),
                    "notes": [{"text": f"Task created from email: {subject}", "timestamp": now}]
                }
                
                # Save task to file and memory
                self.tasks[task_id] = task
                self.save_task(task_id)
                tasks_found += 1
                
                # Mark email as read
                mail.store(e_id, '+FLAGS', '\\Seen')
            
            mail.close()
            mail.logout()
            
            return f"Successfully imported {tasks_found} tasks from email"
            
        except Exception as e:
            return f"Error fetching tasks from email: {e}"
    
    def update_task(self, task_id, status=None, progress=None, note=None):
        """Update task status, progress, or add notes"""
        if task_id not in self.tasks:
            return f"Task {task_id} not found"
            
        task = self.tasks[task_id]
        now = datetime.now().isoformat()
        task["updated_at"] = now
        
        if status:
            task["status"] = status
        if progress is not None:
            task["progress"] = progress
        if note:
            task["notes"].append({"text": note, "timestamp": now})
            
        self.save_task(task_id)
        return f"Task {task_id} updated successfully"
        
    def get_task_progress(self, task_id):
        """Get detailed progress information about a task"""
        if task_id not in self.tasks:
            return f"Task {task_id} not found"
            
        task = self.tasks[task_id]
        
        # Format dates for display
        created = datetime.fromisoformat(task["created_at"]).strftime("%Y-%m-%d %H:%M")
        updated = datetime.fromisoformat(task["updated_at"]).strftime("%Y-%m-%d %H:%M")
        
        # Prepare deadline information
        deadline_info = ""
        if task.get("deadline"):
            try:
                deadline = datetime.fromisoformat(task["deadline"])
                now = datetime.now()
                if deadline > now:
                    days_left = (deadline - now).days
                    deadline_info = f"\nDeadline: {deadline.strftime('%Y-%m-%d')} ({days_left} days remaining)"
                else:
                    deadline_info = f"\nDeadline: {deadline.strftime('%Y-%m-%d')} (OVERDUE)"
            except (ValueError, TypeError):
                deadline_info = f"\nDeadline: {task['deadline']}"
                
        # Format notes
        notes = ""
        if task.get("notes"):
            recent_notes = task["notes"][-3:]  # Show last 3 notes
            notes = "\nRecent notes:\n" + "\n".join([f"- {n['text']}" for n in recent_notes])
            
        # Add source information if available
        source_info = ""
        if task.get("source") == "email":
            source_info = f"\nSource: Email from {task.get('sender', 'unknown')}"
            
        # Format priorities with emoji
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        priority = task.get("priority", "medium")
        priority_display = f"{priority_emoji.get(priority, '⚪')} {priority.title()}"
            
        return (
            f"Task ID: {task_id}\n"
            f"Description: {task['description']}\n"
            f"Status: {task['status'].replace('_', ' ').title()}\n"
            f"Progress: {task['progress']}%\n"
            f"Priority: {priority_display}\n"
            f"Created: {created}\n"
            f"Last updated: {updated}"
            f"{deadline_info}"
            f"{source_info}"
            f"{notes}"
        )
    
    def list_tasks(self, status_filter=None, priority_filter=None):
        """List all tasks, optionally filtered by status or priority"""
        if not self.tasks:
            return "No tasks found"
            
        filtered_tasks = self.tasks.copy()
        
        # Apply filters
        if status_filter:
            filtered_tasks = {k: v for k, v in filtered_tasks.items() if v["status"] == status_filter}
        if priority_filter:
            filtered_tasks = {k: v for k, v in filtered_tasks.items() if v.get("priority") == priority_filter}
            
        if not filtered_tasks:
            filters = []
            if status_filter:
                filters.append(f"status '{status_filter}'")
            if priority_filter:
                filters.append(f"priority '{priority_filter}'")
            filter_desc = " and ".join(filters)
            return f"No tasks with {filter_desc} found"
            
        # Priority emoji for display
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        
        # Sort tasks by priority (high first) then by deadline
        sorted_tasks = sorted(
            filtered_tasks.items(),
            key=lambda x: (
                {"high": 0, "medium": 1, "low": 2}.get(x[1].get("priority", "medium"), 3),
                x[1].get("deadline", "9999-12-31")  # Default to far future for sorting
            )
        )
        
        result = "Tasks:\n"
        for task_id, task in sorted_tasks:
            priority = task.get("priority", "medium")
            p_emoji = priority_emoji.get(priority, "⚪")
            deadline = f" (Due: {task['deadline']})" if task.get("deadline") else ""
            
            result += f"- [{task_id}] {p_emoji} {task['status']} ({task['progress']}%): {task['description'][:50]}{deadline}\n"
        
        return result

    def parse_task_commands(self, user_input):
        """Parse task-related commands from user input"""
        input_lower = user_input.lower()
        
        # Fetch tasks from email
        if "fetch tasks from email" in input_lower or "check email for tasks" in input_lower:
            result = self.fetch_tasks_from_email()
            return result
            
        # Update task command
        elif input_lower.startswith("update task:"):
            parts = user_input.split(":", 2)
            if len(parts) < 3:
                return "Invalid update format. Use 'update task: TASK_ID: your update details'"
            task_id = parts[1].strip()
            update_info = parts[2].strip()
            
            # Parse the update info
            status = None
            progress = None
            note = update_info
            
            if "status:" in update_info.lower():
                for status_type in ["pending", "in_progress", "completed"]:
                    if status_type in update_info.lower():
                        status = status_type
                        break
                        
            if "progress:" in update_info.lower():
                try:
                    progress_text = update_info.lower().split("progress:")[1].split("%")[0].strip()
                    progress = int(progress_text)
                except (ValueError, IndexError):
                    pass
                    
            self.update_task(task_id, status, progress, note)
            return f"Task updated:\n{self.get_task_progress(task_id)}"
            
        # Task progress command
        elif input_lower.startswith("task progress:") or input_lower.startswith("progress:"):
            task_id = user_input.split(":", 1)[1].strip()
            return self.get_task_progress(task_id)
            
        # List tasks command
        elif input_lower == "list tasks" or input_lower == "show tasks":
            return self.list_tasks()
        elif input_lower.startswith("list") and "tasks" in input_lower:
            status_filter = None
            priority_filter = None
            
            if "pending" in input_lower:
                status_filter = "pending"
            elif "progress" in input_lower or "ongoing" in input_lower:
                status_filter = "in_progress"
            elif "complete" in input_lower or "done" in input_lower:
                status_filter = "completed"
                
            if "high priority" in input_lower:
                priority_filter = "high"
            elif "medium priority" in input_lower:
                priority_filter = "medium"
            elif "low priority" in input_lower:
                priority_filter = "low"
                
            return self.list_tasks(status_filter, priority_filter)
            
        # Not a task command
        return None

    def ask(self, user_input):
        # First check if this is a task-related command
        task_response = self.parse_task_commands(user_input)
        if task_response:
            self.log_interaction(user_input, task_response)
            return task_response
        
        # Check if asking about a specific task
        for task_id in self.tasks:
            if task_id in user_input and ("task" in user_input.lower() or "progress" in user_input.lower()):
                task_info = self.get_task_progress(task_id)
                self.log_interaction(user_input, task_info)
                return task_info
        
        # Add task context to more complex queries
        context = ""
        if "task" in user_input.lower():
            # Extract task details for context
            task_summary = self.list_tasks()
            context = f"Current tasks information: {task_summary}\n\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": context + user_input}
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
        for i, entry in enumerate(self.conversation_log[-5:], len(self.conversation_log)-4):  # Show last 5
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
            q = entry['query']
            summary += f"{i}. [{timestamp}] {q[:75]}{'...' if len(q) > 75 else ''}\n"
        
        if self.tasks:
            pending_tasks = sum(1 for t in self.tasks.values() if t['status'] == 'pending')
            in_progress = sum(1 for t in self.tasks.values() if t['status'] == 'in_progress')
            completed = sum(1 for t in self.tasks.values() if t['status'] == 'completed')
            
            summary += f"\nTasks Summary: {len(self.tasks)} total ({pending_tasks} pending, {in_progress} in progress, {completed} completed)\n"
        
        return summary

    def chat_interface(self):
        print("AI Task Tracker Bot - Commands:")
        print("- 'fetch tasks from email' to import tasks from email")
        print("- 'update task: [task_id]: [update details]' to update a task")
        print("- 'task progress: [task_id]' to check task status")
        print("- 'list tasks' to see all tasks")
        print("- 'summary' to view conversation history")
        print("- 'exit' to quit")
        
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

# Flask API implementation
from flask import Flask, request, jsonify
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS for local development

    bot = AITaskTrackerBot()

    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.get_json()
        user_message = data.get("message")
        if not user_message:
            return jsonify({"response": "No message provided"}), 400

        response = bot.ask(user_message)
        return jsonify({"response": response})
    
    @app.route("/api/tasks", methods=["GET"])
    def get_tasks():
        status = request.args.get("status")
        priority = request.args.get("priority")
        
        tasks = bot.tasks
        if status:
            tasks = {k: v for k, v in tasks.items() if v["status"] == status}
        if priority:
            tasks = {k: v for k, v in tasks.items() if v.get("priority") == priority}
            
        return jsonify(tasks)
    
    @app.route("/api/tasks/<task_id>", methods=["GET"])
    def get_task(task_id):
        if task_id not in bot.tasks:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(bot.tasks[task_id])
    
    @app.route("/api/tasks/<task_id>", methods=["PUT"])
    def update_task(task_id):
        if task_id not in bot.tasks:
            return jsonify({"error": "Task not found"}), 404
            
        data = request.get_json()
        status = data.get("status")
        progress = data.get("progress")
        note = data.get("note")
        
        bot.update_task(task_id, status, progress, note)
        return jsonify({"task": bot.tasks[task_id]})
    
    @app.route("/api/fetch-email-tasks", methods=["POST"])
    def fetch_email_tasks():
        result = bot.fetch_tasks_from_email()
        return jsonify({"message": result})
        
    return app

if __name__ == "__main__":
    # Choose whether to run in CLI mode or as web server
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        app = create_app()
        app.run(port=5000, debug=True)
    else:
        bot = AITaskTrackerBot()
        bot.chat_interface()