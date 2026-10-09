import uvicorn

from ianua.core.config import settings
from ianua.core.logging_config import configure_logging


def main() -> None:
    configure_logging(debug=settings.debug)

    uvicorn.run(
        "ianua.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.debug,
        log_config=None,
    )

if __name__ == "__main__":
    main()