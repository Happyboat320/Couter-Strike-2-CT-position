"""将世界坐标映射到雷达网格；保留原始计数而不是叠加 PNG。"""
import numpy as np
import pandas as pd


def make_grids(samples: pd.DataFrame, config: dict, bins=256):
    x = (samples.X.to_numpy() - config["pos_x"]) / config["scale"]
    y = (config["pos_y"] - samples.Y.to_numpy()) / config["scale"]
    extent = config.get("resolution", 1024)
    inside = (x >= 0) & (x < extent) & (y >= 0) & (y < extent)
    masks = {"main": np.ones(len(samples), dtype=bool)}
    if "lower_level_max_units" in config:
        lower = samples.Z.to_numpy() < config["lower_level_max_units"]
        masks = {"upper": ~lower, "lower": lower}
    grids = {}
    for layer, mask in masks.items():
        take = inside & mask
        grid, _, _ = np.histogram2d(y[take], x[take], bins=bins, range=[[0, extent], [0, extent]])
        grids[layer] = grid.astype(np.uint64)
    return grids, int((~inside).sum())
