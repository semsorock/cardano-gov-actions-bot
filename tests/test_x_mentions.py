from bot.x_mentions import extract_actionable_mentions


def _base_event() -> dict:
    return {
        "id_str": "post-1",
        "text": "@GovActions hello",
        "user": {"id_str": "111", "screen_name": "alice"},
        "entities": {"user_mentions": [{"id_str": "999", "screen_name": "GovActions"}]},
    }


def test_direct_mention_is_actionable() -> None:
    payload = {"for_user_id": "999", "tweet_create_events": [_base_event()]}

    actionable, ignored = extract_actionable_mentions(payload)

    assert len(actionable) == 1
    assert actionable[0].post_id == "post-1"
    assert ignored == []


def test_reply_to_bot_without_user_mentions_is_actionable() -> None:
    event = _base_event()
    event["entities"] = {"user_mentions": []}
    event["in_reply_to_user_id"] = "999"
    payload = {"for_user_id": "999", "tweet_create_events": [event]}

    actionable, ignored = extract_actionable_mentions(payload)

    assert len(actionable) == 1
    assert actionable[0].post_id == "post-1"
    assert ignored == []


def test_repost_of_bot_is_actionable() -> None:
    event = _base_event()
    event["text"] = "RT @GovActions: sample post"
    event["entities"] = {"user_mentions": []}
    event["retweeted_status"] = {"user": {"id_str": "999"}}
    payload = {"for_user_id": "999", "tweet_create_events": [event]}

    actionable, ignored = extract_actionable_mentions(payload)

    assert len(actionable) == 1
    assert actionable[0].post_id == "post-1"
    assert ignored == []


def test_repost_of_other_account_is_ignored() -> None:
    event = _base_event()
    event["text"] = "RT @someoneelse: sample post"
    event["entities"] = {"user_mentions": []}
    event["retweeted_status"] = {"user": {"id_str": "123"}}
    payload = {"for_user_id": "999", "tweet_create_events": [event]}

    actionable, ignored = extract_actionable_mentions(payload)

    assert actionable == []
    assert len(ignored) == 1
    assert ignored[0].post_id == "post-1"
    assert ignored[0].reason == "not_mentioning_bot"


def test_post_create_events_alias_is_supported() -> None:
    payload = {"for_user_id": "999", "post_create_events": [_base_event()]}

    actionable, ignored = extract_actionable_mentions(payload)

    assert len(actionable) == 1
    assert actionable[0].post_id == "post-1"
    assert ignored == []


def test_nested_data_payload_is_supported() -> None:
    payload = {
        "data": {
            "for_user_id": "999",
            "post_create_events": [_base_event()],
        }
    }

    actionable, ignored = extract_actionable_mentions(payload)

    assert len(actionable) == 1
    assert actionable[0].post_id == "post-1"
    assert ignored == []
