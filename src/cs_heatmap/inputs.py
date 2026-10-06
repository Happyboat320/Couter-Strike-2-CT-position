"""手动输入 .dem / .dem.bz2 / RAR / ZIP，逐个释放临时 demo。"""
import bz2
from contextlib import contextmanager
from pathlib import Path
import shutil
import tempfile
import zipfile
import rarfile

SUPPORTED = (".dem", ".dem.bz2", ".rar", ".zip")


def input_files(paths: list[Path]):
    found = []
    for path in paths:
        if path.is_dir():
            found.extend(p for p in sorted(path.rglob("*")) if p.is_file() and p.name.lower().endswith(SUPPORTED))
        elif path.is_file() and path.name.lower().endswith(SUPPORTED):
            found.append(path)
        else:
            raise ValueError(f"输入不存在或格式不支持: {path}")
    return list(dict.fromkeys(p.resolve() for p in found))


@contextmanager
def demo_entries(source: Path):
    """返回 (demo 文件名, 临时路径) 迭代器。不会删除或改写用户原始文件。"""
    name = source.name.lower()
    if name.endswith(".dem"):
        yield iter([(source.name, source)])
        return
    with tempfile.TemporaryDirectory(prefix="cs-demo-") as directory:
        folder = Path(directory)
        if name.endswith(".dem.bz2"):
            def single():
                target = folder / source.name[:-4]
                with bz2.open(source, "rb") as stream:
                    _copy(stream, target)
                yield target.name, target
            yield single()
        else:
            opener = rarfile.RarFile if name.endswith(".rar") else zipfile.ZipFile
            with opener(source) as archive:
                def unpack():
                    for info in archive.infolist():
                        if info.is_dir() or not info.filename.lower().endswith(".dem"):
                            continue
                        # 用 basename 避免保留压缩包内部目录结构；每次只保留一个 demo。
                        target = folder / Path(info.filename).name
                        with archive.open(info) as stream:
                            _copy(stream, target, info.file_size)
                        try:
                            yield target.name, target
                        finally:
                            target.unlink(missing_ok=True)
                yield unpack()


def _copy(stream, target: Path, size: int | None = None):
    reserve = 512 * 1024 * 1024
    if size is not None and shutil.disk_usage(target.parent).free < size + reserve:
        raise OSError("解压空间不足：需要 demo 大小加 512 MiB 余量")
    with target.open("wb") as output:
        while block := stream.read(1024 * 1024):
            if shutil.disk_usage(target.parent).free < len(block) + reserve:
                raise OSError("解压过程中剩余空间不足")
            output.write(block)
