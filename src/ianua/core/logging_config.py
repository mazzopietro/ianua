
import logging
import sys


def configure_logging(debug: bool = False) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Aggiunge la console una sola volta, senza rimuovere
    # gli handler già presenti, incluso quello di pytest.
    if not any(
        getattr(handler, "_ianua_console_handler", False)
        for handler in root_logger.handlers
    ):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s - %(message)s"
            )
        )
        console_handler._ianua_console_handler = True
        root_logger.addHandler(console_handler)