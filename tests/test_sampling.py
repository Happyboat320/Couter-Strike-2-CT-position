"""采样边界回归：下包排除、未下包到回合结束、无效回合过滤。"""
import pandas as pd
import numpy as np
from cs_heatmap.parser import sampling_plan, infer_tick_rate
from cs_heatmap.aggregate import make_grids


def events(reason="bomb_defused"):
    return {
        "round_start": pd.DataFrame({"tick": [0, 5000], "is_warmup_period": [False, False]}),
        "round_freeze_end": pd.DataFrame({"tick": [640, 5640], "is_warmup_period": [False, False]}),
        "round_end": pd.DataFrame({"tick": [3000, 8000], "reason": [reason, "t_killed"]}),
        "bomb_planted": pd.DataFrame({"tick": [1920]}),
    }


def test_preplant_excludes_plant_tick():
    plan = sampling_plan(events(), 64)
    first = plan[plan["round"] == 1]
    assert first.tick.tolist() == [round(640 + (10 + step * .2) * 64) for step in range(50)]
    assert len(first) == 50
    assert np.allclose(first.elapsed_seconds, 10 + np.arange(50) * .2)
    assert set(np.diff(first.tick)) == {12, 13}
    assert first.tick.is_unique
    assert np.max(np.abs(first.tick - first.freeze_tick - first.elapsed_seconds * 64)) <= .5
    assert plan[plan["round"] == 2].tick.max() < 8000


def test_restart_and_warmup_excluded():
    e = events("game_commencing")
    assert sampling_plan(e, 64)["round"].unique().tolist() == [2]
    e["round_start"].loc[1, "is_warmup_period"] = True
    assert sampling_plan(e, 64).empty


def test_missing_round_end_excluded():
    e = events()
    e["round_end"] = e["round_end"].iloc[:1]
    assert sampling_plan(e, 64)["round"].unique().tolist() == [1]


def test_tick_rate_clock():
    assert infer_tick_rate({"round_end":pd.DataFrame({"tick":[0,640,1280],"game_time":[5.,15.,25.]})}) == 64


def test_nuke_layers_and_outside():
    samples = pd.DataFrame({"X":[10,10,-10],"Y":[-10,-10,-10],"Z":[0,-500,0]})
    grids, outside = make_grids(samples,{"pos_x":0,"pos_y":0,"scale":1,"lower_level_max_units":-495})
    assert grids["upper"].sum() == grids["lower"].sum() == 1
    assert outside == 1
