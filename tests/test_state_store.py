from __future__ import annotations

from bot import state_store


class _FakeSnapshot:
    def __init__(self, data: dict | None):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return self._data


class _FakeDocumentRef:
    def __init__(self, collection_store: dict, doc_id: str):
        self._collection_store = collection_store
        self._doc_id = doc_id

    def get(self):
        return _FakeSnapshot(self._collection_store.get(self._doc_id))

    def set(self, payload, merge: bool = False):
        if not merge or self._doc_id not in self._collection_store:
            self._collection_store[self._doc_id] = dict(payload)
            return

        merged = dict(self._collection_store[self._doc_id])
        merged.update(payload)
        self._collection_store[self._doc_id] = merged


class _FakeCollectionRef:
    def __init__(self, db_store: dict, collection_name: str):
        self._db_store = db_store
        self._collection_name = collection_name

    def document(self, doc_id: str):
        collection_store = self._db_store.setdefault(self._collection_name, {})
        return _FakeDocumentRef(collection_store, doc_id)


class _FakeFirestoreClient:
    def __init__(self):
        self._store: dict = {}

    def collection(self, collection_name: str):
        return _FakeCollectionRef(self._store, collection_name)


class _FakeFirestoreModule:
    SERVER_TIMESTAMP = "SERVER_TS"


def _reset_state_store(monkeypatch):
    monkeypatch.setattr(state_store, "_FIRESTORE_CLIENT", None)
    monkeypatch.setattr(state_store, "_FIRESTORE_UNAVAILABLE_LOGGED", False)


def test_save_and_get_action_tweet_id(monkeypatch):
    _reset_state_store(monkeypatch)
    fake_client = _FakeFirestoreClient()
    monkeypatch.setattr(state_store, "_get_firestore_client", lambda: fake_client)
    monkeypatch.setattr(state_store, "firestore", _FakeFirestoreModule())

    state_store.save_action_tweet_id("abc123", 0, "987654", source_block=11)

    assert state_store.get_action_tweet_id("abc123", 0) == "987654"
    doc = fake_client.collection(state_store.GOV_ACTION_STATE_COLLECTION).document("abc123_0").get().to_dict()
    assert doc["archived_action"] is True
    assert doc["source_block"] == 11
    assert doc["last_updated_at"] == "SERVER_TS"


def test_get_action_tweet_id_returns_none_for_missing_doc(monkeypatch):
    _reset_state_store(monkeypatch)
    monkeypatch.setattr(state_store, "_get_firestore_client", lambda: _FakeFirestoreClient())

    assert state_store.get_action_tweet_id("missing", 2) is None


def test_set_and_get_checkpoint(monkeypatch):
    _reset_state_store(monkeypatch)
    fake_client = _FakeFirestoreClient()
    monkeypatch.setattr(state_store, "_get_firestore_client", lambda: fake_client)
    monkeypatch.setattr(state_store, "firestore", _FakeFirestoreModule())

    state_store.set_checkpoint("blockfrost_main", block_no=777, epoch_no=123)

    checkpoint = state_store.get_checkpoint("blockfrost_main")
    assert checkpoint is not None
    assert checkpoint["last_block_no"] == 777
    assert checkpoint["last_epoch"] == 123
    assert checkpoint["updated_at"] == "SERVER_TS"


def test_mark_cc_vote_archived_writes_state(monkeypatch):
    _reset_state_store(monkeypatch)
    fake_client = _FakeFirestoreClient()
    monkeypatch.setattr(state_store, "_get_firestore_client", lambda: fake_client)
    monkeypatch.setattr(state_store, "firestore", _FakeFirestoreModule())

    vote_key = "votetx_gatx_5_cchot1abc"
    assert state_store.is_cc_vote_archived(vote_key) is False

    state_store.mark_cc_vote_archived(
        vote_key,
        ga_tx_hash="ga_hash",
        ga_index=5,
        voter_hash="voter_hash",
        source_block=42,
    )

    doc = fake_client.collection(state_store.CC_VOTE_STATE_COLLECTION).document(vote_key).get().to_dict()
    assert doc["archived_vote"] is True
    assert doc["ga_tx_hash"] == "ga_hash"
    assert doc["source_block"] == 42
    assert doc["last_updated_at"] == "SERVER_TS"
    assert state_store.is_cc_vote_archived(vote_key) is True


