from fastapi import Request
from groq import AsyncGroq


def get_groq_client(request: Request) -> AsyncGroq:
    return request.app.state.groq_client
