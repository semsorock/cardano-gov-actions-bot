import os
import re

# import json
# import http.server
# import socketserver
# import random

from decimal import Decimal

import requests
import tweepy
from psycopg2 import pool
from tenacity import retry, stop_after_attempt, wait_exponential

import functions_framework


API_KEY = os.environ.get("API_KEY")
API_SECRET_KEY = os.environ.get("API_SECRET_KEY")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")
DB_SYNC_URL = os.environ.get("DB_SYNC_URL")

client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET_KEY,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
)

DB_POOL = pool.SimpleConnectionPool(minconn=1, maxconn=1, dsn=DB_SYNC_URL)

QUERY_GA = """
        select
            encode(t.hash, 'hex') as tx_hash,
            gap."type",
            gap.index,
            va.url from gov_action_proposal gap
        join voting_anchor va on gap.voting_anchor_id = va.id
        join tx t on gap.tx_id = t.id
        join block b on t.block_id = b.id
        where b.block_no = %s
        """

QUERY_VOTE = """
        select
            encode(t1.hash, 'hex') as ga_tx_hash,
            gap.index as ga_index,
            encode(t2.hash, 'hex') as vote_tx_hash,
            encode(ch.raw, 'hex') as voter_hash,
            vp."vote",
            va.url
        from gov_action_proposal gap
        join voting_procedure vp on gap.id = vp.gov_action_proposal_id
        join committee_hash ch on vp.committee_voter = ch.id
        join voting_anchor va on vp.voting_anchor_id = va.id
        join tx t1 on gap.tx_id = t1.id
        join tx t2 on vp.tx_id = t2.id
        join block b on t2.block_id = b.id
        where vp.voter_role = 'ConstitutionalCommittee'
        and b.block_no = %s
        """


QUERY_EXPIRATIONS = """
        select
            encode(t.hash, 'hex') as tx_hash,
            gap.index
        from gov_action_proposal gap
        join tx t on gap.tx_id = t.id
        where gap.expiration = %s
        and gap.ratified_epoch is null
        and gap.enacted_epoch is null
        and gap.dropped_epoch is null
        """

QUERY_TREASURY_DONATION_TOTAL_PER_EPOCH = """
        SELECT 
            b.block_no,
            encode(t.hash, 'hex') as tx_hash,
            t.treasury_donation
        FROM tx t
        JOIN block b ON t.block_id = b.id
        WHERE t.treasury_donation > 0
        AND b.epoch_no = %s;
        """


# https://gov.tools/connected/governance_actions/0b19476e40bbbb5e1e8ce153523762e2b6859e7ecacbaf06eae0ee6a447e79b9
def _make_gov_tools_link(tx_hash, gov_action_index):
    return f"https://gov.tools/governance_actions/{tx_hash}#{gov_action_index}"


# https://adastat.net/governances/0b19476e40bbbb5e1e8ce153523762e2b6859e7ecacbaf06eae0ee6a447e79b900
def _make_adastat_link(tx_hash, gov_action_index):
    # Convert the index to hex without 0x prefix and ensure lowercase.
    index_hex = format(gov_action_index, "x")

    # Ensure even number of hex digits for the index part (pad with leading zero if needed).
    if len(index_hex) % 2:
        index_hex = "0" + index_hex
    return f"https://adastat.net/governances/{tx_hash}{index_hex}"


# TODO: add explorer link
# https://explorer.cardano.org/governance-action/gov_action1vrkk4dpuss8l3z9g4uc2rmf8ks0f7j534zvz9v4k85dlc54wa3zsqq68rx0
# def _make_explorer_gov_action_link(gov_action_id):
#     return f"https://explorer.cardano.org/governance-action/{gov_action_id}"


def _make_vote_tx_link(tx_hash):
    return f"https://cexplorer.io/tx/{tx_hash}/governance#data"


def _sanitise_url(url: str):
    return url.replace("ipfs://", "https://ipfs.io/ipfs/")


def _get_gov_actions(block_number):
    conn = DB_POOL.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY_GA, (block_number,))
            rows = cur.fetchall()
        return rows
    finally:
        DB_POOL.putconn(conn)


def camel_case_to_spaced(camel_case_string):
    if not isinstance(camel_case_string, str):
        return None

    if not camel_case_string:  # handle empty string
        return ""

    spaced_string = re.sub(r"(?<!^)(?=[A-Z])", " ", camel_case_string)
    return spaced_string


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_url_content(url):
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()

        else:
            print(f"Error retrieving data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error retrieving data: {e}")
        return None


