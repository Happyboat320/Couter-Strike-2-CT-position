"""真实 demo 解析；回放和热力图共用站位读取接口。"""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from demoparser2 import DemoParser
from .config import MAPS, SAMPLE_INTERVAL


@dataclass
class ParsedDemo:
    map_name: str
    samples: pd.DataFrame
    rounds: int
    tick_rate: float


def sampling_plan(events: dict[str, pd.DataFrame], tick_rate: float) -> pd.DataFrame:
    """以 round_start 分段，只有有 freeze_end 与正常结束的非热身回合有效。

    下一次 round_start 会截断异常回合；缺失结束的片段不参与统计。
    """
    starts = events["round_start"].sort_values("tick").drop_duplicates("tick")
    ends = events["round_end"]
    freezes = events["round_freeze_end"]
    plants = events.get("bomb_planted", pd.DataFrame(columns=["tick"]))
    plan = []
    boundaries = starts["tick"].tolist() + [np.iinfo(np.int64).max]
    for i, (_, row) in enumerate(starts.iterrows()):
        lo, hi = int(row["tick"]), boundaries[i + 1]
        if bool(row.get("is_warmup_period", False)):
            continue
        f = freezes[(freezes.tick >= lo) & (freezes.tick < hi)]
        e = ends[(ends.tick > lo) & (ends.tick < hi)]
        # 多次解冻通常属于重启/异常回合，不猜测其有效性。
        if len(f) != 1 or len(e) != 1 or bool(f.iloc[0].get("is_warmup_period", False)):
            continue
        end = int(e.iloc[0].tick)
        if "reason" in e and e.iloc[0]["reason"] in (
            0, "0", "unknown", "game_start", "game_commencing", "round_draw", "draw", "restart"
        ):
            continue
        planted = plants[(plants.tick >= int(f.iloc[0].tick)) & (plants.tick <= end)]
        stop = min(end, int(planted.tick.min())) if len(planted) else end
        freeze = int(f.iloc[0].tick)
        step = 0
        # 以整数采样序号算目标时间，避免浮点累加漂移。
        # 64 tick/s 下 0.2 秒不是整数 tick，间距按最近 tick 在 12/13 之间交替。
        while True:
            second = 10 + step * SAMPLE_INTERVAL
            tick = int(round(freeze + second * tick_rate))
            if tick >= stop:
                break
            plan.append((tick, i + 1, second, freeze, stop))
            step += 1
    return pd.DataFrame(plan, columns=["tick", "round", "elapsed_seconds", "freeze_tick", "stop_tick"])


def infer_tick_rate(events: dict[str, pd.DataFrame]) -> float:
    """从 demo 的游戏时钟校验 tick 频率，不以头部录像时长推测。"""
    frames = [f[["tick", "game_time"]] for f in events.values() if "game_time" in f]
    if not frames:
        raise ValueError("demo 缺少 game_time，不能可靠确定采样频率")
    clock = pd.concat(frames).dropna().sort_values("tick").drop_duplicates("tick")
    dt = clock.game_time.diff()
    ratios = clock.tick.diff()[dt > 0.25] / dt[dt > 0.25]
    if ratios.empty:
        raise ValueError("有效游戏时钟不足")
    rate = float(ratios.median())
    # CS2 GOTV 通常为 64；容忍浮点误差，但不能静默采用错误频率。
    rounded = round(rate)
    if not 16 <= rounded <= 128 or abs(rate - rounded) > 0.1:
        raise ValueError(f"不支持的 tick rate: {rate}")
    return float(rounded)


def positions(parser: DemoParser, ticks: list[int], replay=False) -> pd.DataFrame:
    """预留回放入口：返回所有选手位置、队伍、存活状态和朝向。"""
    props = ["X", "Y", "Z", "team_num", "is_alive", "is_warmup_period"]
    if replay:
        props += ["yaw", "pitch"]
    return parser.parse_ticks(props, ticks=ticks)


def parse_demo(path: Path) -> ParsedDemo:
    with path.open("rb") as file:
        if file.read(8) != b"PBDEMS2\x00":
            raise ValueError(f"不是 CS2 demo（可能下载到了 HTML）：{path}")
    parser = DemoParser(str(path))
    map_name = parser.parse_header()["map_name"].removeprefix("de_")
    if map_name not in MAPS:
        return ParsedDemo(map_name, pd.DataFrame(), 0, 0)
    names = ["round_start", "round_freeze_end", "round_end", "bomb_planted"]
    events = dict(parser.parse_events(names, other=["game_time", "is_warmup_period"]))
    for name in names:
        events.setdefault(name, pd.DataFrame(columns=["tick"]))
    rate = infer_tick_rate(events)
    plan = sampling_plan(events, rate)
    if plan.empty:
        raise ValueError("未找到有效防守窗口，不能将空结果标记为成功")
    frame = positions(parser, plan.tick.tolist())
    frame = frame[(frame.team_num == 3) & frame.is_alive.eq(True) & frame.is_warmup_period.eq(False)]
    frame = frame.dropna(subset=["X", "Y", "Z", "steamid"])
    frame = frame.merge(plan, on="tick", how="inner", validate="many_to_one")
    frame = frame.drop_duplicates(["tick", "steamid"])
    frame["sample_seconds"] = SAMPLE_INTERVAL
    if frame.empty:
        raise ValueError("有效窗口中没有存活 CT 样本")
    return ParsedDemo(map_name, frame, plan["round"].nunique(), rate)
