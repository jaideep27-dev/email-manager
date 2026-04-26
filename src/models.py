from typing import Literal
from pydantic import BaseModel, Field


class EmailClassification(BaseModel):
    classification: Literal["keep", "remove"] = Field(
        description="Whether to keep the email or remove it."
    )
    reasoning: str = Field(
        description="A brief 2-sentence explanation for the decision."
    )
    confidence_score: float = Field(
        description="The confidence level of the classification from 0.0 to 1.0.",
        ge=0,
        le=1,
    )
    category: Literal["personal", "transactional", "promotional", "spam", "other"] = (
        Field(description="The category the email falls into.")
    )

    def __str__(self):
        out = ""
        out += "\nClassification: " + self.classification.upper() + "\n"
        out += "Reasoning: " + self.reasoning + "\n"
        out += "Confidence: " + self.confidence_score + "\n"
        out += "Category: " + self.category.upper() + "\n"
        return out
