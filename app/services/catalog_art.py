"""
Accept clothing artwork submitted as SVG text, and put it on disk.

This exists so a catalog can be filled by something that speaks HTTP and
nothing else — no shell on the server, no admin session, no image pipeline.
An item arrives as one JSON body carrying its own SVG source; this module
decides whether that SVG is safe and correctly shaped, writes it, and derives
the shop thumbnail from it.

## Why the thumbnail is derived rather than uploaded

Every layer shares `viewBox="0 0 512 768"` (see scripts/generate_assets.py) —
that shared coordinate space is the entire reason stacking layers works with
no positioning code anywhere. It also means a thumbnail is not a separate
drawing: it is the same drawing with the viewBox narrowed to the slot's anchor
box. Deriving it removes the failure where a submitted thumbnail slowly stops
matching what the avatar actually wears.

## Why the SVG is validated instead of trusted

The art is served from our own origin and rendered in the Mini App. An SVG
loaded through `<img>` cannot run script in any current browser, so this is
defence in depth rather than the only thing standing between us and trouble —
but the file is written by whoever holds the submission key, served to every
player, and cheap to check. Anything that could fetch, execute, or phone home
is refused rather than sanitised: a rejection tells the submitter to fix their
drawing, while a silent scrub produces art that looks different in the shop
than it did in their editor.
"""
from __future__ import annotations

import pathlib
import re
import unicodedata
from defusedxml import ElementTree as SafeElementTree
from xml.etree.ElementTree import ParseError

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
MEDIA_DIR = ROOT / "media"

# Submitted art lives apart from the art baked into the image. Two reasons:
# a rebuild must not silently revert somebody's upload, and a Docker volume
# mounted over media/clothing would hide the 24 items that ship with the app.
UPLOAD_DIR = MEDIA_DIR / "uploads"
UPLOAD_URL_PREFIX = "/media/uploads"

CANVAS = "0 0 512 768"
MAX_SVG_BYTES = 256 * 1024

# Where each slot's art belongs on the shared canvas. A garment drawn outside
# its box will still render — it will just sit on the bear wrongly — so these
# are published in the spec and checked loosely, not enforced to the pixel.
ANCHORS = {
    "hair": {"x": 156, "y": 60, "width": 200, "height": 200},
    "hat": {"x": 156, "y": 40, "width": 200, "height": 200},
    "accessory": {"x": 196, "y": 150, "width": 120, "height": 50},
    "top": {"x": 146, "y": 255, "width": 220, "height": 230},
    "bottom": {"x": 166, "y": 440, "width": 180, "height": 210},
    "shoes": {"x": 156, "y": 620, "width": 200, "height": 110},
}

# The same boxes as thumbnail viewBoxes, with breathing room. Kept identical
# to scripts/generate_assets.py so uploaded items crop like the shipped ones.
THUMB_VIEW_BOX = {
    "hair": "146 40 220 180",
    "hat": "136 20 240 190",
    "accessory": "176 130 160 100",
    "top": "100 240 312 260",
    "bottom": "156 430 200 240",
    "shoes": "146 600 220 150",
}

# Elements that can fetch, execute, or embed arbitrary HTML.
FORBIDDEN_TAGS = {"script", "foreignobject", "iframe", "embed", "object", "image", "audio", "video", "handler", "set"}

_SVG_OPEN = re.compile(r"^\s*<svg\b[^>]*>", re.IGNORECASE | re.DOTALL)
_SVG_CLOSE = re.compile(r"</svg\s*>\s*$", re.IGNORECASE)


class ArtError(ValueError):
    """The submitted SVG cannot be accepted. The message is shown to the
    submitter, so it says what to change rather than what went wrong."""


def slugify(name: str) -> str:
    """A filename from a display name.

    Accents are folded and everything outside [a-z0-9-] becomes a hyphen, so
    "Ünlü Şapka" and "Fest Tee!!" both produce something that survives a URL,
    a filesystem and a shell without quoting.
    """
    folded = unicodedata.normalize("NFKD", name)
    ascii_only = folded.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()
    return slug or "item"


