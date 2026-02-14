from unittest.mock import MagicMock, patch

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
