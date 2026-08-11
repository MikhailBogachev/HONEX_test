"""
Парсинг и обработка объявлений Avito.

extract_items() — извлекает список объявлений из JSON.
process_article() — оркестратор: API → fallback → фильтры → сортировка → top-N.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from .api import fetch_json_from_api, load_test_data
from .config import BASE_URL, CONDITION, TOP_N
from .models import Listing

log = logging.getLogger(__name__)


def extract_items(data: dict) -> list[dict]:
    """
    Извлекает список объявлений из JSON-ответа: data → catalog → items[].
    """
    try:
        items = data.get("catalog", {}).get("items", [])
        if not items:
            log.warning("Список объявлений пуст (catalog.items)")
        return items
    except (AttributeError, TypeError) as e:
        log.error("Неожиданная структура JSON: %s", e)
        return []


def _get_price(item: dict) -> float:
    """Извлекает числовую цену (для сортировки). Inf если цены нет."""
    pd = item.get("priceDetailed") or item.get("price") or {}
    if isinstance(pd, dict):
        return pd.get("value") or float("inf")
    if isinstance(pd, (int, float)):
        return pd
    return float("inf")


def _extract_price(item: dict) -> Optional[int]:
    """Извлекает цену как int, или None."""
    raw = item.get("priceDetailed") or item.get("price") or {}
    if isinstance(raw, dict):
        val = raw.get("value")
    elif isinstance(raw, (int, float)):
        val = raw
    else:
        return None
    if val is not None and isinstance(val, (int, float)):
        return int(val)
    return None


def _has_article_in_spare_parts(item: dict, article: str) -> bool:
    """
    Проверяет, содержит ли объявление артикул в SparePartsParamsStep.

    Путь: item → iva → SparePartsParamsStep[] → payload → text
    """
    norm = article.upper().replace("-", "").replace(" ", "")
    try:
        iva = item.get("iva") or {}
        for step in (iva.get("SparePartsParamsStep") or []):
            text = step.get("payload", {}).get("text", "")
            if norm in text.upper().replace("-", "").replace(" ", ""):
                return True
    except (AttributeError, TypeError):
        pass
    return False


def _parse_item(item: dict, article: str, rank: int, check_time: str) -> Listing:
    """Преобразует словарь из catalog.items[] в Listing."""
    title = item.get("title", "").strip()

    location = item.get("location") or {}
    city = (location.get("name", "") if isinstance(location, dict) else "")
    if not city:
        city = (item.get("coords") or {}).get("address_user", "")

    url_path = item.get("urlPath", "")
    url = f"{BASE_URL}{url_path}" if url_path else ""

    return Listing(
        article=article,
        search_query=article,
        title=title,
        price=_extract_price(item),
        city=city,
        condition=CONDITION,
        url=url,
        rank_by_price=rank,
        check_datetime=check_time,
    )


def _error_listing(article: str, title: str, check_time: str) -> Listing:
    """Создаёт Listing-заглушку для ошибки / «не найдено»."""
    return Listing(
        article=article,
        search_query=article,
        title=title,
        price=None, city="", condition="", url="",
        rank_by_price=0,
        check_datetime=check_time,
    )


def process_article(article: str, description: str) -> list[Listing]:
    """
    Ищет объявления по артикулу: API → fallback → фильтры → top-N.

    Returns:
        Список Listing (до TOP_N), или одна строка с ошибкой.
    """
    log.info("Поиск артикула: %s (%s)", article, description)

    check_time = datetime.now(
        tz=timezone(timedelta(hours=8))
    ).strftime("%Y-%m-%d %H:%M:%S %z")

    # 1. Запрос к API
    data = fetch_json_from_api(article)

    # 2. Fallback
    if data is None:
        log.warning("API недоступен для '%s', загружаем тестовые данные", article)
        data = load_test_data(article)

    if data is None:
        log.error("Не удалось получить данные для '%s'", article)
        return [_error_listing(article, "[ОШИБКА] Не удалось получить данные",
                               check_time)]

    # 3. Извлечение
    raw_items = extract_items(data)
    if not raw_items:
        return [_error_listing(article, "[НЕ НАЙДЕНО] Нет подходящих объявлений",
                               check_time)]

    # 4. Фильтр по SparePartsParamsStep
    matching = [i for i in raw_items if _has_article_in_spare_parts(i, article)]
    if not matching:
        return [_error_listing(
            article,
            "[НЕ НАЙДЕНО] Нет объявлений с артикулом в параметрах",
            check_time,
        )]
    log.info("'%s': %d с артикулом в SparePartsParamsStep (из %d)",
             article, len(matching), len(raw_items))

    # 5. С ценой
    with_price = [i for i in matching if _extract_price(i) is not None]

    # 6. Дедупликация
    seen: set[int] = set()
    unique: list[dict] = []
    for item in with_price:
        item_id = item.get("id")
        if item_id and item_id not in seen:
            seen.add(item_id)
            unique.append(item)

    # 7. Сортировка и top-N
    unique.sort(key=_get_price)
    top = unique[:TOP_N]

    listings = [_parse_item(i, article, r, check_time)
                for r, i in enumerate(top, start=1)]

    log.info("'%s': с ценой %d, уникальных %d, отобрано %d",
             article, len(with_price), len(unique), len(listings))
    return listings
