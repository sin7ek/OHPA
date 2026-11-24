"""Release branding invariants; no browser or third-party image dependency."""
import json
import struct
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata():
    version = (ROOT / "VERSION").read_text().strip()
    assert f'version: "{version}"' in (ROOT / "ohpa/config.yaml").read_text().splitlines()
    for changelog in ("CHANGELOG.md", "ohpa/CHANGELOG.md"):
        assert f"## {version}" in (ROOT / changelog).read_text().splitlines()


def test_native_branding_pngs():
    for path, dimensions in (("ohpa/icon.png", (128, 128)), ("ohpa/logo.png", (250, 98))):
        data = (ROOT / path).read_bytes()
        assert data[:8] == bytes.fromhex("89504e470d0a1a0a")
        assert data[12:16] == b"IHDR"
        assert struct.unpack(">II", data[16:24]) == dimensions


def test_shared_brand_assets():
    html = (ROOT / "static/index.html").read_text()
    for path in ("static/branding/app-icon.svg", "static/branding/tokens.css"):
        assert f'"{path}"' in html
        assert (ROOT / path).is_file()
    assert '<base href="__OHPA_BASE__">' in html
    assert "Open HeatPump Analytics" in html
    for path in [ROOT / "static/branding/app-icon.svg", *(ROOT / "branding/logos").glob("*.svg")]:
        assert ElementTree.parse(path).getroot().tag.endswith("svg")
    palette = json.loads((ROOT / "branding/tokens.json").read_text())
    css = (ROOT / "static/branding/tokens.css").read_text()
    assert all(color in css for color in palette.values())
    assert "prefers-color-scheme: dark" in css
    assert "chartRoles" in (ROOT / "static/app.js").read_text()
