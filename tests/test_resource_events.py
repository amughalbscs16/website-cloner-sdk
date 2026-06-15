"""The SDK advertises per-resource events; verify download_file actually emits them."""
from src.utils.file_utils import FileManager
from src.downloaders.resource_downloader import ResourceDownloader
from src.events.event_emitter import EventEmitter, ClonerEvents


def _run(tmp_path, download_result):
    fm = FileManager(tmp_path)
    em = EventEmitter()
    got = {}
    for ev, key in [(ClonerEvents.RESOURCE_DISCOVERED, "disc"),
                    (ClonerEvents.RESOURCE_DOWNLOAD_SUCCESS, "ok"),
                    (ClonerEvents.RESOURCE_DOWNLOAD_FAILED, "fail"),
                    (ClonerEvents.STATS_UPDATE, "stats")]:
        em.on(ev, (lambda k: (lambda d: got.setdefault(k, []).append(d)))(key))
    dl = ResourceDownloader(fm, event_emitter=em)
    dl.download_resource = lambda url, **kw: download_result  # stub network
    proj = tmp_path / "proj"
    proj.mkdir()
    dl.download_file("https://x.test", "https://x.test/a.png", proj)
    return got


def test_success_emits_discovered_success_and_stats(tmp_path):
    got = _run(tmp_path, (b"PNGDATA", "cdp"))
    assert got.get("disc") and got["disc"][0].url.endswith("a.png")
    assert got.get("ok") and got["ok"][0].size_bytes == 7
    assert "fail" not in got
    assert got.get("stats") and got["stats"][-1].successful_downloads == 1


def test_failure_emits_failed_and_stats(tmp_path):
    got = _run(tmp_path, (None, None))
    assert got.get("disc")
    assert got.get("fail") and got["fail"][0].url.endswith("a.png")
    assert got.get("stats") and got["stats"][-1].failed_downloads == 1
