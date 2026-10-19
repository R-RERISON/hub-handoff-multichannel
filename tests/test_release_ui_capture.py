"""SPEC-006C-2 unit tests; no browser launch, login or data migration."""
from pathlib import Path

import pytest

from scripts import release_ui_capture as cap
from scripts.lab_environment import LabSafetyError


class Locator:
    def __init__(self, selected="n1", visible=True):
        self.selected = selected
        self.visible = visible

    def count(self):
        return 1

    def is_visible(self):
        return self.visible

    def input_value(self):
        return self.selected


class FakePage:
    def __init__(self, url, width, height, queue="n1", scroll_width=None):
        self.url = url
        self.width = width
        self.height = height
        self.queue = queue
        self.scroll_width = scroll_width or width

    def locator(self, css):
        return Locator(self.queue)

    def evaluate(self, source):
        assert "innerWidth" in source
        return {
            "width": self.width, "height": self.height,
            "scrollWidth": self.scroll_width,
        }

    def screenshot(self, *, full_page, animations):
        assert full_page is False
        assert animations == "disabled"
        return b"QA-ONLY-MOCK-BROWSER-PNG"


def test_validates_exact_route_queue_and_viewport_before_writing(tmp_path):
    target = tmp_path / "capture.png"
    page = FakePage(cap.WEB_URL + "/supervisao/conversas", 1366, 768, queue="n2")
    slot = ("UX-02", "SUPERVISOR", "historico", "n2", 1366, 768)
    assert cap.capture_one(page, target, slot)["horizontal_overflow"] is False
    assert target.read_bytes() == b"QA-ONLY-MOCK-BROWSER-PNG"
    with pytest.raises(LabSafetyError, match="sobrescrita"):
        cap.capture_one(page, target, slot)


def test_rejects_wrong_queue_or_false_viewport_without_screenshot(tmp_path):
    page = FakePage(cap.WEB_URL + "/supervisao/conversas", 390, 844, queue="n1")
    requested = ("UX-02", "SUPERVISOR", "historico", "n2", 1366, 768)
    with pytest.raises(LabSafetyError, match="Fila"):
        cap.capture_one(page, tmp_path / "bad.png", requested)
    assert not (tmp_path / "bad.png").exists()
    page.queue = "n2"
    with pytest.raises(LabSafetyError, match="Viewport"):
        cap.capture_one(page, tmp_path / "bad.png", requested)
    assert not (tmp_path / "bad.png").exists()


def test_never_captures_remote_site_and_reports_horizontal_overflow(tmp_path):
    slot = ("UX-08", "OPERATOR", "mesa", "", 390, 844)
    external = FakePage("https://example.com/operador", 390, 844)
    with pytest.raises(LabSafetyError, match="LOCAL"):
        cap.capture_one(external, tmp_path / "remote.png", slot)
    assert not (tmp_path / "remote.png").exists()

    page = FakePage(cap.WEB_URL + "/operador", 390, 844, scroll_width=401)
    target = Path(tmp_path / "overflow.png")
    observation = cap.capture_one(page, target, slot)
    assert observation["horizontal_overflow"] is True
