"""FastAPI application entry point."""
import os

import openai
from fastapi import FastAPI
from chromadb import Client
from chromadb.utils import embedding_functions

from .db import init_db
from .routes import router

init_db()

app = FastAPI()

# OpenAI & Chroma setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in environment")

openai.api_key = OPENAI_API_KEY

chroma_client = Client()
collection = chroma_client.get_or_create_collection(
    name="deal_embeddings",
    embedding_function=embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-ada-002",
    ),
)

app.include_router(router)

