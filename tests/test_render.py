"""验证连续密度、透明度边界及显示不修改原始聚合。"""
import numpy as np
import pytest
from cs_heatmap.render import smooth_density, heatmap_rgba


def test_smoothing_continuous_and_preserves_counts():
    grid = np.zeros((64, 64), dtype=np.uint64)
    grid[32, 32] = 100
    original = grid.copy()
    density = smooth_density(grid)
    assert density[32, 31] > 0
    assert density[32, 32] > density[32, 31] > density[32, 27]
    assert density.sum() == pytest.approx(20)
    np.testing.assert_array_equal(original, grid)


def test_overlay_never_obscures_radar():
    grid = np.zeros((64, 64))
    grid[32, 32] = 1
    rgba = heatmap_rgba(grid, opacity=.45)
    assert rgba[..., 3].max() <= .45
    assert rgba[0, 0, 3] == 0
    assert 0 < rgba[32, 27, 3] < rgba[32, 32, 3]
    assert heatmap_rgba(np.zeros((4, 4)))[..., 3].sum() == 0


@pytest.mark.parametrize('opacity', [0, 1, float('nan')])
def test_invalid_opacity(opacity):
    with pytest.raises(ValueError):
        heatmap_rgba(np.zeros((4, 4)), opacity=opacity)
