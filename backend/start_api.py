import os

import uvicorn


def main():
    uvicorn.run(
        "backend.api:app",
        host=os.getenv("AZE_API_HOST", "127.0.0.1"),
        port=int(os.getenv("AZE_API_PORT", "8000")),
        reload=False,
        log_level=os.getenv("AZE_API_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
