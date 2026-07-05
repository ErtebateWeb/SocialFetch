import socialfetch


def test_package_imports() -> None:
    assert hasattr(socialfetch, "__package__")
    assert socialfetch.__package__ == "socialfetch"
