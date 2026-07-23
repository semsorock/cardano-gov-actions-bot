import json
from unittest.mock import MagicMock, patch

import requests

from bot.metadata.fetcher import fetch_metadata, sanitise_url


class TestSanitiseUrl:
    def test_ipfs_url(self):
        url = "ipfs://QmbhTQ9pcvAmBBHTFE4n78N9wPTykUdJkteVQ8gmvW53To"
        assert sanitise_url(url) == "https://ipfs.io/ipfs/QmbhTQ9pcvAmBBHTFE4n78N9wPTykUdJkteVQ8gmvW53To"

    def test_https_url_unchanged(self):
        url = "https://example.com/metadata.json"
        assert sanitise_url(url) == url

    def test_http_url_unchanged(self):
        url = "http://example.com/metadata.json"
        assert sanitise_url(url) == url


class TestFetchMetadata:
    @patch("bot.metadata.fetcher.requests.get")
    def test_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"body": {"title": "Test"}}
        mock_get.return_value = mock_response

        result = fetch_metadata("https://example.com/metadata.json")
        assert result == {"body": {"title": "Test"}}

    @patch("bot.metadata.fetcher.requests.get")
    def test_utf8_body_with_non_charset_content_type(self, mock_get):
        """UTF-8 JSON served as text/* (no charset) must not be mangled to Latin-1.

        Hosts like IPFS gateways serve JSON as text/plain without a charset, so
        requests defaults response.encoding to ISO-8859-1. Without forcing UTF-8,
        response.json() double-decodes non-ASCII characters into mojibake.
        """
        title = 'Name the Protocol Version 12 hard fork “von Bergen”'
        body = json.dumps({"body": {"title": title}}, ensure_ascii=False)

        response = requests.models.Response()
        response.status_code = 200
        response._content = body.encode("utf-8")
        response.headers["Content-Type"] = "text/plain"  # no charset
        # Mirror how requests populates encoding from the headers (-> ISO-8859-1).
        response.encoding = requests.utils.get_encoding_from_headers(response.headers)
        assert response.encoding == "ISO-8859-1"  # the condition that triggers the bug
        mock_get.return_value = response

        result = fetch_metadata("https://ipfs.io/ipfs/Qmwhatever")
        assert result == {"body": {"title": title}}

    @patch("bot.metadata.fetcher.requests.get")
    def test_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = fetch_metadata("https://example.com/missing.json")
        assert result is None

    @patch("bot.metadata.fetcher.requests.get")
    def test_exception(self, mock_get):
        mock_get.side_effect = ConnectionError("timeout")

        result = fetch_metadata("https://example.com/metadata.json")
        assert result is None
