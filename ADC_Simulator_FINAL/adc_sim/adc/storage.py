"""Storage module.

Secret: where and in what format persistent data is kept (JSON files in a
data folder, written atomically).
Anticipated change: logs and inventory move from local files to a database.

Interface
  load(name, default) -> object          read a saved document, or default
  save(name, obj)                         replace a document atomically
  append(name, record)                    add one record to an append-only list
  read_all(name) -> list                  every record appended so far
"""
import json
import os


class JsonStore:
    def __init__(self, folder: str):
        self._dir = folder
        os.makedirs(folder, exist_ok=True)

    def _path(self, name, ext):
        return os.path.join(self._dir, f"{name}.{ext}")

    def load(self, name, default):
        p = self._path(name, "json")
        if not os.path.exists(p):
            return default
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    def save(self, name, obj):
        p = self._path(name, "json")
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1)
        os.replace(tmp, p)

    def append(self, name, record):
        with open(self._path(name, "jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def read_all(self, name):
        p = self._path(name, "jsonl")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
