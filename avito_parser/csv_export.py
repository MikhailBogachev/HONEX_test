"""Экспорт результатов в CSV."""

import csv
import logging
from pathlib import Path

from .models import Listing

log = logging.getLogger(__name__)


def write_csv(results: list[Listing], output_path: str = "result.csv") -> None:
    """Сохраняет результаты в CSV-файл с кодировкой UTF-8 BOM."""
    if not results:
        log.warning("Нет данных для записи в CSV")
        return

    fieldnames = [
        "article", "search_query", "title", "price",
        "city", "condition", "url", "rank_by_price", "check_datetime",
    ]

    try:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for listing in results:
                writer.writerow({
                    "article": listing.article,
                    "search_query": listing.search_query,
                    "title": listing.title,
                    "price": listing.price,
                    "city": listing.city,
                    "condition": listing.condition,
                    "url": listing.url,
                    "rank_by_price": listing.rank_by_price,
                    "check_datetime": listing.check_datetime,
                })
        log.info("Результаты сохранены в %s (%d строк)", output_path, len(results))
    except OSError as e:
        log.error("Ошибка записи CSV: %s", e)
        raise
