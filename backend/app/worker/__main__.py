"""Entrypoint do worker: `python -m app.worker`. Por enquanto só um loop vazio."""

import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("worker")


def main() -> None:
    log.info("worker iniciado")
    while True:
        log.info("worker rodando")
        time.sleep(60)


if __name__ == "__main__":
    main()
