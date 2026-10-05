"""demo-api: minimal FastAPI service used as the first FlowForge target."""


def main() -> None:
    """Run the development server (entry point of the `demo-api` script)."""
    import uvicorn

    uvicorn.run("demo_api.main:app", host="127.0.0.1", port=8000)
