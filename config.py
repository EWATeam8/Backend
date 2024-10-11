import os


class Config:
    SECRET_KEY = os.environ.get("OPENAI_API_KEY")
