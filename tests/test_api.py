from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_ok():
    res = client.get("/")
    assert res.status_code == 200
    assert "Interview" in res.text


def test_providers_lists_mock():
    res = client.get("/providers")
    assert res.status_code == 200
    names = {p["name"] for p in res.json()}
    assert "mock" in names


def test_generate_returns_table_and_downloads(sample_jd):
    res = client.post("/generate", data={"jd": sample_jd, "provider": "mock"})
    assert res.status_code == 200, res.text
    payload = res.json()

    # Three downloadable formats.
    assert {f["label"] for f in payload["files"]} == {
        "Table — Markdown", "Table — CSV", "Table — HTML",
    }
    # Preview carries mapped rows, none of them degree/years bars.
    rows = payload["preview"]["rows"]
    assert rows
    joined = " ".join(r["requirement"].lower() for r in rows)
    assert "bachelor" not in joined

    # Each download is actually served.
    for f in payload["files"]:
        dl = client.get(f["url"])
        assert dl.status_code == 200
        assert dl.content


def test_generate_with_instructions_returns_schedule(sample_jd):
    res = client.post("/generate", data={
        "jd": sample_jd, "provider": "mock", "instructions": "1 week to prepare",
    })
    assert res.status_code == 200, res.text
    preview = res.json()["preview"]
    # A pacing summary and a per-row study window come back in the preview.
    assert preview["guidance"]
    assert all(r["timebox"] for r in preview["rows"])


def test_generate_qualifications_only_is_400():
    jd = "Bachelor's degree required.\n5+ years of experience required.\n"
    res = client.post("/generate", data={"jd": jd, "provider": "mock"})
    assert res.status_code == 400


def test_download_rejects_bad_job_id():
    assert client.get("/download/not-a-job-id/x.md").status_code == 404
