"""按赛事 / demo 存储小型贡献网格，确保增量不会重复累计。"""
from pathlib import Path
import re
import tempfile
import shutil
import numpy as np
from .config import POLICY, SCHEMA_VERSION, read_json, write_json


def identifier(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", value) or value in (".", ".."):
        raise ValueError(f"标识只支持字母、数字、下划线、点和横线: {value}")
    return value


class Store:
    def __init__(self, root: Path, maps: dict):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        metadata = {"schema_version": SCHEMA_VERSION, "policy": POLICY, "maps": maps, "bins": 256}
        config = root / "config.json"
        if config.exists():
            if read_json(config) != metadata:
                raise ValueError("状态目录的采样口径或地图配置不同，请指定新 --state 后重新解析，禁止混入旧 1 秒样本")
        else:
            write_json(config, metadata)

    def path(self, event: str, demo_name: str):
        return self.root / identifier(event) / identifier(Path(demo_name).stem)

    def contains(self, event: str, demo_name: str):
        return (self.path(event, demo_name) / "record.json").exists()

    def save(self, event: str, demo_name: str, record: dict, grids: dict):
        destination = self.path(event, demo_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # 网格和记录作为一项共同提交；失败时不会留下可被当作成功的半成品。
        temporary = Path(tempfile.mkdtemp(prefix=".pending-", dir=destination.parent))
        try:
            np.savez_compressed(temporary / "grids.npz", **grids)
            write_json(temporary / "record.json", record)
            temporary.rename(destination)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)

    def records(self):
        for file in sorted(self.root.glob("*/*/record.json")):
            yield file.parent, read_json(file)

    def summaries(self):
        groups = {}
        for folder, record in self.records():
            event = record["event"]
            group = groups.setdefault(event, {"name":record["event_name"], "date":record["event_date"], "records":[], "grids":{}})
            group["records"].append(record)
            with np.load(folder / "grids.npz") as archive:
                for layer in archive.files:
                    key = (record["map"], layer)
                    grid = archive[layer]
                    group["grids"][key] = group["grids"].get(key, np.zeros_like(grid)) + grid
        return groups
