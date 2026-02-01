"""Simple in-memory metrics collector."""

from collections import defaultdict
from threading import Lock


class MetricsCollector:
    def __init__(self):
        self._lock = Lock()
        self._request_count = 0
        self._status_codes = defaultdict(int)

    def increment_request(self):
        with self._lock:
            self._request_count += 1

    def record_status_code(self, code: int):
        with self._lock:
            self._status_codes[code] += 1

    def get_metrics(self) -> dict:
        with self._lock:
            return {
                "total_requests": self._request_count,
                "status_codes": dict(self._status_codes),
            }


metrics = MetricsCollector()
