"""SSH tunnel for accessing PostgreSQL through a bastion host.

Uses paramiko directly (sshtunnel is unmaintained and incompatible with
paramiko >= 4).  A local TCP server accepts connections on 127.0.0.1 and
forwards them through the SSH transport to the remote DB host.
"""

from __future__ import annotations

import select
import socket
import threading
from urllib.parse import urlparse, urlunparse

import paramiko

from bot.config import Config
from bot.logging import get_logger

logger = get_logger("ssh_tunnel")


class SshTunnel:
    """Local port-forwarding tunnel over SSH."""

    def __init__(self, ssh_client: paramiko.SSHClient, local_port: int) -> None:
        self.ssh_client = ssh_client
        self.local_bind_port = local_port
        self._server: socket.socket | None = None

    def is_active(self) -> bool:
        """Return whether the local listener and SSH transport are both usable."""
        transport = self.ssh_client.get_transport()
        return (
            self._server is not None
            and self._server.fileno() != -1
            and transport is not None
            and transport.is_active()
        )

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
            self._server = None
        self.ssh_client.close()


def _forward(local_sock: socket.socket, channel: paramiko.Channel) -> None:
    """Bi-directionally forward data between a local socket and SSH channel."""
    try:
        while True:
            r, _, _ = select.select([local_sock, channel], [], [], 60)
            if local_sock in r:
                data = local_sock.recv(16384)
                if not data:
                    break
                channel.sendall(data)
            if channel in r:
                data = channel.recv(16384)
                if not data:
                    break
                local_sock.sendall(data)
    except Exception:
        pass
    finally:
        channel.close()
        local_sock.close()


def _accept_loop(
    server: socket.socket,
    transport: paramiko.Transport,
    remote_host: str,
    remote_port: int,
) -> None:
    """Accept local connections and forward each through the SSH transport."""
    while True:
        try:
            client_sock, addr = server.accept()
        except OSError:
            # Server socket closed — tunnel is stopping.
            break
        try:
            if not transport.is_active():
                logger.warning(
                    "SSH transport became inactive; stopping local forwarder for %s:%s",
                    remote_host,
                    remote_port,
                )
                client_sock.close()
                server.close()
                break
            channel = transport.open_channel(
                "direct-tcpip",
                (remote_host, remote_port),
                addr,
            )
        except paramiko.SSHException:
            if not transport.is_active():
                logger.warning(
                    "SSH transport became inactive while opening channel; stopping local forwarder for %s:%s",
                    remote_host,
                    remote_port,
                )
                client_sock.close()
                server.close()
                break
            logger.exception("Failed to open SSH channel to %s:%s", remote_host, remote_port)
            client_sock.close()
            continue
        except Exception:
            logger.exception("Failed to open SSH channel to %s:%s", remote_host, remote_port)
            client_sock.close()
            continue
        threading.Thread(target=_forward, args=(client_sock, channel), daemon=True).start()


def start_tunnel(cfg: Config, *, local_port: int | None = None) -> SshTunnel:
    """Start an SSH tunnel forwarding a local port to the remote DB.

    Parses ``cfg.db_sync_url`` to extract the remote DB host/port and
    creates a tunnel through the SSH server specified in ``cfg``.
    """
    parsed = urlparse(cfg.db_sync_url)
    remote_host = parsed.hostname or "localhost"
    remote_port = parsed.port or 5432

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        cfg.ssh_host,
        port=cfg.ssh_port,
        username=cfg.ssh_user,
        key_filename=cfg.ssh_key_path,
        timeout=30,
        banner_timeout=30,
        auth_timeout=30,
    )

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", local_port or 0))
    server.listen(5)
    local_port = server.getsockname()[1]

    transport = client.get_transport()
    assert transport is not None
    transport.set_keepalive(30)

    threading.Thread(
        target=_accept_loop,
        args=(server, transport, remote_host, remote_port),
        daemon=True,
    ).start()

    tunnel = SshTunnel(client, local_port)
    tunnel._server = server

    logger.info(
        "SSH tunnel established: 127.0.0.1:%s -> %s:%s via %s",
        local_port,
        remote_host,
        remote_port,
        cfg.ssh_host,
    )
    return tunnel


def get_tunneled_url(cfg: Config, tunnel: SshTunnel) -> str:
    """Rewrite ``db_sync_url`` to route through the local tunnel port."""
    parsed = urlparse(cfg.db_sync_url)
    local = f"127.0.0.1:{tunnel.local_bind_port}"
    if parsed.password:
        netloc = f"{parsed.username}:{parsed.password}@{local}"
    else:
        netloc = f"{parsed.username}@{local}"
    return urlunparse(parsed._replace(netloc=netloc))


class SshTunnelManager:
    """Own the SSH tunnel and recreate it when the transport drops."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._lock = threading.Lock()
        self._tunnel: SshTunnel | None = None

    def ensure_active(self) -> SshTunnel:
        """Return an active tunnel, recreating it if necessary."""
        with self._lock:
            if self._tunnel is not None and self._tunnel.is_active():
                return self._tunnel

            preferred_port = self._tunnel.local_bind_port if self._tunnel is not None else None
            if self._tunnel is not None:
                logger.warning("SSH tunnel is inactive; recreating it")
                self._tunnel.stop()
                self._tunnel = None

            try:
                self._tunnel = start_tunnel(self._cfg, local_port=preferred_port)
            except OSError:
                if preferred_port is None:
                    raise
                logger.warning(
                    "Could not rebind SSH tunnel on local port %s; allocating a new port",
                    preferred_port,
                    exc_info=True,
                )
                self._tunnel = start_tunnel(self._cfg)

            return self._tunnel

    def get_tunneled_url(self) -> str:
        """Return the DB URL routed through the current active tunnel."""
        return get_tunneled_url(self._cfg, self.ensure_active())

    def stop(self) -> None:
        with self._lock:
            if self._tunnel is not None:
                self._tunnel.stop()
                self._tunnel = None