def _process_gov_action(gov_action):
    tx_hash = gov_action[0]
    action_type = camel_case_to_spaced(gov_action[1])
    gov_action_index = gov_action[2]
    raw_url = gov_action[3]
    url = _sanitise_url(raw_url)

    if tx_hash == "8ad3d454f3496a35cb0d07b0fd32f687f66338b7d60e787fc0a22939e5d8833e":
        if gov_action_index < 17:
            print(f"Skipping gov action: {tx_hash}#{gov_action_index} - {gov_action}")
            return

    content = get_url_content(url)

    tweet_text_lines = []

    tweet_text_lines.append("🚨 NEW GOVERNANCE ACTION ALERT! 🚨\n")

    if content:
        title = content.get("body", {}).get("title")

        if title:
            tweet_text_lines.append(f"📢 Title: {title}")

        # authors = content.get("authors")

        # if authors is not None and len(authors) > 0:
        #     authors_names = [author.get("name") for author in authors]
        #     authors_names_str = ", ".join(authors_names)
        #     tweet_text_lines.append(f"👥 Authors: {authors_names_str}\n")

    tweet_text_lines.append(f"🏷️ Type: {action_type}")
    tweet_text_lines.append(
        f"🔗 Details: {_make_adastat_link(tx_hash, gov_action_index)}\n\n"
    )
    tweet_text_lines.append("#Cardano #Blockchain #Governance")

    tweet_text = "\n".join(tweet_text_lines)

    print(tweet_text)

    # response = client.create_tweet(text=tweet_text)

    # print(f"Response: {response}")


def _get_cc_vote_records(block_number):
    conn = DB_POOL.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY_VOTE, (block_number,))
            rows = cur.fetchall()
        return rows
    finally:
        DB_POOL.putconn(conn)


VOTES_MAPPING = {
    "YES": "Constitutional",
    "NO": "Unconstitutional",
    "ABSTAIN": "Abstain",
}


# CC_MEMBERS_TO_X_HANDLE = {
#     {"CARDANO JAPAN"}:            "@Cardanojp_icc",
#     {"INPUT | OUTPUT"}:           "@InputOutputHK",
#     {"CARDANO FOUNDATION"}:       "@Cardano_CF",
#     {"CARDANO ATLANTIC COUNCIL"}: "@CardanoAtlantic",
#     {"EASTERN CARDANO COUNCIL"}:  "@EasternCardano",
#     {"EMURGO"}:                   "@emurgo_io",
#     {"INTERSECT"}:                "@IntersectMBO"
# }


def _make_vote_text(vote: str):
    return VOTES_MAPPING.get(vote.upper(), vote)


def _process_cc_vote_record(vote_record):
    ga_tx_hash = vote_record[0]
    ga_index = vote_record[1]
    # vote_tx_hash = vote_record[2]
    # voter_hash = vote_record[3]
    vote = vote_record[4]
    raw_url = vote_record[5]

    url = _sanitise_url(raw_url)

    content = get_url_content(url)

    tweet_text_lines = []

    tweet_text_lines.append("📜 CC MEMBER VOTE ALERT! 📜\n")
    tweet_text_lines.append(f"🗳️ The vote is: {_make_vote_text(vote)}")

    if content:
        authors = content.get("authors")

        if authors is not None and len(authors) > 0:
            authors_names = [author.get("name") for author in authors]
            authors_names_str = ", ".join(authors_names)
            tweet_text_lines.append(f"👥 Voted by: {authors_names_str}\n")

    tweet_text_lines.append(
        f"🔗 Gov Action: {_make_adastat_link(ga_tx_hash, ga_index)}"
    )
    tweet_text_lines.append(f"🔗 The vote rationale: {url}\n\n")
    tweet_text_lines.append("#Cardano #Blockchain #Governance")

    tweet_text = "\n".join(tweet_text_lines)

    print(tweet_text)

    # response = client.create_tweet(text=tweet_text)

    # print(f"Response: {response}")


def process_block(request_json):
    """
    sample body request:
    {
        "id": "00683ff9-290c-4e58-a3a4-8b149c4e0795",
        "webhook_id": "dba3dcfc-f382-433e-9474-412ad2d5bb21",
        "created": 1741253461,
        "api_version": 1,
        "type": "block",
        "payload": {
            "time": 1741253373,
            "height": 11567685,
            "hash": "e9808bba81f099ae1442c01c022caa60a9539b33f214a5fd65a61cb1d4e11f03",
            "slot": 149687082,
            "epoch": 544,
            "epoch_slot": 42282,
            "slot_leader": "pool1ax8znp3yeeh0udrr2vvtm4wkxjldwv4mywycn573km7fu20y5xa",
            "size": 20617,
            "tx_count": 32,
            "output": "2413374482586",
            "fees": "7905893",
            "block_vrf": "vrf_vk1vzzngklkz56jwr4vgl9vxny3gkjkkevcns2cwqhhff35k26klm5qez5c3q",
            "op_cert": "c0127703768a2461cf25105b4e2bf43ef1a6a37f529f0f25715aea224c243255",
            "op_cert_counter": "28",
            "previous_block": "bb57af294fe124843b773188fae0e5a699bac3e5309f0b44200955e4ceaf9de2",
            "next_block": "acccea365d31fcb5e20572cfc3bcf31bbd3999a32fbb2177c3bf677c8a56b560",
            "confirmations": 4
        }
    }
    """

    block_number = request_json.get("payload", {}).get("height")

    # Gov actions
    gov_actions = _get_gov_actions(block_number)

    if len(gov_actions) == 0:
        print(f"No gov actions for the block: {block_number}")
    else:
        for gov_action in gov_actions:
            _process_gov_action(gov_action)

    # Votes
    cc_vote_records = _get_cc_vote_records(block_number)

    if len(cc_vote_records) == 0:
        print(f"No CC vote records for the block: {block_number}")
    else:
        for cc_vote_record in cc_vote_records:
            _process_cc_vote_record(cc_vote_record)


