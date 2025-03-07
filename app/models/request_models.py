from pydantic import BaseModel

class SentenceInput(BaseModel):
    sentence: str