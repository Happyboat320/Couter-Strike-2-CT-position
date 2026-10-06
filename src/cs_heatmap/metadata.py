"""地图由 demo 识别；赛事由 HLTV 原始包名/父目录识别，不猜测头部未提供的信息。"""
from dataclasses import dataclass
from pathlib import Path
import re
from .config import read_json


@dataclass(frozen=True)
class Event:
    id: str
    name: str
    date: str | None
    source: str


def identify_event(source: Path, catalog: dict) -> Event:
    candidates = [source.name.lower(), *(part.lower() for part in source.parts[:-1][::-1])]
    # 精确目录名或原始包名前缀；别名来自可维护赛事目录。
    for candidate in candidates:
        for event_id, info in catalog.items():
            if any(candidate == alias or candidate.startswith(alias + "-") or candidate.startswith(alias + ".")
                   for alias in [event_id, *info.get("aliases", [])]):
                return Event(event_id, info["name"], info.get("start_date"), "filename/catalog")
    for candidate in candidates:
        # HLTV 常见包名：赛事-年份/season-N-队伍-vs-队伍-…；只识别赛事部分。
        match = re.match(r"^([a-z0-9][a-z0-9-]*?(?:20\d{2}|season-\d+))(?:-|\.|$)", candidate)
        if match:
            event_id = match[1]
            return Event(event_id, event_id.replace("-", " "), None, "filename")
    return Event("unclassified", "未识别赛事", None, "unknown")


def load_events(path=Path("config/events.json")):
    return read_json(path)
