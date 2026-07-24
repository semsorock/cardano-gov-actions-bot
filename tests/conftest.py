import os

# Ensure the config singleton can be imported in test environments that do not
# set Blockfrost credentials.
os.environ.setdefault("BLOCKFROST_PROJECT_ID", "test-project-id")
