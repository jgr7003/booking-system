"""The SMTP sender against the local Mailpit, checked through Mailpit's API."""

import os
import uuid
from urllib.parse import urlparse

import httpx2
import pytest

from app.notifications.core.config import EmailBackend, EmailSettings
from app.notifications.public import EmailMessage, create_email_sender

pytestmark = pytest.mark.anyio

# Web and API of Mailpit; its SMTP port is 1025 on the same host.
MAILPIT_URL = os.environ.get("TEST_MAILPIT_URL")


async def test_the_email_reaches_the_mail_server_with_both_bodies():
    if not MAILPIT_URL:
        pytest.skip("TEST_MAILPIT_URL is not set")
    subject = f"Prueba {uuid.uuid4().hex[:8]} · Bogotá ⇄ Cali"
    settings = EmailSettings(email_backend=EmailBackend.SMTP, smtp_host=urlparse(MAILPIT_URL).hostname, smtp_port=1025)

    await create_email_sender(settings).send(
        EmailMessage(to="ana@example.com", subject=subject, html="<p><strong>Hola</strong> Ana</p>", text="Hola Ana")
    )

    async with httpx2.AsyncClient(base_url=MAILPIT_URL) as mailpit:
        found = (await mailpit.get("/api/v1/search", params={"query": f'subject:"{subject}"'})).json()["messages"]
        assert len(found) == 1
        message = (await mailpit.get(f"/api/v1/message/{found[0]['ID']}")).json()
    assert message["To"][0]["Address"] == "ana@example.com"
    assert message["Subject"] == subject
    assert "<strong>Hola</strong>" in message["HTML"]
    assert message["Text"].strip() == "Hola Ana"
