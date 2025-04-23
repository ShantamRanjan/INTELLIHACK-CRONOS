import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from imapclient import IMAPClient
import pyzmail
from openai import OpenAI

# ── FORCE UTF-8 OUTPUT ───────────────────────────────────────────────────────
# On Windows consoles this ensures unicode (like “✔”) can be printed
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── CONFIG ────────────────────────────────────────────────────────────────────
load_dotenv()
PERPLEXITY_KEY = os.getenv("PERPLEXITY_API_KEY")
EMAIL_HOST    = os.getenv("EMAIL_HOST")
EMAIL_USER    = os.getenv("EMAIL_USER")
EMAIL_PASS    = os.getenv("EMAIL_PASS")

if not all([PERPLEXITY_KEY, EMAIL_HOST, EMAIL_USER, EMAIL_PASS]):
    raise RuntimeError("Set PERPLEXITY_API_KEY, EMAIL_HOST, EMAIL_USER, EMAIL_PASS in your .env")

# Initialize the Perplexity client (OpenAI‐compatible interface)
openai = OpenAI(api_key=PERPLEXITY_KEY, base_url="https://api.perplexity.ai")

# ── AGENT ─────────────────────────────────────────────────────────────────────
class PerplexityTaskAgent:
    def extract_tasks(self, email_text: str):
        """
        Ask Perplexity to identify any tasks in the email body.
        Returns a list of {"title": ..., "due_date": ...} dicts.
        """
        system = (
            "You are a helpful assistant that extracts TODO tasks from an email. "
            "For each task, return an object with keys: "
            "'title' (string), 'due_date' (ISO 8601 date or null). "
            "Return a JSON array of those objects only; e.g. "
            '[{"title":"Buy milk","due_date":"2025-05-01"},…]. '
            "If no tasks are present, return an empty array [] exactly."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": email_text}
        ]

        resp = openai.chat.completions.create(
            model="sonar-pro",
            messages=messages,
            temperature=0.0
        )
        content = resp.choices[0].message.content.strip()

        # Extract the JSON array between [ ... ]
        start = content.find('[')
        end   = content.rfind(']') + 1
        try:
            return json.loads(content[start:end])
        except Exception:
            return []

# ── EMAIL PROCESSOR ───────────────────────────────────────────────────────────
class EmailInboxProcessor:
    def __init__(self, host, user, password, limit=10):
        self.host   = host
        self.user   = user
        self.passw  = password
        self.limit  = limit
        self.agent  = PerplexityTaskAgent()

    def fetch_recent(self):
        with IMAPClient(self.host) as server:
            server.login(self.user, self.passw)
            server.select_folder("INBOX", readonly=True)
            uids = server.search("ALL")[-self.limit:]
            records = server.fetch(uids, ["RFC822"])

        emails = []
        for uid, data in records.items():
            msg = pyzmail.PyzMessage.factory(data[b"RFC822"])
            if msg.text_part:
                body = msg.text_part.get_payload().decode(
                    msg.text_part.charset or "utf-8",
                    errors="ignore"
                )
            elif msg.html_part:
                body = msg.html_part.get_payload().decode(
                    msg.html_part.charset or "utf-8",
                    errors="ignore"
                )
            else:
                body = ""

            emails.append({
                "uid":     uid,
                "subject": msg.get_subject() or "",
                "from":    msg.get_addresses("from"),
                "body":    body
            })
        return emails

    def process(self):
        emails = self.fetch_recent()
        tasks_out = []
        for e in emails:
            tasks = self.agent.extract_tasks(e["body"])
            for t in tasks:
                tasks_out.append({
                    "email_uid": e["uid"],
                    "title":     t.get("title", "").strip(),
                    "due_date":  t.get("due_date"),
                    "progress":  None
                })
        return tasks_out

# ── RUN & SAVE ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    processor = EmailInboxProcessor(
        EMAIL_HOST, EMAIL_USER, EMAIL_PASS, limit=10
    )
    all_tasks = processor.process()

    # Prepare output path
    out_dir = "task_data"
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = os.path.join(out_dir, f"extracted_tasks_{ts}.json")

    # Write JSON file
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_tasks, f, ensure_ascii=False, indent=2)

    # Final confirmation
    print(f"✔ Wrote {len(all_tasks)} tasks → {out_file}")
