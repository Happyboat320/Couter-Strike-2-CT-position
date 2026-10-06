"""默认一键扫描 data/input，自动归类；仅 render 的高级参数可选。"""
import argparse
from pathlib import Path
import sys
import time
from .aggregate import make_grids
from .config import load_maps, SAMPLE_INTERVAL, POLICY, write_json
from .inputs import input_files, demo_entries
from .metadata import identify_event, load_events
from .parser import parse_demo
from .publish import publish
from .store import Store


def main():
    parser = argparse.ArgumentParser(description="将 HLTV demo 放到 data/input 后运行，自动生成热力图")
    parser.add_argument("command", choices=["generate", "render"], nargs="?", default="generate")
    parser.add_argument("--input", type=Path, default=Path("data/input"))
    parser.add_argument("--state", type=Path, default=Path("results/state"))
    parser.add_argument("--output", type=Path, default=Path("frontend/public/data"))
    parser.add_argument("--maps", type=Path, default=Path("config/maps.json"))
    parser.add_argument("--sigma", type=float, default=2.5)
    parser.add_argument("--opacity", type=float, default=0.5)
    parser.add_argument("--save-samples", type=Path, help="可选输出原始 Parquet，默认不保存大量坐标")
    args = parser.parse_args()
    failures = []
    try:
        maps = load_maps(args.maps)
        store = Store(args.state, maps)
        if args.command == "generate":
            args.input.mkdir(parents=True, exist_ok=True)
            sources = input_files([args.input])
            catalog = load_events()
            if not sources:
                raise ValueError(f"请先把 .dem / .dem.bz2 / .rar / .zip 放到 {args.input}")
            for source in sources:
                event = identify_event(source, catalog)
                print(f"输入: {source.name} → {event.name}", flush=True)
                try:
                    with demo_entries(source) as entries:
                        seen = False
                        for name, path in entries:
                            seen = True
                            if store.contains(event.id, name):
                                print("已处理，跳过:", name, flush=True)
                                continue
                            try:
                                started = time.monotonic()
                                parsed = parse_demo(path)
                                if parsed.map_name not in maps:
                                    print("白名单外地图，跳过:", name, parsed.map_name, flush=True)
                                    continue
                                grids, outside = make_grids(parsed.samples, maps[parsed.map_name])
                                record = {"event":event.id, "event_name":event.name,
                                          "event_date":event.date, "event_source":event.source, "demo":name,
                                          "map":parsed.map_name, "rounds":int(parsed.rounds),
                                          "samples":len(parsed.samples), "outside_radar_samples":outside,
                                          "sample_interval":SAMPLE_INTERVAL, "policy":POLICY,
                                          "tick_rate":parsed.tick_rate, "source_archive":source.name,
                                          "parse_seconds":round(time.monotonic()-started, 3)}
                                if args.save_samples:
                                    folder = args.save_samples / event.id
                                    folder.mkdir(parents=True, exist_ok=True)
                                    parsed.samples.to_parquet(folder / (Path(name).stem+".parquet"), index=False)
                                store.save(event.id, name, record, grids)
                                print("已解析:", name, "CT 样本:", len(parsed.samples), "越界:", outside, flush=True)
                            except Exception as exc:
                                failures.append({"input":str(source), "demo":name, "error":str(exc)})
                                print("解析失败:", name, str(exc), file=sys.stderr, flush=True)
                        if not seen:
                            raise ValueError("压缩包中没有 .dem")
                except Exception as exc:
                    failures.append({"input":str(source), "error":str(exc)})
                    print("输入失败:", source, str(exc), file=sys.stderr, flush=True)
            write_json(args.state / "last-run.json", {"failures":failures})
        index = publish(store, maps, args.output, args.sigma, args.opacity)
        print("已输出:", args.output, "最新已知赛事:", index["latest_event"], flush=True)
        return 1 if failures else 0
    except (ValueError, OSError) as exc:
        print("错误:", str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
