"""Append-only audit log writer + reader against ClickHouse.

Usage::

    from wfi_audit import AuditLogger
    audit = AuditLogger.from_env()
    await audit.record(AuditLogEntry(...))
"""

from wfi_audit.client import AuditLogger, NullAuditLogger

__all__ = ["AuditLogger", "NullAuditLogger"]