def _get_ga_expirations(epoch_number):
    conn = DB_POOL.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY_EXPIRATIONS, (epoch_number,))
            rows = cur.fetchall()
        return rows
    finally:
        DB_POOL.putconn(conn)


def process_epoch(request_json):
    """
    sample body request:
    {
        "id": "5ffcaf65-7961-4377-9741-fa0c76176a4b",
        "webhook_id": "b592db93-ec26-4ecc-8800-8a14b3a2806f",
        "created": 1654811689,
        "api_version": 1,
        "type": "epoch",
        "payload": {
            "previous_epoch": {
                "epoch": 343,
                "start_time": 1654379091,
                "end_time": 1654811091,
                "first_block_time": 1654379116,
                "last_block_time": 1654811087,
                "block_count": 20994,
                "tx_count": 463239,
                "output": "106038169691018243",
                "fees": "162340782180",
                "active_stake": "24538091587045780"
            },
            "current_epoch": {
                "epoch": 344,
                "start_time": 1654811091,
                "end_time": 1655243091
            }
        }
    }
    """

    epoch_number = request_json.get("payload", {}).get("current_epoch", {}).get("epoch")

    print(f"Processing epoch: {epoch_number}")

    # # commented out for now. need to consider if we want to process this
    # _process_ga_expirations(epoch_number)

    _process_treasury_donations(epoch_number - 1)


def _process_ga_expirations(epoch_number):
    ga_expirations = _get_ga_expirations(epoch_number + 1)

    if len(ga_expirations) == 0:
        print(f"No GA expirations for the epoch: {epoch_number}")
    else:
        for ga_expiration in ga_expirations:
            _process_ga_expiration(ga_expiration)


def _process_ga_expiration(ga_expiration):
    ga_tx_hash = ga_expiration[0]
    ga_index = ga_expiration[1]

    tweet_text_lines = []

    tweet_text_lines.append("⏳ GOVERNANCE ACTION EXPIRY ALERT! ⏳\n\n")
    tweet_text_lines.append(
        "Heads up! There is only 1 epoch (5 days) left to vote on this GA:\n"
    )
    tweet_text_lines.append(f"🔗 {_make_adastat_link(ga_tx_hash, ga_index)}")
    tweet_text_lines.append("Make sure to review and participate if applicable!\n\n")

    tweet_text_lines.append("#Cardano #Blockchain #Governance")

    tweet_text = "\n".join(tweet_text_lines)

    print(tweet_text)

    # response = client.create_tweet(text=tweet_text)

    # print(f"Response: {response}")


def _get_treasury_donations(epoch_number):
    conn = DB_POOL.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY_TREASURY_DONATION_TOTAL_PER_EPOCH, (epoch_number,))
            rows = cur.fetchall()
        return rows
    finally:
        DB_POOL.putconn(conn)


def _convert_lovelace_to_ada(lovelace):
    return lovelace / Decimal("1000000")


def _process_treasury_donations(epoch_number):
    donations = _get_treasury_donations(epoch_number)
    print(f"Donations: {donations}")

    if donations is None or len(donations) == 0:
        print(f"No treasury donations for the epoch: {epoch_number}")
    else:
        total_donations_ada = _convert_lovelace_to_ada(
            sum(donation[2] for donation in donations)
        )

        tweet_text_lines = []

        tweet_text_lines.append("💸 PREVIOUS EPOCH TREASURY DONATIONS! 💸\n")

        tweet_text_lines.append(
            "Here are the Cardano Treasury donation stats for the last epoch:"
        )
        tweet_text_lines.append(f"📈 Donations Count: {len(donations)}")
        tweet_text_lines.append(f"💰 Total Donated: {total_donations_ada} ADA")
        tweet_text_lines.append(
            "Thank you to everyone supporting the growth of #Cardano!\n"
        )

        tweet_text_lines.append("#Treasury #Blockchain #Governance")

        tweet_text = "\n".join(tweet_text_lines)

        print(tweet_text)

        # response = client.create_tweet(text=tweet_text)

        # print(f"Response: {response}")


@functions_framework.http
def hello_http(request):

    request_json = request.get_json(silent=True)
    request_path = request.path

    print(f"request_json: {request_json}")
    print(f"request_path: {request_path}")

    if request_path == "/block":
        process_block(request_json)
    elif request_path == "/epoch":
        process_epoch(request_json)
    else:
        print(f"Unknown request path: {request_path}")

    return f"Received POST data: {request_json}".encode("utf-8")
