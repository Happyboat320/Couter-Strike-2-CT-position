"""自动归类仅使用确有依据的名称与日期，裸 demo 不虚构赛事。"""
from pathlib import Path
from cs_heatmap.metadata import identify_event, load_events


def test_hltv_original_archive():
    e = identify_event(Path('data/input/iem-cologne-major-2026-stage-2-astralis-vs-tyloo-nuke-id.rar'), load_events())
    assert e.id == 'cologne-major-2026'
    assert e.date == '2026-06-02'


def test_bare_demo_in_event_folder():
    e = identify_event(Path('data/input/esl-pro-league-season-24/team-vs-team-nuke.dem'), load_events())
    assert e.id == 'esl-pro-league-season-24'
    assert e.date == '2026-10-03'


def test_future_event_no_fake_date():
    e = identify_event(Path('data/input/iem-example-2027-team-vs-other-id.rar'), load_events())
    assert e.id == 'iem-example-2027'
    assert e.date is None


def test_unclassified_still_usable():
    e = identify_event(Path('data/input/team-vs-other-nuke.dem'), load_events())
    assert e.id == 'unclassified'
    assert e.date is None
