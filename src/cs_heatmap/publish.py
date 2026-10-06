"""仅发布 PNG 和统计索引，不把 demo、选手坐标或依赖上传 Pages。"""
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from .config import POLICY, SAMPLE_INTERVAL, write_json
from .render import render_grid
from .store import Store


def publish(store: Store, maps: dict, output: Path, sigma=2.5, opacity=0.5):
    # 即使没有数据，也先校验绘图参数。
    from .render import heatmap_rgba
    heatmap_rgba(np.zeros((1, 1)), sigma, opacity)
    groups = store.summaries()
    cumulative = {"name":"Historical total", "records":[], "grids":{}}
    for group in groups.values():
        cumulative["records"].extend(group["records"])
        for key, grid in group["grids"].items():
            cumulative["grids"][key] = cumulative["grids"].get(key, np.zeros_like(grid)) + grid
    output.mkdir(parents=True, exist_ok=True)
    views = []
    for event, group in [("all", cumulative)] + sorted(groups.items(), key=lambda pair: (pair[1]["date"] or "", pair[0]), reverse=True):
        view = {"id":event, "name":group["name"], "date":group.get("date"), "demo_count":len(group["records"]), "images":[]}
        for (map_name, layer), grid in sorted(group["grids"].items()):
            image = f"images/{event}-{map_name}-{layer}.png"
            seconds = round(int(grid.sum()) * SAMPLE_INTERVAL, 1)
            render_grid(grid, Path(maps[map_name]["radars"][layer]), output / image,
                        f"{map_name.upper()} / {layer} / {seconds:,.1f} CT player-seconds", sigma, opacity)
            view["images"].append({"map":map_name, "layer":layer, "url":image,
                                   "samples":int(grid.sum()), "player_seconds":seconds})
        views.append(view)
    dated = {event: group for event, group in groups.items() if group["date"]}
    latest = max(dated, key=lambda event: (dated[event]["date"], event)) if dated else None
    index = {"updated_at":datetime.now(timezone.utc).isoformat(), "policy":POLICY,
             "sample_interval":SAMPLE_INTERVAL, "sigma":sigma, "opacity":opacity,
             "latest_event":latest, "views":views,
             "coverage":"仅统计手动导入的 demo，不代表赛事已完整收集"}
    write_json(output / "index.json", index)
    return index
