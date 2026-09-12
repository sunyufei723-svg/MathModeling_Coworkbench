from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonEvaluationCache:
    """小型、可中断续跑的JSON缓存；每个完成样本立即原子落盘。"""

    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.exists():
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("evaluation cache must contain a JSON object")
            self.data: dict[str, dict[str, Any]] = loaded
        else:
            self.data = {}

    def get(self, key: str) -> dict[str, Any] | None:
        return self.data.get(key)

    def put(self, key: str, value: dict[str, Any]) -> None:
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        temporary.replace(self.path)
