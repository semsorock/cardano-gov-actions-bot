"""SSH tunnel for accessing PostgreSQL through a bastion host."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from sshtunnel import SSHTunnelForwarder

from bot.config import Config
from bot.logging import get_logger

logger = get_logger("ssh_tunnel")


def start_tunnel(cfg: Config) -> SSHTunnelForwarder:
    """Start an SSH tunnel forwarding a local port to the remote DB.

    Parses ``cfg.db_sync_url`` to extract the remote DB host/port and
    creates a tunnel through the SSH server specified in ``cfg``.
    """
    parsed = urlparse(cfg.db_sync_url)
    remote_host = parsed.hostname or "localhost"
    remote_port = parsed.port or 5432

    tunnel = SSHTunnelForwarder(
        (cfg.ssh_host, cfg.ssh_port),
        ssh_username=cfg.ssh_user,
        ssh_pkey=cfg.ssh_key_path,
        remote_bind_address=(remote_host, remote_port),
        local_bind_address=("127.0.0.1", 0),
    )
    tunnel.start()

    logger.info(
        "SSH tunnel established: 127.0.0.1:%s -> %s:%s via %s",
        tunnel.local_bind_port,
        remote_host,
        remote_port,
        cfg.ssh_host,
    )
    return tunnel


def get_tunneled_url(cfg: Config, tunnel: SSHTunnelForwarder) -> str:
    """Rewrite ``db_sync_url`` to route through the local tunnel port."""
    parsed = urlparse(cfg.db_sync_url)
    local = f"127.0.0.1:{tunnel.local_bind_port}"
    if parsed.password:
        netloc = f"{parsed.username}:{parsed.password}@{local}"
    else:
        netloc = f"{parsed.username}@{local}"
    return urlunparse(parsed._replace(netloc=netloc))
