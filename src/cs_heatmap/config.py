"""配置读取；底图校准与业务统计口径分离。"""
import json
from pathlib import Path

MAPS = ("dust2", "mirage", "inferno", "ancient", "cache", "anubis", "nuke")
SCHEMA_VERSION = 2
SAMPLE_INTERVAL = 0.2
POLICY = "freeze+10s_alive-ct_0.2s_preplant_v2"


def read_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_maps(path="config/maps.json"):
    config = read_json(path)
    if set(config) != set(MAPS):
        raise ValueError("地图配置必须恰好包含固定七图白名单")
    for name, item in config.items():
        if item["scale"] <= 0 or item.get("rotate", 0) != 0:
            raise ValueError(f"{name}: 无效 scale 或尚未支持的旋转雷达")
    return config
