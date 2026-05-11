from __future__ import annotations

from abc import ABC, abstractmethod

import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from app.models import RawArticle


disable_warnings(InsecureRequestWarning)


class BaseSourceAdapter(ABC):
    source_name: str

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def get_text(self, url: str, *, encoding: str | None = None) -> str:
        response = self.session.get(url, timeout=20, verify=False)
        response.raise_for_status()
        if encoding:
            response.encoding = encoding
        elif response.apparent_encoding:
            response.encoding = response.apparent_encoding
        return response.text

    @abstractmethod
    def fetch(self, source_day_compact: str) -> list[RawArticle]:
        raise NotImplementedError
