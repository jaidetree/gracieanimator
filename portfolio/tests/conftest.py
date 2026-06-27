import pytest


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Isolate uploads and imagekit cache files in a per-test temp dir."""
    settings.MEDIA_ROOT = tmp_path
