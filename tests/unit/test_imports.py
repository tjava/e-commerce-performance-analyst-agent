def test_package_can_be_imported() -> None:
    import ecommerce_analyst

    assert ecommerce_analyst.__version__ == "0.1.0"
