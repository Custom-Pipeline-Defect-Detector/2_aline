"""Backward-compatible auth exports.

Canonical auth/RBAC dependency helpers live in app.deps.
"""

from app.deps import get_current_user, require_roles

__all__ = ["get_current_user", "require_roles"]
