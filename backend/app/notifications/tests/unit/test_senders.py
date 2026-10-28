import pytest

from app.notifications.core.config import EmailBackend, EmailSettings
from app.notifications.providers.console.sender import ConsoleEmailSender
from app.notifications.providers.smtp.sender import SmtpEmailSender, build_mime
from app.notifications.public import EmailDeliveryError, EmailMessage, create_email_sender

pytestmark = pytest.mark.anyio

# A message with an accent and a symbol in the subject, as the real ones have.
MESSAGE = EmailMessage(
    to="ana@example.com",
    subject="Reserva confirmada · GNA3VA · Bogotá ⇄ Cali",
    html="<p>Hola</p>",
    text="Hola",
)


def test_the_environment_chooses_the_sender():
    assert isinstance(create_email_sender(EmailSettings(email_backend=EmailBackend.SMTP)), SmtpEmailSender)
    assert isinstance(create_email_sender(EmailSettings(email_backend=EmailBackend.CONSOLE)), ConsoleEmailSender)


def test_tests_use_the_console_sender_by_default():
    assert isinstance(create_email_sender(), ConsoleEmailSender)


def test_the_mime_message_has_text_with_an_html_alternative():
    mime = build_mime(MESSAGE, "Vuelos <reservas@vuelos.test>")

    assert mime["To"] == "ana@example.com"
    assert mime["Subject"] == MESSAGE.subject
    assert mime["Message-ID"].endswith("@vuelos.test>")
    assert [part.get_content_type() for part in mime.iter_parts()] == ["text/plain", "text/html"]


async def test_an_unreachable_server_is_a_delivery_error():
    sender = SmtpEmailSender(EmailSettings(smtp_host="127.0.0.1", smtp_port=9, smtp_timeout_s=1))

    with pytest.raises(EmailDeliveryError):
        await sender.send(MESSAGE)
