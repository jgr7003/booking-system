import pytest

from app.identity.services.devices import describe_device

WINDOWS_CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
IPHONE_SAFARI = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1"
ANDROID_EDGE = "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140.0 Mobile Safari/537.36 EdgA/140.0 Edg/140.0"


@pytest.mark.parametrize(
    ("user_agent", "name"),
    [
        (WINDOWS_CHROME, "Chrome en Windows"),
        (IPHONE_SAFARI, "Safari en iPhone"),
        (ANDROID_EDGE, "Edge en Android"),
        (None, "Dispositivo desconocido"),
        ("curl/8.0", "Dispositivo desconocido"),
    ],
)
def test_names_the_device_from_its_user_agent(user_agent, name):
    assert describe_device(user_agent) == name
