ADMIN = "Admin"


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(name: str = ADMIN) -> dict:
    """The headers of a hub login for that person (tests/fake_hub.py)."""
    import fake_hub

    return bearer(fake_hub.token(name))
