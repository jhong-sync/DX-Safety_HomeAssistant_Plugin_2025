import time, json, os
from pathlib import Path

class DedupStore:
    def __init__(self, ttl=86400, path="/data/dedup.json"):
        self.ttl = ttl
        self.path = Path(path)
        self.state = {}
        self._load()
    def _load(self):
        if self.path.exists():
            try:
                self.state = json.loads(self.path.read_text())
            except Exception:
                self.state = {}
    def _save(self):
        self.path.write_text(json.dumps(self._purge(), ensure_ascii=False))
    def _purge(self):
        now = time.time()
        return {k:v for k,v in self.state.items() if now - v < self.ttl}
    def accept(self, event_id: str, sent_at: str) -> bool:
        key = f"{event_id}:{sent_at}"
        now = time.time()
        ok = key not in self.state
        self.state[key] = now
        self._save()
        return ok