def test_is_action_archived(monkeypatch):
    _reset_state_store(monkeypatch)
    fake_client = _FakeFirestoreClient()
    monkeypatch.setattr(state_store, "_get_firestore_client", lambda: fake_client)
    monkeypatch.setattr(state_store, "firestore", _FakeFirestoreModule())

    assert state_store.is_action_archived("tx", 0) is False
    state_store.save_action_tweet_id("tx", 0, "123", source_block=5)
    assert state_store.is_action_archived("tx", 0) is True


def test_feed_watermark_roundtrip(monkeypatch):
    _reset_state_store(monkeypatch)
    fake_client = _FakeFirestoreClient()
    monkeypatch.setattr(state_store, "_get_firestore_client", lambda: fake_client)
    monkeypatch.setattr(state_store, "firestore", _FakeFirestoreModule())

    assert state_store.get_feed_watermark("governance_proposals") is None
    state_store.set_feed_watermark("governance_proposals", "gov_action1abc")
    assert state_store.get_feed_watermark("governance_proposals") == "gov_action1abc"


def test_committee_snapshot_roundtrip(monkeypatch):
    _reset_state_store(monkeypatch)
    fake_client = _FakeFirestoreClient()
    monkeypatch.setattr(state_store, "_get_firestore_client", lambda: fake_client)
    monkeypatch.setattr(state_store, "firestore", _FakeFirestoreModule())

    assert state_store.get_committee_snapshot(500) is None
    snapshot = {"quorum": {"numerator": 2, "denominator": 3}, "members": []}
    state_store.save_committee_snapshot(500, snapshot)
    assert state_store.get_committee_snapshot(500) == snapshot


def test_treasury_donation_accumulation_is_idempotent(monkeypatch):
    _reset_state_store(monkeypatch)
    fake_client = _FakeFirestoreClient()
    monkeypatch.setattr(state_store, "_get_firestore_client", lambda: fake_client)
    monkeypatch.setattr(state_store, "firestore", _FakeFirestoreModule())

    from bot.models import TreasuryDonation

    state_store.record_treasury_donations(510, [TreasuryDonation(block_no=1, tx_hash="aa", amount_lovelace=1_000_000)])
    state_store.record_treasury_donations(
        510,
        [
            TreasuryDonation(block_no=1, tx_hash="aa", amount_lovelace=1_000_000),  # duplicate
            TreasuryDonation(block_no=2, tx_hash="bb", amount_lovelace=2_000_000),
        ],
    )

    doc = state_store.get_treasury_epoch(510)
    assert doc["donations"] == {"aa": 1_000_000, "bb": 2_000_000}
    assert sum(doc["donations"].values()) == 3_000_000

    assert not doc.get("summarized")
    state_store.mark_treasury_epoch_summarized(510)
    assert state_store.get_treasury_epoch(510)["summarized"] is True


def test_donation_start_epoch_is_set_once(monkeypatch):
    _reset_state_store(monkeypatch)
    fake_client = _FakeFirestoreClient()
    monkeypatch.setattr(state_store, "_get_firestore_client", lambda: fake_client)
    monkeypatch.setattr(state_store, "firestore", _FakeFirestoreModule())

    assert state_store.get_donation_start_epoch() is None
    state_store.ensure_donation_start_epoch(500)
    state_store.ensure_donation_start_epoch(501)  # ignored — first wins
    assert state_store.get_donation_start_epoch() == 500
