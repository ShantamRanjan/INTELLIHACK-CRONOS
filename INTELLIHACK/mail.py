import os
import json
from datetime import datetime, timedelta
import re
from openai import OpenAI
from dotenv import load_dotenv
from imapclient import IMAPClient
import pyzmail
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

class PerplexityEmailAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable not set")

        self.client = OpenAI(api_key=self.api_key, base_url="https://api.perplexity.ai")

    def extract_meeting_info(self, email_text):
        system_prompt = (
            "You are a highly skilled AI assistant, expert in identifying and extracting meeting information from email text. "
            "Your goal is to extract the date, time, and meeting link (if any) from the provided email content. "
            "1. Analyze the email text carefully to identify potential meeting details. "
            "2. If a meeting is found, return a JSON object with the keys: 'date' (YYYY-MM-DD format), 'time' (HH:MM in 24-hour format), 'link' (URL), and 'description' (short summary of meeting context)."
            "3. If any of the date, time, or link information is missing, extract the date and time for the call to happen from today forward.  The date for the call is likely to be happening in a short amount of time"
            "4. If no meeting is found return an empty JSON `{}`"
            "5. Focus on emails that contain google meet or zoom link"
            "Ensure your output is a valid JSON object."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": email_text}
        ]

        try:
            response = self.client.chat.completions.create(
                model="sonar-pro",
                messages=messages,
                temperature=0.1  # Reduced temperature for more consistent output
            )
            content = response.choices[0].message.content.strip()

            # Extract JSON from response
            start = content.find('{')
            end = content.rfind('}') + 1
            json_str = content[start:end]
            try:
                meeting_info = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}, Content: {json_str}")
                return {}

            return meeting_info
        except Exception as e:
            print(f"Error during extraction: {e}")
            return {"error": str(e)}

def add_meeting_to_calendar(meeting_info):
    """Adds meeting details to Google Calendar."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                return  # Stop if refresh fails
        else:
            try:
                # Check if credentials.json exists
                if not os.path.exists('credentials.json'):
                    print("Error: credentials.json file not found in the same directory as the script.")
                    return

                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                print("Error: credentials.json file not found.  Make sure it is in the same directory")
                return  # Stop if not found
            except Exception as e:
                print(f"Error during authentication flow: {e}")
                return
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)
        # Convert meeting time to RFC3339 format with timezone
        date_str = meeting_info.get('date')
        time_str = meeting_info.get('time')

        # Validate date and time
        if not date_str or not time_str:
            print("Missing date or time information. Cannot add to calendar.")
            return

        try:
            # Combine date and time
            combined_dt_str = f"{date_str}T{time_str}:00"  # Assuming UTC, adjust as needed

            # Attempt to parse the combined datetime string
            event_start_time = datetime.strptime(combined_dt_str, '%Y-%m-%dT%H:%M:%S')
            # Add a timezone offset (IST is UTC+5:30)
            event_start_time = event_start_time - timedelta(hours=5, minutes=30)
            event_start_time = event_start_time.isoformat() + 'Z'

        except ValueError as e:
            print(f"Error parsing date or time: {e}")
            return

        # Create the event
        event = {
            'summary': 'Scheduled Meeting',
            'description': meeting_info.get('description', 'Meeting Link: ' + str(meeting_info.get('link'))),
            'start': {
                'dateTime': event_start_time,
                'timeZone': 'UTC',  # Use UTC as a default, adjust if known
            },
            'end': {
                'dateTime': (datetime.strptime(combined_dt_str, '%Y-%m-%dT%H:%M:%S')  - timedelta(hours=5, minutes=30)).isoformat() + 'Z', # Same time as start for now - could add a duration
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")

    except Exception as e:
        print(f"An error occurred: {e}")

class EmailInboxProcessor:
    def __init__(self):
        load_dotenv()
        self.host = os.getenv("EMAIL_HOST")
        self.user = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASS")
        if not all([self.host, self.user, self.password]):
            raise ValueError("Email credentials not fully set in environment variables")
        self.agent = PerplexityEmailAgent()

    def fetch_unread_emails(self, folder="INBOX", limit=50):  # Increase limit for more recent emails
        with IMAPClient(self.host) as server:
            server.login(self.user, self.password)
            server.select_folder(folder)
            # Search for unseen emails
            messages = server.search(['UNSEEN'])
            print(f"Found {len(messages)} unread emails.")
            # Get most recent emails
            messages = messages[-limit:] #get last limit

            emails = []
            for uid in messages:
                raw_message = server.fetch([uid], ['RFC822'])[uid][b'RFC822']
                message = pyzmail.PyzMessage.factory(raw_message)
                subject = None  # Initialize subject
                try:
                    subject = message.get_subject()
                except Exception as e:
                    print(f"Error getting subject: {e}")
                    subject = "Subject unavailable"

                from_ = message.get_addresses('from')
                # Extract text/plain or fallback to html
                if message.text_part:
                    try:
                        body = message.text_part.get_payload().decode(message.text_part.charset or 'utf-8', errors='ignore')
                    except Exception as e:
                        print(f"Text part decode error {uid}: {e}")
                        body = ""
                elif message.html_part:
                    try:
                        body = message.html_part.get_payload().decode(message.html_part.charset or 'utf-8', errors='ignore')
                    except Exception as e:
                        print(f"HTML part decode error {uid}: {e}")
                        body = ""
                else:
                    body = ""

                emails.append({
                    "uid": uid,
                    "subject": subject,
                    "from": from_,
                    "body": body
                })
            return emails

    def process_emails(self):
        emails = self.fetch_unread_emails()
        results = []
        for email in emails:
            try:
                print(f"Processing email UID {email['uid']} Subject: {email['subject']}")
            except UnicodeEncodeError as e:
                print(f"Could not print email info due to encoding error: {e}")
            if "meet.google.com" in email['body'] or "zoom.us" in email['body']: #check emails for link and process
                meeting_info = self.agent.extract_meeting_info(email['body'])

                if meeting_info and meeting_info != {}:  # Check for non-empty meeting information
                    add_meeting_to_calendar(meeting_info)
                    print(f"Added meeting to calendar for email {email['uid']}")
                    results.append({
                        "email_uid": email['uid'],
                        "subject": email['subject'],
                        "from": email['from'],
                        "meeting_info": meeting_info
                    })
                else:
                    print(f"No meeting information found in email {email['uid']}")
            else:
                print(f"Skipping email {email['uid']} as no gmeet/zoom link was found")

        return results

if __name__ == "__main__":
    processor = EmailInboxProcessor()
    extracted_meetings = processor.process_emails()
    
    # Create output directory if it doesn't exist
    output_dir = "meeting_data"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(output_dir, f"extracted_meetings_{timestamp}.json")
    
    # Save results to a JSON file
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(extracted_meetings, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved extracted meetings to {output_filename}")
    except Exception as e:
        print(f"Error saving JSON file: {e}")
    
    # Also print to console (optional)
    try:
        print(json.dumps(extracted_meetings, indent=2, ensure_ascii=False))
    except UnicodeEncodeError as e:
        print(f"Error encoding JSON for console output: {e}")