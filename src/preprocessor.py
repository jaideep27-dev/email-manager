import base64
import re
from bs4 import BeautifulSoup

def preprocess_email(raw_content, max_chars=2000):
    """
    Cleans HTML, removes excessive whitespace, and truncates the body.
    """
    if not raw_content:
        return ""

    # 1. Strip HTML tags and CSS using BeautifulSoup
    soup = BeautifulSoup(raw_content, "html.parser")

    # Remove style and script tags entirely
    for element in soup(["style", "script", "header", "footer"]):
        element.decompose()

    # Get text with a space separator to avoid merging words
    clean_text = soup.get_text(separator=" ")

    # 2. Normalize whitespace (remove tabs, double spaces, and empty lines)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # 3. Sandwich Truncation (Head and Tail)
    # If the email is huge, we take the beginning (context) and the end (metadata/links)
    if len(clean_text) > max_chars:
        head = clean_text[: int(max_chars * 0.8)]
        tail = clean_text[-int(max_chars * 0.2) :]
        clean_text = f"{head}\n\n[... CONTENT TRUNCATED ...]\n\n{tail}"

    return clean_text


def decode_gmail_data(data):
    try:
        # Standardize the data string by adding padding if missing
        padding = "=" * ((4 - len(data) % 4) % 4)
        decoded_bytes = base64.urlsafe_b64decode(data + padding)

        # Use 'ignore' to skip characters that aren't valid UTF-8
        # (common in weirdly formatted newsletters)
        return decoded_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error decoding: {e}")
        return ""

def get_best_body(payload):
    """
    Recursively collects all relevant text parts from the email.
    If it finds an 'alternative' section, it picks only the best format (plain text).
    Otherwise, it collects and joins all text parts found.
    """
    text_parts = []

    def walk_parts(current_part):
        mime_type = current_part.get("mimeType")
        parts = current_part.get("parts", [])
        body_data = current_part.get("body", {}).get("data")

        # 1. Handle Alternative sections (Pick one: prefer plain, then html)
        if mime_type == "multipart/alternative":
            best_subpart = None
            # Look for plain text first
            for subpart in parts:
                if subpart.get("mimeType") == "text/plain" and subpart.get("body", {}).get("data"):
                    best_subpart = subpart
                    break
            # Fallback to HTML if no plain text exists in the alternative section
            if not best_subpart:
                for subpart in parts:
                    if subpart.get("mimeType") == "text/html" and subpart.get("body", {}).get("data"):
                        best_subpart = subpart
                        break
            
            if best_subpart:
                text_parts.append(decode_gmail_data(best_subpart["body"]["data"]))
            return  # Stop recursion for this specific alternative branch

        # 2. Handle leaf nodes with actual data
        if body_data and mime_type in ["text/plain", "text/html"]:
            text_parts.append(decode_gmail_data(body_data))

        # 3. Recursively walk through all other multipart types (mixed, related, etc.)
        for part in parts:
            walk_parts(part)

    walk_parts(payload)
    
    # Combine all collected parts, separated by newlines
    full_content = "\n".join(text_parts).strip()
    return full_content if full_content else "No content found."