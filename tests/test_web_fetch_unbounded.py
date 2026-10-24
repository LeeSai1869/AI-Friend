from section_8_tools.web.web import WebFetch


class FetchResponse:
    encoding = "utf-8"
    headers = {"Content-Type": "text/plain"}

    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start:start + chunk_size]

    def close(self):
        pass


def test_unbounded_fetch_returns_more_than_one_mib_without_truncating(
    tmp_path,
    monkeypatch,
):
    content = "a" * (1024 * 1024 + 1)
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FetchResponse(content.encode("utf-8")),
    )

    result = WebFetch(tmp_path, None).call({
        "url": "https://example.test/lesson",
        "max_chars": None,
    })

    assert result["ok"]
    assert result["data"]["text"] == content
    assert result["data"]["chars"] == len(content)
    assert result["data"]["truncated"] is False


def test_fetch_keeps_default_preview_but_accepts_limits_above_old_cap(
    tmp_path,
    monkeypatch,
):
    content = "b" * 150_001
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FetchResponse(content.encode("utf-8")),
    )

    result = WebFetch(tmp_path, None).call({
        "url": "https://example.test/lesson",
        "max_chars": 150_001,
    })

    assert result["ok"]
    assert result["data"]["text"] == content
    assert result["data"]["truncated"] is False
