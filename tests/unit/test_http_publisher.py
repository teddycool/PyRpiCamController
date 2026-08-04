"""Tests for the HttpPublisher lifecycle contract."""

from unittest.mock import Mock, patch

from Publishers.HttpPublisher import HttpPublisher


def test_publish_returns_true_for_successful_response():
    publisher = HttpPublisher("https://example.invalid/upload")
    response = Mock(status_code=204)

    with patch("Publishers.HttpPublisher.requests.post", return_value=response) as post:
        result = publisher.publish(Mock(tobytes=lambda: b"jpeg"), {"frame": 1})

    assert result is True
    post.assert_called_once()
    assert post.call_args.kwargs["timeout"] == 30


def test_publish_returns_false_for_failed_response():
    publisher = HttpPublisher("https://example.invalid/upload")

    with patch(
        "Publishers.HttpPublisher.requests.post",
        return_value=Mock(status_code=503),
    ):
        result = publisher.publish(Mock(tobytes=lambda: b"jpeg"))

    assert result is False


def test_cleanup_is_safe():
    publisher = HttpPublisher()
    assert publisher.cleanup() is None
