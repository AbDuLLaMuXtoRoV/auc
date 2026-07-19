"""Push provayderi abstraksiyasi testlari — DB kerak emas (sof birlik testlari)."""

import pytest

from app.services.push_provider import (
    BasePushProvider,
    LogPushProvider,
    NullPushProvider,
    PushProviderError,
    PushResult,
    available_provider_names,
    get_push_provider,
)


def test_log_provider_send_delivered():
    result = LogPushProvider().send(user_id=1, title="X", body="Y", data={"a": 1})
    assert isinstance(result, PushResult)
    assert result.delivered is True
    assert result.message_id.startswith("log_")


def test_log_provider_body_and_data_optional():
    result = LogPushProvider().send(user_id=1, title="X", body=None, data=None)
    assert result.delivered is True
    assert result.message_id.startswith("log_")


def test_get_push_provider_returns_log_instance():
    provider = get_push_provider("log")
    assert isinstance(provider, LogPushProvider)


def test_get_push_provider_returns_null_instance():
    provider = get_push_provider("null")
    assert isinstance(provider, NullPushProvider)
    assert provider.send(user_id=1, title="X", body=None, data=None).delivered is False


def test_get_push_provider_unknown_raises():
    with pytest.raises(PushProviderError):
        get_push_provider("nomalum")


def test_available_provider_names():
    names = available_provider_names()
    assert "log" in names
    assert names == sorted(names)


def test_base_provider_not_instantiable():
    with pytest.raises(TypeError):
        BasePushProvider()
