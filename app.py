from src.gmail_service import GmailService
from src.auth import authenticate_with_google
from src.llm_handler import get_classification_chain
import logging
from src import database

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

def email_manager(chain, gmail_service, next_page_token):
    total_processed = 0
    messages, next_page_token = gmail_service.list_inbox_messages(max_results=50, page_token=next_page_token)
    emails_list = []
    for message in messages:
        emails_list.append(gmail_service.get_message_details(message["id"]))
    logging.info("Total messages retrieved : %s", len(emails_list))

    for email in emails_list:
        if not database.is_processed(email['Id']):
            logging.info("Invoking chain for message ID : %s", email["Id"])
            result = chain.invoke(
                {
                    "sender": email.get("From"),
                    "subject": email.get("Subject"),
                    "body": email.get("Body"),
                }
            )
            logging.info(
                "\n\nClassification: %s\nReason: %s\nConfidence: %s\nCategory: %s\n\n",
                result["classification"],
                result["reasoning"],
                result["confidence_score"],
                result["category"],
            )
            if result["classification"] == "remove" and result["confidence_score"] > 0.8:
                if gmail_service.trash_message(email["Id"]):
                    logging.info("Email moved to trash successfully!")
                else:
                    logging.info("Failed to move the email to trash")
            database.mark_as_processed(email["Id"], result['classification'])
            logging.info("Saved the result in database")
            total_processed += 1
    return total_processed, next_page_token

def main():
    # Initialize database
    database.init_db()

    # Initiate authentication
    credentials = authenticate_with_google()
    logging.info("Authentication successful!")

    # Instantiate Gmail Service
    gmail_service = GmailService(credentials=credentials)

    # Get LLM chain
    chain = get_classification_chain()
    logging.info("Chain created successfully")

    user_input = None
    page_token = None
    total_emails_processed = 0
    do_process_all = False
    while True:
        if not (do_process_all and user_input):
            user_input = input("Do you want to continue? (Y/N): ")
        if user_input.lower() == "y":
            current_emails_processed, next_page_token = email_manager(chain, gmail_service, page_token)
            total_emails_processed += current_emails_processed
            page_token = next_page_token
            logging.info("Next page token: %s", page_token)
            logging.info("Processed Emails: %s", total_emails_processed)
            if not page_token:
                logging.info("All emails processed")
                break
        elif user_input.lower() == "all":
            do_process_all = True
            user_input = "y"
        elif user_input.lower() == "n":
            logging.info("Exiting...")
            break
        else:
            logging.info("Incorrect input! try again")
    logging.info("Total emails processed : %s", total_emails_processed)

   
        


if __name__ == "__main__":
    main()
