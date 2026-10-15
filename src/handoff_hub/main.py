"""FastAPI entrypoint for the local-only SQLite proof of concept."""
from handoff_hub.poc_api import create_app

app = create_app()
