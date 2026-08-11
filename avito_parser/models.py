"""
Модели данных парсера Avito.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Listing:
    """Одно найденное объявление."""
    article: str              # Искомый артикул
    search_query: str         # Поисковый запрос
    title: str                # Заголовок
    price: Optional[int]      # Цена (число, руб.) или None
    city: str                 # Город / регион
    condition: str            # Состояние товара
    url: str                  # Ссылка на объявление
    rank_by_price: int        # Место по цене (1 = самое дешёвое)
    check_datetime: str       # Дата и время проверки
