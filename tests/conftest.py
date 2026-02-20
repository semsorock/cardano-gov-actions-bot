import os

# Ensure config singleton can be imported in test environments that do not set BLOCKFROST_PROJECT_ID.
os.environ.setdefault("BLOCKFROST_PROJECT_ID", "test_project_id_mainnet")
