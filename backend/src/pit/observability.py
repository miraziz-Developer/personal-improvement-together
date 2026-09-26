"""Error tracking (Sentry). Off unless PIT_SENTRY_DSN is set.

Every ERROR log becomes an alert — including "AI verification failed", which would otherwise
pass quietly because proofs fall back to an unchecked approval."""

import logging

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from pit.config import Settings


def init_sentry(settings: Settings, component: str) -> bool:
    dsn = settings.sentry_dsn.get_secret_value()
    if not dsn:
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=settings.env,
        server_name=component,  # "api" or "worker"
        traces_sample_rate=settings.sentry_traces_sample_rate,
        # Users are children too: no IPs, cookies or request bodies (passwords, photos) leave.
        send_default_pii=False,
        max_request_body_size="never",
        shutdown_timeout=2,  # never hold a restart hostage to an unreachable Sentry
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    return True
