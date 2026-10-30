# AI Email Triage & Inbox Cleaner

An intelligent, privacy-preserving email triage automation tool powered by local LLMs (Gemma via Ollama), LangChain, and the Google Gmail API. The system fetches unprocessed inbox messages, extracts and sanitizes multipart contents, classifies each email using structured Pydantic schemas, and safely trashes low-value noise (promotions, social updates, and marketing digests) with high-confidence thresholds while persisting audit history in SQLite.

---

## Architecture Overview

```
                      +-----------------------------+
                      |   Google OAuth 2.0 Flow     |
                      |   (credentials / token.json)|
                      +--------------+--------------+
                                     |
                                     v
                          +--------------------+
                          |  Gmail API Client  |
                          | (Users.Messages)   |
                          +----------+---------+
                                     | (Raw Email Payload)
                                     v
                          +--------------------+
                          |  Preprocessor      |
                          |  - MIME traversal  |
                          |  - HTML cleaning   |
                          |  - Head-tail trunc |
                          +----------+---------+
                                     | (Sanitized Text)
                                     v
                          +--------------------+
                          |  LangChain LCEL    |
                          |  Prompt + Rubric   |
                          +----------+---------+
                                     |
                                     v
+---------------------+   +--------------------+
| Local LLM (Ollama)  |<--| Structured Output  |
| (Gemma)    |-->| Pydantic Parser   |
+---------------------+   +----------+---------+
                                     | (Classification, Confidence, Category)
                                     v
                       +-------------+-------------+
                       |                           |
                       v                           v
             +--------------------+      +--------------------+
             | Gmail Trash Action |      | SQLite Audit DB    |
             | (confidence > 0.8  |      | (processed_emails  |
             | & category=remove) |      |  deduplication)    |
             +--------------------+      +--------------------+
```

### Core Architecture Components

1. **Authentication Layer (`src/auth.py`)**:
   - Implements Google OAuth 2.0 with the `gmail.modify` scope.
   - Automatically handles token issuance, disk persistence (`data/token.json`), and silent refresh via Google Auth requests.

2. **Ingestion & MIME Parsing (`src/gmail_service.py` & `src/preprocessor.py`)**:
   - **Recursive MIME Walking**: Traverses nested multipart MIME structures (`multipart/alternative`, `multipart/mixed`, `multipart/related`).
   - **Format Priority**: Intelligently selects plaintext over HTML when both exist, decoding base64-urlsafe representations with automatic padding repair and resilient character encoding.
   - **DOM Sanitization**: Employs BeautifulSoup to strip `<script>`, `<style>`, `<header>`, and `<footer>` tags, normalizing excess whitespace.
   - **Sandwich Head-Tail Truncation**: Safeguards against context-window explosion on long marketing or legal emails by preserving the top 80% (essential message context) and trailing 20% (sign-offs, unsubscribes, and metadata links).

3. **Inference & Structured Parsing (`src/llm_handler.py`, `src/models.py`, `prompts/system.txt`)**:
   - Powered by a local Ollama deployment running `Gemma` (zero-temperature, zero data leakage).
   - Enforces deterministic output schema via LangChain's `JsonOutputParser` paired with a Pydantic model (`classification`, `confidence_score`, `reasoning`, `category`).
   - Rubric explicitly enforces defensive retention ("When ambiguous, default to keep").

4. **Persistence & Safeguards (`src/database.py` & `app.py`)**:
   - SQLite table tracks `message_id`, `classification`, and processing timestamps to guarantee idempotency and avoid duplicate LLM inferences.
   - Guarded execution: Only messages classified as `remove` with a `confidence_score > 0.8` are moved to Gmail Trash.

---

## Features

- **100% Local Inference & Privacy**: Email content never leaves your local machine; inference is executed on local hardware via Ollama.
- **Structured JSON Decisions**: Guaranteed JSON outputs matching Pydantic models for safe downstream integration.
- **Defensive Triage Guardrails**: Strict confidence thresholding (`> 0.8`) and soft-delete semantics (moves to Gmail Trash instead of permanent deletion).
- **Idempotent Processing**: Local SQLite database tracks processed IDs, preventing redundant API calls and re-processing costs.
- **Interactive Batch Processing**: Clean CLI interface supporting chunked page-by-page traversal or hands-free batch cleanup.

---

## Project Structure

```
email_manager/
│
├── app.py                  # Application entry point & orchestration workflow
├── prompts/
│   └── system.txt          # Detailed email triage rubric and classification guidelines
├── src/
│   ├── __init__.py
│   ├── auth.py             # Google OAuth 2.0 flow and token lifecycle manager
│   ├── database.py         # SQLite connection layer for idempotency and history
│   ├── gmail_service.py    # Gmail API client wrapper (list, fetch, trash)
│   ├── llm_handler.py      # LangChain chain assembly (prompt + Ollama + parser)
│   ├── models.py           # Pydantic schema for structured triage outputs
│   └── preprocessor.py     # MIME parser, BeautifulSoup HTML stripping, and text truncator
└── data/                   # (Excluded from git)
    ├── credentials.json    # OAuth client secrets from Google Cloud Console
    ├── token.json          # Cached access and refresh tokens
    └── processed_emails.db # SQLite database
```

---

## Prerequisites

1. **Python 3.10+**
2. **Ollama**: Installed and running locally.
   - Pull the Gemma model:
     ```bash
     ollama pull gemma4:e2b
     ```
3. **Google Cloud Project**:
   - Enable the **Gmail API** in Google Cloud Console.
   - Configure the **OAuth Consent Screen** (set User Type to External and add your Gmail address as a test user).
   - Create **OAuth 2.0 Client IDs** (Desktop application) and download the client secret file as `credentials.json`.
   - Place `credentials.json` into the `data/` directory.

---

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd email_manager
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Linux / macOS
   python -m venv venv
   source venv/bin/activate

   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```bash
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib langchain langchain-ollama pydantic beautifulsoup4
   ```

4. **Verify Ollama**:
   Ensure the Ollama daemon is running:
   ```bash
   ollama list
   ```

---

## Usage

Run the main application:
```bash
python app.py
```

### Workflow Execution
1. On first run, a browser window opens requesting authorization with the `gmail.modify` scope. Tokens are automatically cached in `data/token.json`.
2. The system checks `data/processed_emails.db` to ensure previously handled emails are not re-processed.
3. The interactive CLI prompts:
   - `Y`: Processes the next batch of up to 50 emails.
   - `ALL`: Runs continuously across all pagination tokens until all inbox messages are processed.
   - `N`: Safely terminates execution.
4. Emails meeting removal criteria (`classification == "remove"` and `confidence > 0.8`) are moved to the Trash.

---

## Extensibility & Future Enhancements

- **Autonomous Background Worker**: Wrap the CLI runner into an async cron job or Windows/systemd background daemon.
- **Fine-grained Actions**: Add custom Gmail label application (e.g., `Archive`, `Newsletters`, `Follow-up`) alongside trashing.
- **Multi-Model Provider Swapping**: Switch between local Ollama models or remote API endpoints via environment variables.

