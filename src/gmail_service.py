from googleapiclient.discovery import build
from pathlib import Path
from src.preprocessor import preprocess_email, get_best_body
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

class GmailService:
    def __init__(self, credentials):
        """Initializes the Gmail API service using authenticated credentials."""
        self.service = build("gmail", "v1", credentials=credentials)
        self.user_id = "me"

    def list_inbox_messages(self, max_results=50, page_token=None):
        """Fetches a list of message IDs from the inbox."""
        try:
            logging.info("Fetching email message IDs")
            results = (
                self.service.users()
                .messages()
                .list(
                    userId=self.user_id,
                    labelIds=["INBOX"],
                    maxResults=max_results,
                    pageToken=page_token,
                )
                .execute()
            )
            return results.get("messages", []), results.get("nextPageToken")
        except Exception as e:
            logging.error("Error listing messages: %s", e)
            return [], None

    def get_message_details(self, message_id):
        """Retrieves the full content of a specific."""
        try:
            result = (
                self.service.users()
                .messages()
                .get(userId=self.user_id, id=message_id)
                .execute()
            )
            email_dict = {"Id": result["id"]}

            payload_headers = result["payload"]["headers"]
            for header in payload_headers:
                if header["name"] == "Subject":
                    email_dict["Subject"] = header["value"]
                elif header["name"] == "From":
                    email_dict["From"] = header["value"]

            body = get_best_body(result["payload"])
            clean_body = preprocess_email(body)
            email_dict["Body"] = clean_body
            return email_dict
        except Exception as e:
            logging.error("Error fetching message %s: %s", message_id, e)
            return None

    def trash_message(self, message_id):
        """Moves a message to the Trash folder."""
        try:
            self.service.users().messages().trash(
                userId=self.user_id, id=message_id
            ).execute()
            return True
        except Exception as e:
            print(f"Error trashing message {message_id}: {e}")
            return False