def validate(svg_text: str) -> str:
    """Check one submitted SVG, returning it unchanged if it is acceptable."""
    if len(svg_text.encode("utf-8")) > MAX_SVG_BYTES:
        raise ArtError(
            f"SVG is larger than {MAX_SVG_BYTES // 1024} KB. Flat shapes in this "
            "style are a few KB; that size usually means an embedded bitmap or "
            "a traced photo."
        )

    lowered = svg_text.lower()
    # Checked on the raw text, before any parser sees it: an entity
    # declaration is how a small document becomes a large one.
    if "<!doctype" in lowered or "<!entity" in lowered:
        raise ArtError("Remove the DOCTYPE / ENTITY declaration; send the <svg> element alone.")

    try:
        root = SafeElementTree.fromstring(svg_text)
    except ParseError as exc:
        raise ArtError(f"Not well-formed XML: {exc}") from exc

    if _local_name(root.tag) != "svg":
        raise ArtError("The root element must be <svg>.")

    view_box = (root.get("viewBox") or "").split()
    if view_box != CANVAS.split():
        raise ArtError(
            f'The root <svg> must carry viewBox="{CANVAS}" exactly. Every layer '
            "shares one canvas — that is what makes the garment land in the "
            "right place with no positioning code."
        )

    for element in root.iter():
        tag = _local_name(element.tag)
        if tag in FORBIDDEN_TAGS:
            raise ArtError(
                f"<{tag}> is not allowed. Draw with shapes and paths only — no "
                "scripts, no embedded documents, no external images."
            )
        for attribute, value in element.attrib.items():
            attribute_name = _local_name(attribute).lower()
            if attribute_name.startswith("on"):
                raise ArtError(f'Event attribute "{attribute}" is not allowed.')
            if attribute_name in {"href", "src"} and not value.strip().startswith("#"):
                raise ArtError(
                    f'"{attribute}" may only point inside the same file (a "#id" '
                    "reference). Nothing may be loaded from another address."
                )
            if "url(" in value.lower() and not re.search(r"url\(\s*['\"]?#", value, re.IGNORECASE):
                raise ArtError(
                    f'"{attribute}" references an external url(). Gradients and '
                    "filters must be defined in the same file and referenced by #id."
                )

    return svg_text


def thumbnail(svg_text: str, slot: str) -> str:
    """The same drawing, cropped to the slot's anchor box.

    Works on the original text rather than a re-serialised tree so that
    namespaces, formatting and anything the author wrote deliberately survive
    untouched — the only change is the viewBox on the root element.
    """
    inner = _SVG_CLOSE.sub("", _SVG_OPEN.sub("", svg_text)).strip()
    view_box = THUMB_VIEW_BOX[slot]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" fill="none">\n'
        f"{inner}\n</svg>\n"
    )


def write(slot: str, slug: str, svg_text: str) -> str:
    """Write the layer and its thumbnail. Returns the public image URL."""
    directory = UPLOAD_DIR / slot
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{slug}.svg").write_text(svg_text, encoding="utf-8")
    (directory / f"{slug}.thumb.svg").write_text(thumbnail(svg_text, slot), encoding="utf-8")
    return f"{UPLOAD_URL_PREFIX}/{slot}/{slug}.svg"


def remove(image_url: str) -> None:
    """Delete art we wrote. Silent when the item's art is not ours to delete
    (a shipped item, or a URL pointing somewhere else entirely)."""
    if not image_url.startswith(UPLOAD_URL_PREFIX + "/"):
        return
    relative = image_url[len(UPLOAD_URL_PREFIX) + 1 :]
    for path in (UPLOAD_DIR / relative, UPLOAD_DIR / relative.replace(".svg", ".thumb.svg")):
        path.unlink(missing_ok=True)


def _local_name(tag: str) -> str:
    """`{http://www.w3.org/2000/svg}rect` -> `rect`."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""
