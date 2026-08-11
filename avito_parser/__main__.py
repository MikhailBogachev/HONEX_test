"""Точка входа: python -m avito_parser."""

import logging
import sys

from .config import ARTICLES
from .parser import process_article
from .csv_export import write_csv

log = logging.getLogger("avito_parser")


def setup_logging() -> None:
    """Настройка логирования."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, stream=sys.stdout)


def main() -> None:
    setup_logging()
    log.info("Запуск парсера Avito")

    all_results = []
    for article_info in ARTICLES:
        article = article_info["article"]
        description = article_info["description"]
        log.info("Обработка артикула: %s (%s)", article, description)
        results = process_article(article, description)
        all_results.extend(results)

        for r in results:
            price_str = f"{r.price:,}".replace(",", " ") if r.price is not None else "—"
            log.info(
                "  %d. %s | %s ₽ | %s",
                r.rank_by_price, r.title[:60], price_str, r.url,
            )

    write_csv(all_results)
    log.info("Готово! Всего строк: %d", len(all_results))


if __name__ == "__main__":
    main()
