"""Async Blockfrost client and the domain adapters built on top of it.

Blockfrost is the sole Cardano data provider (see issue #34). This package
holds the thin HTTP client (:mod:`bot.blockfrost.client`) plus the pure helpers
that turn Blockfrost responses into the bot's domain objects: feed pagination
and watermarks (:mod:`bot.blockfrost.feeds`), governance-type/vote mapping
(:mod:`bot.blockfrost.mapping`), committee-snapshot parsing
(:mod:`bot.blockfrost.committee`) and treasury-donation extraction from
transaction CBOR (:mod:`bot.blockfrost.cbor`).
"""
