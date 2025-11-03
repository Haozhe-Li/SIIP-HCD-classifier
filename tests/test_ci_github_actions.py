# For testing functionality for Github Actions CI checks


def test_import() -> None:
    """test core import statement"""
    try:
        import core
    except ImportError as e:
        assert False, f"ImportError raised: {e}"
