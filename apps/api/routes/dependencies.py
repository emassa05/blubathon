"""Route dependencies for the fixed-tenant API."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from apps.api.context import RequestContext
from apps.api.events import EventBroker
from apps.api.services import ServiceRegistry


def registry(request: Request) -> ServiceRegistry:
    return request.app.state.registry


def request_context(request: Request) -> RequestContext:
    return RequestContext(request_id=request.state.request_id)


def event_broker(request: Request) -> EventBroker:
    return request.app.state.event_broker


Registry = Annotated[ServiceRegistry, Depends(registry)]
Context = Annotated[RequestContext, Depends(request_context)]
Broker = Annotated[EventBroker, Depends(event_broker)]
