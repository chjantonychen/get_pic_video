import pytest
from app.download_engine.downloader import Downloader

def test_safe_filename():
    d = Downloader({})
    assert d._safe_filename("a<b>c:d") == "a_b_c_d"
    assert d._safe_filename("normal.jpg") == "normal.jpg"
