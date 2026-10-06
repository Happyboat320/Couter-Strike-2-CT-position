"""本地工具输入、增量去重和新旧口径隔离。"""
import bz2
from pathlib import Path
import zipfile
import numpy as np
import pytest
from cs_heatmap.inputs import demo_entries, input_files
from cs_heatmap.store import Store
from cs_heatmap.config import read_json, write_json


def test_archive_sequential_and_original_untouched(tmp_path):
    source = tmp_path / 'match.zip'
    with zipfile.ZipFile(source, 'w') as z:
        z.writestr('folder/one.dem', b'PBDEMS2\x00one')
        z.writestr('two.dem', b'PBDEMS2\x00two')
        z.writestr('ignore.txt', b'text')
    with demo_entries(source) as entries:
        iterator = iter(entries)
        first_name, first_path = next(iterator)
        assert first_name == 'one.dem' and first_path.exists()
        _, second_path = next(iterator)
        assert not first_path.exists() and second_path.exists()
        with pytest.raises(StopIteration): next(iterator)
        assert not second_path.exists()
    assert source.exists()


def test_bz2_and_directory(tmp_path):
    path = tmp_path / 'one.dem.bz2'
    path.write_bytes(bz2.compress(b'PBDEMS2\x00abc'))
    assert input_files([tmp_path, path]) == [path.resolve()]
    with demo_entries(path) as entries:
        name, output = next(entries)
        assert name == 'one.dem'
        assert output.read_bytes() == b'PBDEMS2\x00abc'
    assert not output.exists() and path.exists()


def test_store_no_double_count_and_policy_mismatch(tmp_path):
    state = tmp_path / 'state'
    store = Store(state, {})
    grid = np.ones((2, 2), dtype=np.uint64)
    record = {'event':'cologne', 'event_name':'Cologne', 'event_date':'2026-06-02', 'map':'dust2'}
    assert not store.contains('cologne', 'one.dem')
    store.save('cologne', 'one.dem', record, {'main':grid})
    assert store.contains('cologne', 'one.dem')
    assert store.summaries()['cologne']['grids'][('dust2','main')].sum() == 4
    assert len(list(store.records())) == 1
    config = read_json(state / 'config.json')
    config['policy'] = 'old-1s'
    write_json(state / 'config.json', config)
    with pytest.raises(ValueError, match='口径'):
        Store(state, {})


def test_publish_unknown_date_does_not_override_latest(tmp_path):
    from cs_heatmap.publish import publish
    from PIL import Image
    radar = tmp_path / 'radar.png'
    Image.new('RGB', (32, 32), 'white').save(radar)
    maps = {'dust2': {'radars': {'main':str(radar)}}}
    store = Store(tmp_path / 'state', maps)
    for event, date in [('known', '2026-06-02'), ('unknown', None)]:
        record = {'event':event, 'event_name':event, 'event_date':date, 'map':'dust2'}
        store.save(event, 'one.dem', record, {'main':np.ones((4, 4), dtype=np.uint64)})
    index = publish(store, maps, tmp_path / 'out')
    assert index['latest_event'] == 'known'
    assert index['views'][0]['demo_count'] == 2
