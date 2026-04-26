from langchain_ollama import ChatOllama
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.output_parsers.json import JsonOutputParser
from src.models import EmailClassification
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

BASE_DIR = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system.txt"


def get_classification_chain():
    # Initialize local LLM
    llm = ChatOllama(
        model="deepseek-r1:8b", temperature=0, reasoning=False, format="json"
    )

    logging.info("LLM %s initialized", llm.model)

    # Load the system prompt from the text file
    system_template = SYSTEM_PROMPT_PATH.read_text()

    # Define email classify message structure
    email_classification_template = """
        Classify the following email:
        from: {sender}
        subject: {subject}
        body: {body}
    """

    # Set up pydantic parser
    parser = JsonOutputParser(pydantic_object=EmailClassification)

    # Build the prompt template
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(email_classification_template),
        ]
    )

    # Injecting format instructions
    ready_prompt = chat_prompt.partial(
        format_instructions=parser.get_format_instructions()
    )

    # Return the chain using the partialled prompt
    return ready_prompt | llm | parser
