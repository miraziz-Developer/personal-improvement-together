"""ASGI entry point:  uv run uvicorn pit.main:app --reload"""

from pit.api.app import create_app

app = create_app()
