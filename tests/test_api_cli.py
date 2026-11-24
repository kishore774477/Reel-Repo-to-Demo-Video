import time

import pytest
from fastapi.testclient import TestClient

from reel import server
from reel.cli import main


@pytest.fixture()
def client():
    app = server.create_app(precompute=False)
    with TestClient(app) as c:
        yield c


def test_app_starts_fast_without_blocking_on_a_video(client):
    m = client.get("/api/meta").json()
    assert m["rendering"] is False
    sb = client.get("/api/storyboard").json()
    assert sb["video_path"] is None and sb["backend"] is None and len(sb["storyboard"]["scenes"]) > 0


def test_build_with_render_true_produces_a_video(client):
    r = client.post("/api/build", json={"seconds": 15, "render": True}).json()
    assert r["backend"] in ("mp4", "gif") and r["video_path"]
    v = client.get("/api/video")
    assert v.status_code == 200 and v.headers["content-type"] in ("video/mp4", "image/gif")


def test_build_with_render_false_has_no_video(client):
    r = client.post("/api/build", json={"seconds": 15, "render": False}).json()
    assert r["backend"] is None and r["video_path"] is None
    assert client.get("/api/video").status_code == 404


def test_build_validates_inputs(client):
    assert client.post("/api/build", json={"seconds": 1}).status_code == 400
    assert client.post("/api/build", json={"seconds": 1000}).status_code == 400
    assert client.post("/api/build", json={"max_screenshots": 99}).status_code == 400
    assert client.post("/api/build", json={"repo": "C:/definitely/not/a/real/path"}).status_code == 400


def test_frame_endpoint_and_bounds(client):
    f = client.get("/api/frame/0")
    assert f.status_code == 200 and f.headers["content-type"] == "image/png"
    assert client.get("/api/frame/999").status_code == 404


def test_reset_restores_the_sample(client):
    client.post("/api/build", json={"seconds": 20, "cta_text": "custom"})
    r = client.post("/api/reset").json()
    assert r["repo"] == "sample_repo" and r["storyboard"]["scenes"][-1]["body"] != "custom"


def test_background_precompute_eventually_produces_a_video():
    app = server.create_app(precompute=True)
    with TestClient(app) as c:
        deadline = time.time() + 60
        backend = None
        while time.time() < deadline:
            m = c.get("/api/meta").json()
            if not m["rendering"]:
                backend = c.get("/api/storyboard").json()["backend"]
                if backend:
                    break
            time.sleep(1)
        assert backend in ("mp4", "gif")


def test_dashboard_is_served(client):
    assert "Reel" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200 and client.get("/static/style.css").status_code == 200


# ---------------------------------------------------------------------------- CLI
def test_cli_demo_script_only(capsys):
    main(["demo", "--out", "out_cli_test", "--seconds", "20"])
    out = capsys.readouterr().out
    assert "Pathfinder" in out and "scenes" in out
    import shutil
    shutil.rmtree("out_cli_test", ignore_errors=True)


def test_cli_build_script_only(capsys, sample_repo, tmp_path):
    main(["build", str(sample_repo), "--out", str(tmp_path / "o"), "--script-only"])
    out = capsys.readouterr().out
    assert "no video rendered" in out
    assert (tmp_path / "o" / "frames").exists()


def test_cli_build_missing_repo_exits_cleanly(tmp_path):
    with pytest.raises(SystemExit):
        main(["build", str(tmp_path / "missing"), "--out", str(tmp_path / "o")])
