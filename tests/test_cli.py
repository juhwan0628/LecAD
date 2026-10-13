from lecad.cli import _filter_ai_range


def test_filter_ai_range_limits_deictic_events_and_contexts():
    manifest = {
        "events": [
            {"type": "slide_change", "timestamp_s": 1},
            {"id": "a", "type": "deictic", "insertion_timestamp_s": 10},
            {"id": "b", "type": "deictic", "insertion_timestamp_s": 20},
        ]
    }
    contexts = [{"id": "a"}, {"id": "b"}]
    out_manifest, out_contexts = _filter_ai_range(manifest, contexts, 15, 25)
    assert [e.get("id") for e in out_manifest["events"]] == ["b"]
    assert [c["id"] for c in out_contexts] == ["b"]


def test_cli_honors_provider_environment(tmp_path, monkeypatch):
    import json
    from lecad.cli import main
    manifest = tmp_path / "manifest.json"
    contexts = tmp_path / "contexts.json"
    manifest.write_text('{"events": []}')
    contexts.write_text('[]')
    monkeypatch.setenv("LECAD_PROVIDER", "mock")
    assert main(["--enrich-manifest", str(manifest), "--contexts", str(contexts),
                 "--output-dir", str(tmp_path), "--env-file", str(tmp_path / "missing.env")]) == 0
    out = json.loads((tmp_path / "manifest.approved.json").read_text())
    assert out["generation"]["vision_provider"] == "MockVisionProvider"
