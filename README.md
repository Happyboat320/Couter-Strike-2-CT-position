# CS2 CT 防守站位解析工具

将从 HLTV 手动下载的 demo 放到 `data/input/`，运行一条命令，自动生成雷达底图上的连续半透明热力图。无需填写地图、队伍、赛事参数。

维护者 Pages：`https://happyboat.tech/Couter-Strike-2-CT-position/`。展示手动导入的科隆 Major 及后续赛事样本，不代表完整赛事覆盖。仓库是通用本地解析工具，不自动抓取 HLTV。

## 快速开始

需要 **Python 3.11+、uv**。解析 `.rar` 还需 `unrar`（Ubuntu/Debian：`sudo apt-get install unrar`）。

```bash
git clone https://github.com/Happyboat320/Couter-Strike-2-CT-position.git
cd Couter-Strike-2-CT-position
uv sync --frozen
```

Python 依赖使用中科大镜像，版本由 `uv.lock` 锁定。

1. 浏览器打开 HLTV 比赛页，下载 GOTV demo。
2. 把下载的原始包直接放进 `data/input/`，**保留原始文件名**。
3. 从仓库根目录运行：

```bash
uv run cs-heatmap
```

支持 `.dem`、`.dem.bz2`、`.rar`、`.zip`，也递归扫描子目录。无需预先解压，原始文件不会被删除。RAR/ZIP 每次只解压一个地图 demo，处理后清理临时文件，并检查磁盘剩余空间。

生成结果：

```text
frontend/public/data/
  index.json               页面数据与样本覆盖索引
  images/all-*.png          历史总和热力图
  images/<赛事>-*.png        各赛事热力图
results/state/              本地增量状态，需自行备份
```

加入新包后再运行同一命令。以 **赛事标识 + demo 文件名** 去重，已处理的 demo 不重复累计。不要把相同 demo 改名后重复导入，也不要同时提供压缩包及其改名后的解压版本。

### 自动识别的边界

- **地图、回合、CT 队伍、存活状态、tick 频率**由 demo 内容读取。
- HLTV demo 头部通常只有地图与服务器名称，**不含完整赛事名称或日历日期**。因此赛事使用原始 HLTV 包名/父目录名识别，已知名称与开始日期来自 `config/events.json`。
- 当前目录包含科隆 Major 2026 和 EPL S24 的别名与开始日期。后续原始包名包含 `赛事-2026` 或 `赛事-season-N` 时可自动归类，即使尚未登记也能解析，但开始日期显示未知，不参与“最新已知赛事”的排序。
- 裸 `.dem` 若无法识别赛事会归入“未识别赛事”，**仍正常产生热力图**；要保留赛事分组，可将其放到以原始赛事命名的子目录，或直接保留原始下载包。
- 工具不会拿文件修改时间当比赛日期。维护者可更新 `config/events.json`，普通使用者不需要填写运行参数。

## 统计与显示

- 冻结结束后 **10 秒**开始，每 **0.2 秒**采样，仅记录当时属于 CT 且存活的选手。
- 下包完成时及以后不计入；没有下包则采样到回合结束之前。
- 包括手枪局、经济局和加时；排除热身、缺失有效结束及识别出的重启回合。
- 固定七图：Dust2、Mirage、Inferno、Ancient、Cache、Anubis、Nuke；Overpass 排除。
- Nuke 分上下层，Z < -495 为下层。
- 0.2 秒在 64 tick/s 下为 12.8 tick：取最近 tick，间距交替为 12/13 tick，最大舍入误差半个 tick。
- 原始网格保存采样数，**选手秒 = 采样数 × 0.2**。高斯平滑只作用于显示，不改变计数；颜色是本图相对强度，不支持跨图绝对颜色比较。
- 默认最大不透明度 **0.5**，低密度渐隐，底图始终可见。默认 sigma 为 2.5 个网格格数（约 10 雷达像素）。

只调整透明度与连续程度，无需重新解析：

```bash
uv run cs-heatmap render --opacity 0.4 --sigma 3
```

可选高级参数，不影响默认一键使用：

```bash
# 原始采样点输出 Parquet
uv run cs-heatmap --save-samples data/samples
# 独立数据集；不覆盖克隆来的维护者发布结果
uv run cs-heatmap --state results/my-state --output results/my-images
```

默认克隆用户从空状态解析自己的数据；默认生成会替换本地页面索引，不混入维护者计数。旧 1 秒样本不能和 0.2 秒样本混合，口径不一致会报错，需使用新状态目录重新解析。失败项保存在 `results/state/last-run.json`，成功项保留，修复后重跑。

## 本地浏览页面

仅生成 PNG 不需要 Node.js。React 页面需要 **Node.js 22.12+**：

```bash
cd frontend
npm ci --registry=https://registry.npmmirror.com
npm run dev
```

打开终端显示的地址，加上 `/Couter-Strike-2-CT-position/` 路径。页面可切换历史总和和各赛事，按已知开始日期标记最新赛事。

```bash
npm run build
npm run preview
```

克隆用户部署到其他仓库时，设置 `VITE_BASE=/你的仓库名/`；根域部署设置 `/`。

## GitHub Pages 发布

1. 本地一键解析并查看结果。
2. 提交源码和 `frontend/public/data/` 中 PNG/JSON；demo、Parquet、增量状态及缓存由 `.gitignore` 排除。
3. 仓库 Settings → Pages → Source 选择 **GitHub Actions**。
4. 推送 main 后，`.github/workflows/pages.yml` 构建并发布 React 静态页面，亦可手动触发。云端不下载、不解析 demo，没有 cron。
5. 本项目不设置 Custom domain 或 CNAME；用户主页配置了 `happyboat.tech` 后，项目路径继承该域名，主站与项目独立部署。

**请备份 `results/state/`**，换电脑时复制它才能继续增量累计。PNG/JSON 不是累加状态，也不能恢复历史贡献。

## 项目结构

```text
src/cs_heatmap/
  cli.py        默认一键入口
  metadata.py   自动赛事归类，不虚构缺失日期
  inputs.py     本地输入、逐 demo 解压、磁盘检查
  parser.py     回合识别与存活 CT 采样；预留回放 positions 接口
  aggregate.py  坐标变换、Nuke 分层、计数网格
  store.py      持久化贡献与增量去重
  render.py     连续密度、半透明 PNG
  publish.py    汇总与静态索引
config/          地图校准、赛事目录
assets/radars/   雷达底图与来源
frontend/        React 简单展示页及发布图片
scripts/         真实 demo 验收
```

未来可用 `parser.positions(..., replay=True)` 获取选手位置、队伍、存活状态和朝向；本次不实现网页上传或回放服务。

## 验证

```bash
uv sync --frozen --extra test
uv run pytest -q
# 已解压的真实 demo 验收
uv run scripts/validate_local.py data/validation/demos --output data/validation/0.2s
```

真实样本验收记录见 `docs/local-validation.json`；已导入总数和地图覆盖见发布索引。

## 已知限制

- 简单高斯平滑不理解墙体，会略跨越墙壁，仅是显示效果。
- Cache 尚无本地真实样本验证；地图版本变化需更新底图、坐标并重新解析。
- 相同 demo 改名后无法按文件名去重；同名不同 demo 应使用稳定唯一名称。
- 状态目录仅支持单个写进程；异常录制、回滚的比赛仍需人工确认。
- 赛事目录新增/修改后，已有状态记录不会自动迁移；用新 `--state` 重建以更新分组或日期。
