import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("/app/logs")
LOG_FILE = LOG_DIR / "audit.log"

# Tipos de evento
ACCESS_GRANTED      = "ACCESS_GRANTED"
ACCESS_DENIED_401   = "ACCESS_DENIED_401"
ACCESS_DENIED_403   = "ACCESS_DENIED_403"
LOGIN               = "LOGIN"
LOGOUT              = "LOGOUT"


def _setup_logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("retailcorp.audit")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
    logger.propagate = False
    return logger


_logger = _setup_logger()


def log_event(
    event_type: str,
    username: str,
    path: str,
    ip: str,
    roles: list | None = None,
    detail: str | None = None,
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "username": username,
        "roles": roles or [],
        "path": path,
        "ip": ip,
    }
    if detail:
        entry["detail"] = detail
    _logger.info(json.dumps(entry, ensure_ascii=False))


def read_events(n: int = 100) -> list[dict]:
    """Retorna os últimos N eventos, do mais recente para o mais antigo."""
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return list(reversed(events[-n:]))
