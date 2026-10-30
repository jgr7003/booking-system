"""Names of devices for the list of connected devices."""

# Browsers, checked in order: Edge and Opera also say "Chrome", Chrome also says "Safari".
_BROWSERS = (("Edg/", "Edge"), ("OPR/", "Opera"), ("Firefox/", "Firefox"), ("Chrome/", "Chrome"), ("Safari/", "Safari"))

# Operating systems, checked in order: Android also says "Linux", iOS also says "Mac OS".
_SYSTEMS = (
    ("Android", "Android"),
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Windows", "Windows"),
    ("Mac OS", "macOS"),
    ("Linux", "Linux"),
)


def describe_device(user_agent: str | None) -> str:
    """A short Spanish name of the device, e.g. «Chrome en Windows».

    Only a label for people: nothing relies on it, so a rough match is enough.

    Args:
        user_agent: The `User-Agent` header.

    Returns:
        The name, or «Dispositivo desconocido».
    """
    if not user_agent:
        return "Dispositivo desconocido"
    browser = next((name for token, name in _BROWSERS if token in user_agent), None)
    system = next((name for token, name in _SYSTEMS if token in user_agent), None)
    if browser and system:
        return f"{browser} en {system}"
    return browser or system or "Dispositivo desconocido"
