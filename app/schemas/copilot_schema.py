from pydantic import BaseModel


class CopilotQuestion(BaseModel):
    question: str
