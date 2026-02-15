import os

# Ensure config singleton can be imported in test environments that do not set DB_SYNC_URL.
os.environ.setdefault("DB_SYNC_URL", "postgresql://localhost/test")
