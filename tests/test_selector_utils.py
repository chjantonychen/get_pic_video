import pytest
from app.rule_builder import generalize_selectors

def test_generalize_single():
    assert generalize_selectors(["a.link"]) == "a.link"

def test_generalize_multiple():
    sels = ["div.list > a:nth-child(1)", "div.list > a:nth-child(2)"]
    assert generalize_selectors(sels) == "div.list"

def test_generalize_no_common():
    sels = ["a.link", "img.photo"]
    assert generalize_selectors(sels) == "a.link"
