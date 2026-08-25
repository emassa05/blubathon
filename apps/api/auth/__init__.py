"""Autenticación demo y autorización clínica (SPEC 13, CONVENTIONS 15)."""

from __future__ import annotations

from apps.api.auth.authorization import (
    AuthorizationService,
    SubjectAuthorization,
)
from apps.api.auth.context import ActorContext

__all__ = ["ActorContext", "AuthorizationService", "SubjectAuthorization"]
