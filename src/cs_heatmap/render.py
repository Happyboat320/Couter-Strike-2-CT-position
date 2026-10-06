"""连续、半透明热力图。平滑仅用于显示，不改变持久化的采样计数。"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from .config import SAMPLE_INTERVAL


def smooth_density(grid: np.ndarray, sigma: float = 2.5) -> np.ndarray:
    """可分离高斯卷积；sigma 的单位是网格格数，256 格时默认约 10 雷达像素。"""
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("sigma 必须是正数")
    radius = int(np.ceil(4 * sigma))
    offsets = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
    kernel /= kernel.sum()
    density = grid.astype(float) * SAMPLE_INTERVAL
    # 对称边界让地图边缘的密度不因卷积丢失；不在不同层之间平滑。
    for axis in (0, 1):
        pads = [(0, 0), (0, 0)]
        pads[axis] = (radius, radius)
        padded = np.pad(density, pads, mode="symmetric")
        density = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="valid"), axis, padded)
    return density


def heatmap_rgba(grid: np.ndarray, sigma: float = 2.5, opacity: float = 0.5):
    """低密度渐隐，高密度也不超过指定透明度，始终能看见底图。"""
    if not np.isfinite(opacity) or not 0 < opacity < 1:
        raise ValueError("opacity 必须在 0 与 1 之间，不允许完全遮挡底图")
    density = smooth_density(grid, sigma)
    positive = density[density > 0]
    rgba = np.zeros((*density.shape, 4))
    if positive.size:
        # 99 分位压缩极端热点；色标是本图内相对强度，不用于跨图绝对比较。
        high = float(np.percentile(positive, 99))
        scaled = np.clip(np.log1p(density / high * 20) / np.log1p(20), 0, 1)
        rgba = matplotlib.colormaps["turbo"](scaled)
        rgba[..., 3] = opacity * scaled ** 0.65
    return rgba


def render_grid(grid: np.ndarray, radar: Path, target: Path, title: str,
                sigma: float = 2.5, opacity: float = 0.5):
    if not radar.exists():
        raise FileNotFoundError(f"缺少真实雷达底图: {radar}")
    image = plt.imread(radar)
    rgba = heatmap_rgba(grid, sigma, opacity)
    fig, ax = plt.subplots(figsize=(8, 8), dpi=160)
    ax.set_facecolor("#182026")
    ax.imshow(image, extent=(0, 1024, 1024, 0))
    ax.imshow(rgba, extent=(0, 1024, 1024, 0), origin="upper", interpolation="bilinear")
    ax.set_xlim(0, 1024)
    ax.set_ylim(1024, 0)
    ax.set_title(title, fontsize=11)
    ax.axis("off")
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, bbox_inches="tight", facecolor="white")
    plt.close(fig)
