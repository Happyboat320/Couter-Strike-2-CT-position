"""对已解压的职业 demo 做窗口断言并输出 Parquet、网格与 PNG。

uv run scripts/validate_local.py data/validation/demos
"""
import argparse
import time
from pathlib import Path
import numpy as np
from cs_heatmap.parser import parse_demo
from cs_heatmap.aggregate import make_grids
from cs_heatmap.render import render_grid
from cs_heatmap.config import load_maps, write_json, SAMPLE_INTERVAL, POLICY

p = argparse.ArgumentParser()
p.add_argument("directory", type=Path)
p.add_argument("--output", type=Path, default=Path("data/validation"))
args = p.parse_args()
maps = load_maps()
report = []
for path in sorted(args.directory.glob("*.dem")):
    start = time.monotonic()
    parsed = parse_demo(path)
    elapsed = time.monotonic() - start
    if parsed.map_name not in maps:
        print("跳过白名单外地图:", path.name, parsed.map_name)
        continue
    frame = parsed.samples
    assert frame.team_num.eq(3).all() and frame.is_alive.all()
    assert frame.elapsed_seconds.ge(10).all()
    assert frame.tick.lt(frame.stop_tick).all()
    assert not frame.duplicated(["tick", "steamid"]).any()
    assert (np.abs((frame.tick-frame.freeze_tick) - frame.elapsed_seconds*parsed.tick_rate) <= 0.5 + 1e-9).all()
    data_dir = args.output / "samples"
    data_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(data_dir / (path.stem + ".parquet"), index=False)
    config = maps[parsed.map_name]
    grids, outside = make_grids(frame, config)
    np.savez_compressed(data_dir / (path.stem + ".npz"), **grids)
    layers = {}
    for layer, grid in grids.items():
        dest = args.output / "images" / f"{path.stem}-{layer}.png"
        render_grid(grid, Path(config["radars"][layer]), dest,
                    f"{parsed.map_name.upper()} / {layer} / {grid.sum()*SAMPLE_INTERVAL:.1f} CT player-seconds")
        layers[layer] = {"samples":int(grid.sum()), "player_seconds":round(float(grid.sum())*SAMPLE_INTERVAL, 1), "image":str(dest)}
    item = {"file":path.name, "map":parsed.map_name, "rounds":int(parsed.rounds),
            "samples":len(frame), "sample_interval":SAMPLE_INTERVAL, "policy":POLICY, "tick_rate":parsed.tick_rate,
            "parse_seconds":round(elapsed, 2), "demo_bytes":path.stat().st_size,
            "outside_radar_samples":outside, "layers":layers}
    report.append(item)
    print(item, flush=True)
write_json(args.output / "report.json", report)
