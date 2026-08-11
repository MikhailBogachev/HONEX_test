"""
Взаимодействие с API Avito.

build_search_url() — формирует URL для GET-запроса.
fetch_json_from_api() — выполняет запрос с ретраями и обработкой HTTP 439.
load_test_data() — загружает мок-данные из файла.
"""

import json
import logging
import os
import time
from typing import Optional
from urllib.parse import urlencode

import requests

from .config import (
    API_URL, CATEGORY_ID, CHALLENGE_WAIT, CONDITION_NEW_PARAM, GEO_COORDS,
    HEADERS, LOCATION_ID, MAX_RETRIES, MOCK_DATA_DIR, REQUEST_TIMEOUT,
    RETRY_DELAY, ROOT_CATEGORY_ID,
)

log = logging.getLogger(__name__)


def build_search_url(query: str, page: int = 1) -> str:
    """
    Формирует URL для API-запроса поиска Avito.

    Args:
        query: поисковый запрос (артикул)
        page: номер страницы (начиная с 1)

    Returns:
        Полный URL для GET-запроса
    """
    params = {
        "categoryId": CATEGORY_ID,
        "locationId": LOCATION_ID,
        "name": query,
        "rootCategoryId": ROOT_CATEGORY_ID,
        "verticalCategoryId": 0,
        "geoCoords": GEO_COORDS,
        "cd": 1,
        "s": 1,
        "localPriority": 0,
        "sort": 1,    # 1 = «Дешевле»
        "p": page,
    }

    if CONDITION_NEW_PARAM:
        params[CONDITION_NEW_PARAM[0]] = CONDITION_NEW_PARAM[1]

    return f"{API_URL}?{urlencode(params, doseq=True)}"


def fetch_json_from_api(
    query: str,
    page: int = 1,
    max_retries: int = MAX_RETRIES,
    retry_delay: float = RETRY_DELAY,
) -> Optional[dict]:
    """
    Выполняет GET-запрос к API Avito и возвращает JSON.

    При HTTP 439 (антибот): читает Set-Cookie, ждёт CHALLENGE_WAIT, повторяет.
    При прочих ошибках — до max_retries попыток с экспоненциальным backoff.

    Returns:
        Словарь с JSON-ответом или None
    """
    url = build_search_url(query, page)

    session = requests.Session()
    session.headers.update(HEADERS)

    for attempt in range(1, max_retries + 1):
        log.info("Попытка %d/%d — Запрос API: %s", attempt, max_retries, url)

        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)

            if resp.status_code == 439:
                _ = resp.content  # session принимает Set-Cookie
                log.warning(
                    "Попытка %d/%d — HTTP 439 (антибот). "
                    "Cookie: %s. Пауза %.1f сек…",
                    attempt, max_retries,
                    dict(session.cookies), CHALLENGE_WAIT,
                )
                time.sleep(CHALLENGE_WAIT)
                continue

            resp.raise_for_status()
            return resp.json()

        except json.JSONDecodeError as e:
            log.warning("Попытка %d/%d — ошибка JSON: %s",
                        attempt, max_retries, e)
        except requests.exceptions.HTTPError as e:
            log.warning("Попытка %d/%d — HTTP %s: %s",
                        attempt, max_retries, resp.status_code, e)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            log.warning("Попытка %d/%d — ошибка сети: %s",
                        attempt, max_retries, e)

        if attempt < max_retries:
            delay = retry_delay * (2 ** (attempt - 1))
            log.info("Повтор через %.1f сек…", delay)
            time.sleep(delay)

    log.error("Все %d попытки исчерпаны для '%s'", max_retries, query)
    return None


def load_test_data(article: str) -> Optional[dict]:
    """
    Загружает тестовые данные для артикула (fallback).

    Ищет файл mock_data/{article}.json.

    Returns:
        Словарь с данными или None
    """
    file_path = os.path.join(MOCK_DATA_DIR, f"{article}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            log.info("Загружены тестовые данные из: %s", file_path)
            return data
    except FileNotFoundError:
        log.error("Файл тестовых данных не найден: %s", file_path)
    except json.JSONDecodeError as e:
        log.error("Ошибка парсинга '%s': %s", file_path, e)

    return None
