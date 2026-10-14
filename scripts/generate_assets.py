"""
Draw the avatar and every clothing item, as layered SVG.

    python scripts/generate_assets.py

Writes media/avatar/*.svg and media/clothing/<slot>/<slug>.svg (plus a
cropped .thumb.svg per item). The output is committed, so neither Docker nor
the server ever runs this — it exists so the art can be re-tuned by editing a
few numbers rather than by hand-editing forty-eight files.

## Why the art is generated at all

The vendored seeds point at https://mycolabear.example.com, a domain that does
not exist, so every item rendered as a broken image. Real illustration is a
design job; this is a coherent placeholder set that ships, in one style, that
a designer can replace file by file through the admin panel without touching
code.

## The one idea that makes layering work

Every layer — the bear and all 24 garments — is an SVG with the SAME
`viewBox="0 0 512 768"`, and each garment is drawn where it belongs in that
shared space. Rendering an outfit is therefore just stacking the files on top
of each other in slot order: no per-item offsets, no anchor metadata, no
alignment code in the client. Adding a garment means drawing inside the right
anchor box below and nothing else.

Anchor boxes (a new item should stay inside its slot's box):

    HEAD   x 156-356, y  60-260     hair, hats
    EYES   x 196-316, y 150-200     glasses
    TORSO  x 146-366, y 255-485     tops
    HIPS   x 166-346, y 440-650     bottoms
    FEET   x 156-356, y 620-730     shoes

Thumbnails reuse the exact same shapes with the viewBox narrowed to the
anchor box, so the shop grid shows the garment filling the tile instead of a
speck on a mostly-empty 512x768 canvas — from one definition, which cannot
drift from what the avatar wears.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MEDIA = ROOT / "media"

# --- Palette ---------------------------------------------------------------
# Cola Fest. Two tones per shape (base + shadow), no gradients, no outlines —
# shapes read by silhouette, which is what keeps 24 items looking like one set.
RED = "#E4002B"
RED_DEEP = "#A5001F"
WHITE = "#FFFFFF"
FUR = "#F4EFE6"
FUR_SHADE = "#DCD3C4"
INK = "#1A1A1A"
GOLD = "#F2C230"
DENIM = "#4A6FA5"
DENIM_DEEP = "#33527E"
SLATE = "#3C4652"
SLATE_DEEP = "#2A323C"
ICE = "#BFE3F2"
ICE_DEEP = "#8CC4DC"
MINT = "#37C2A6"
MINT_DEEP = "#28A48C"
GOLD_DEEP = "#E0A81E"
OLIVE = "#6E7A4F"
OLIVE_DEEP = "#57603D"

# Anchor boxes, as thumbnail viewBoxes (x y w h) with a little breathing room.
THUMB = {
    "hair": "146 40 220 180",
    "hat": "136 20 240 190",
    "accessory": "176 130 160 100",
    "top": "100 240 312 260",
    "bottom": "156 430 200 240",
    "shoes": "146 600 220 150",
}


def svg(view_box: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" '
        f'fill="none">\n{body}\n</svg>\n'
    )


# --- The bear --------------------------------------------------------------


def base_back() -> str:
    """Everything that sits behind the bear: the ground shadow.

    Its own layer so the shadow stays under the shoes rather than on top of
    them, without the shoes having to know it exists.
    """
    return (
        f'  <ellipse cx="256" cy="726" rx="150" ry="26" fill="{INK}" '
        f'opacity="0.10"/>'
    )


def base() -> str:
    """The polar bear itself — head, ears, muzzle, body, arms, legs, feet."""
    return "\n".join(
        [
            # Arms first so the torso covers where they meet the body.
            f'  <rect x="112" y="286" width="50" height="176" rx="25" fill="{FUR_SHADE}"/>',
            f'  <rect x="350" y="286" width="50" height="176" rx="25" fill="{FUR_SHADE}"/>',
            # Legs.
            f'  <rect x="182" y="452" width="64" height="212" rx="32" fill="{FUR_SHADE}"/>',
            f'  <rect x="266" y="452" width="64" height="212" rx="32" fill="{FUR_SHADE}"/>',
            # Feet.
            f'  <ellipse cx="214" cy="678" rx="54" ry="34" fill="{FUR}"/>',
            f'  <ellipse cx="298" cy="678" rx="54" ry="34" fill="{FUR}"/>',
            # Torso.
            f'  <rect x="146" y="255" width="220" height="234" rx="72" fill="{FUR}"/>',
            f'  <ellipse cx="256" cy="404" rx="72" ry="62" fill="{FUR_SHADE}" opacity="0.55"/>',
            # Ears.
            f'  <circle cx="181" cy="96" r="36" fill="{FUR}"/>',
            f'  <circle cx="331" cy="96" r="36" fill="{FUR}"/>',
            f'  <circle cx="181" cy="96" r="18" fill="{FUR_SHADE}"/>',
            f'  <circle cx="331" cy="96" r="18" fill="{FUR_SHADE}"/>',
            # Head.
            f'  <circle cx="256" cy="164" r="96" fill="{FUR}"/>',
            # Muzzle.
            f'  <ellipse cx="256" cy="208" rx="52" ry="38" fill="{WHITE}"/>',
            f'  <ellipse cx="256" cy="192" rx="17" ry="12" fill="{INK}"/>',
            f'  <path d="M256 204 v14" stroke="{INK}" stroke-width="5" '
            f'stroke-linecap="round"/>',
            # Eyes.
            f'  <circle cx="220" cy="158" r="10" fill="{INK}"/>',
            f'  <circle cx="292" cy="158" r="10" fill="{INK}"/>',
            f'  <circle cx="223" cy="154" r="3.5" fill="{WHITE}"/>',
            f'  <circle cx="295" cy="154" r="3.5" fill="{WHITE}"/>',
        ]
    )


# --- Clothing --------------------------------------------------------------
# Each entry: (slug, slot, svg body). Names/prices live in the migration that
# seeds them; this file is only about what they look like.


def hair_crew_cut() -> str:
    return "\n".join([
        f'  <path d="M162 150 A94 94 0 0 1 350 150 L350 128 A94 94 0 0 0 162 128 Z" fill="{SLATE}"/>',
        f'  <path d="M162 132 A94 94 0 0 1 350 132 L350 112 A94 94 0 0 0 162 112 Z" fill="{SLATE_DEEP}"/>',
    ])


def hair_windblown() -> str:
    return "\n".join([
        f'  <path d="M160 148 C168 74 250 52 306 74 C280 84 268 96 264 108 '
        f'C300 92 348 100 366 130 C336 122 306 128 288 142 Z" fill="{SLATE}"/>',
        f'  <path d="M186 96 C214 72 262 66 292 78 C258 80 222 88 200 106 Z" fill="{SLATE_DEEP}"/>',
    ])


def hair_cola_curls() -> str:
    return "\n".join([
        f'  <circle cx="196" cy="118" r="30" fill="{RED_DEEP}"/>',
        f'  <circle cx="248" cy="96" r="34" fill="{RED}"/>',
        f'  <circle cx="304" cy="112" r="30" fill="{RED_DEEP}"/>',
        f'  <circle cx="336" cy="146" r="24" fill="{RED}"/>',
        f'  <circle cx="172" cy="152" r="24" fill="{RED}"/>',
    ])


def hair_faux_hawk() -> str:
    return "\n".join([
        f'  <path d="M256 44 L292 128 L220 128 Z" fill="{MINT}"/>',
        f'  <path d="M220 128 L292 128 L306 152 L206 152 Z" fill="{MINT}"/>',
        f'  <path d="M256 44 L256 128 L220 128 Z" fill="{MINT_DEEP}"/>',
        f'  <path d="M206 152 L306 152 L300 166 L212 166 Z" fill="{MINT_DEEP}"/>',
    ])


def hat_bucket() -> str:
    return "\n".join([
        f'  <path d="M186 118 A70 70 0 0 1 326 118 L326 132 L186 132 Z" fill="{GOLD}"/>',
        f'  <ellipse cx="256" cy="136" rx="106" ry="26" fill="{GOLD_DEEP}"/>',
        f'  <rect x="186" y="112" width="140" height="16" fill="{GOLD_DEEP}"/>',
    ])


def hat_toque() -> str:
    return "\n".join([
        f'  <circle cx="256" cy="42" r="20" fill="{WHITE}"/>',
        f'  <path d="M180 122 A76 76 0 0 1 332 122 Z" fill="{RED}"/>',
        f'  <rect x="172" y="118" width="168" height="30" rx="15" fill="{WHITE}"/>',
    ])


def hat_snapback() -> str:
    return "\n".join([
        f'  <path d="M182 120 A74 74 0 0 1 330 120 L330 130 L182 130 Z" fill="{RED}"/>',
        f'  <path d="M256 46 A74 74 0 0 1 330 120 L256 120 Z" fill="{RED_DEEP}"/>',
        f'  <rect x="178" y="118" width="212" height="22" rx="11" fill="{RED_DEEP}"/>',
        f'  <circle cx="256" cy="52" r="7" fill="{WHITE}"/>',
    ])


def hat_crown() -> str:
    return "\n".join([
        f'  <path d="M176 132 L176 56 L212 96 L256 40 L300 96 L336 56 L336 132 Z" fill="{GOLD}"/>',
        f'  <rect x="176" y="126" width="160" height="24" rx="8" fill="{GOLD_DEEP}"/>',
        f'  <circle cx="256" cy="138" r="9" fill="{RED}"/>',
        f'  <circle cx="204" cy="138" r="7" fill="{RED_DEEP}"/>',
        f'  <circle cx="308" cy="138" r="7" fill="{RED_DEEP}"/>',
    ])


def _tee(colour: str, shade: str) -> list[str]:
    """The shared tee silhouette: torso panel plus two sleeves."""
    return [
        f'  <rect x="112" y="286" width="52" height="104" rx="26" fill="{shade}"/>',
        f'  <rect x="348" y="286" width="52" height="104" rx="26" fill="{shade}"/>',
        f'  <path d="M150 300 A62 62 0 0 1 362 300 L362 470 '
        f'A22 22 0 0 1 340 492 L172 492 A22 22 0 0 1 150 470 Z" fill="{colour}"/>',
    ]


def top_classic_tee() -> str:
    return "\n".join(_tee(RED, RED_DEEP) + [
        f'  <path d="M214 282 A46 46 0 0 0 298 282 A70 70 0 0 1 214 282 Z" fill="{RED_DEEP}"/>',
        f'  <path d="M186 372 C220 356 292 356 326 372" stroke="{WHITE}" '
        f'stroke-width="12" stroke-linecap="round"/>',
        f'  <circle cx="256" cy="416" r="20" fill="{WHITE}"/>',
    ])


def top_polar_hoodie() -> str:
    return "\n".join(_tee(SLATE, SLATE_DEEP) + [
        f'  <path d="M196 268 A62 62 0 0 0 316 268 A76 76 0 0 1 196 268 Z" fill="{SLATE_DEEP}"/>',
        f'  <rect x="206" y="404" width="100" height="56" rx="16" fill="{SLATE_DEEP}"/>',
        f'  <path d="M232 296 L240 350 M280 296 L272 350" stroke="{WHITE}" '
        f'stroke-width="8" stroke-linecap="round"/>',
    ])


def top_cold_brew_jacket() -> str:
    return "\n".join(_tee(ICE, ICE_DEEP) + [
        f'  <rect x="246" y="292" width="20" height="200" fill="{ICE_DEEP}"/>',
        f'  <rect x="150" y="300" width="42" height="60" rx="12" fill="{WHITE}"/>',
        f'  <rect x="320" y="300" width="42" height="60" rx="12" fill="{WHITE}"/>',
        f'  <rect x="112" y="330" width="52" height="18" fill="{WHITE}"/>',
        f'  <rect x="348" y="330" width="52" height="18" fill="{WHITE}"/>',
    ])


def top_bottle_cap_vest() -> str:
    return "\n".join([
        f'  <path d="M172 292 A56 56 0 0 1 224 286 L246 340 L246 492 L172 492 '
        f'A22 22 0 0 1 150 470 L150 320 Z" fill="{RED}"/>',
        f'  <path d="M340 292 A56 56 0 0 0 288 286 L266 340 L266 492 L340 492 '
        f'A22 22 0 0 0 362 470 L362 320 Z" fill="{RED_DEEP}"/>',
        f'  <circle cx="256" cy="352" r="30" fill="{GOLD}"/>',
        f'  <circle cx="256" cy="352" r="18" fill="{WHITE}"/>',
    ])


def bottom_shorts() -> str:
    return "\n".join([
        f'  <path d="M176 452 L336 452 L330 560 L272 560 L256 500 L240 560 '
        f'L182 560 Z" fill="{DENIM}"/>',
        f'  <rect x="176" y="446" width="160" height="22" rx="11" fill="{DENIM_DEEP}"/>',
        f'  <path d="M256 500 L256 560" stroke="{DENIM_DEEP}" stroke-width="8"/>',
    ])


def bottom_track_pants() -> str:
    return "\n".join([
        f'  <path d="M176 452 L336 452 L332 648 L272 648 L256 520 L240 648 '
        f'L180 648 Z" fill="{SLATE}"/>',
        f'  <rect x="176" y="446" width="160" height="22" rx="11" fill="{SLATE_DEEP}"/>',
        f'  <path d="M192 470 L188 644 M320 470 L324 644" stroke="{WHITE}" '
        f'stroke-width="9" stroke-linecap="round"/>',
    ])


def bottom_cargo_pants() -> str:
    return "\n".join([
        f'  <path d="M174 452 L338 452 L334 652 L272 652 L256 520 L240 652 '
        f'L178 652 Z" fill="{OLIVE}"/>',
        f'  <rect x="174" y="446" width="164" height="22" rx="11" fill="{OLIVE_DEEP}"/>',
        f'  <rect x="182" y="530" width="46" height="52" rx="8" fill="{OLIVE_DEEP}"/>',
        f'  <rect x="284" y="530" width="46" height="52" rx="8" fill="{OLIVE_DEEP}"/>',
    ])


def bottom_glacier_skirt() -> str:
    return "\n".join([
        f'  <path d="M180 452 L332 452 L356 578 L156 578 Z" fill="{ICE}"/>',
        f'  <rect x="178" y="446" width="156" height="22" rx="11" fill="{ICE_DEEP}"/>',
        f'  <path d="M200 468 L184 574 M256 468 L256 578 M312 468 L328 574" '
        f'stroke="{ICE_DEEP}" stroke-width="7" stroke-linecap="round"/>',
    ])


def _shoes(colour: str, sole: str, height: int = 0) -> list[str]:
    """Both feet at once. `height` lifts the collar for high-tops."""
    return [
        f'  <path d="M162 {664 - height} h104 v46 a16 16 0 0 1 -16 16 h-72 '
        f'a16 16 0 0 1 -16 -16 Z" fill="{colour}"/>',
        f'  <path d="M246 {664 - height} h104 v46 a16 16 0 0 1 -16 16 h-72 '
        f'a16 16 0 0 1 -16 -16 Z" fill="{colour}"/>',
        f'  <ellipse cx="214" cy="712" rx="56" ry="18" fill="{sole}"/>',
        f'  <ellipse cx="298" cy="712" rx="56" ry="18" fill="{sole}"/>',
    ]


def shoes_bubbles() -> str:
    return "\n".join(_shoes(WHITE, ICE_DEEP) + [
        f'  <circle cx="196" cy="682" r="9" fill="{ICE}"/>',
        f'  <circle cx="222" cy="694" r="6" fill="{ICE}"/>',
        f'  <circle cx="290" cy="682" r="9" fill="{ICE}"/>',
        f'  <circle cx="316" cy="694" r="6" fill="{ICE}"/>',
    ])


def shoes_fizzy_kicks() -> str:
    return "\n".join(_shoes(RED, WHITE) + [
        f'  <path d="M176 690 h76 M260 690 h76" stroke="{WHITE}" '
        f'stroke-width="8" stroke-linecap="round"/>',
    ])


def shoes_midnight_high_tops() -> str:
    return "\n".join(_shoes(SLATE_DEEP, RED, height=34) + [
        f'  <path d="M176 656 h76 M260 656 h76 M176 676 h76 M260 676 h76" '
        f'stroke="{WHITE}" stroke-width="6" stroke-linecap="round"/>',
    ])


def shoes_bear_paws() -> str:
    return "\n".join(_shoes(FUR, GOLD) + [
        f'  <circle cx="196" cy="680" r="8" fill="{FUR_SHADE}"/>',
        f'  <circle cx="216" cy="674" r="8" fill="{FUR_SHADE}"/>',
        f'  <circle cx="236" cy="680" r="8" fill="{FUR_SHADE}"/>',
        f'  <circle cx="280" cy="680" r="8" fill="{FUR_SHADE}"/>',
        f'  <circle cx="300" cy="674" r="8" fill="{FUR_SHADE}"/>',
        f'  <circle cx="320" cy="680" r="8" fill="{FUR_SHADE}"/>',
    ])


def glasses_polar_shades() -> str:
    return "\n".join([
        f'  <rect x="192" y="142" width="56" height="34" rx="10" fill="{INK}"/>',
        f'  <rect x="264" y="142" width="56" height="34" rx="10" fill="{INK}"/>',
        f'  <rect x="248" y="154" width="16" height="8" fill="{INK}"/>',
        f'  <rect x="200" y="148" width="18" height="8" rx="4" fill="{WHITE}" opacity="0.5"/>',
    ])


def glasses_ice_cool() -> str:
    return "\n".join([
        f'  <rect x="190" y="140" width="60" height="36" rx="18" fill="{ICE}" opacity="0.9"/>',
        f'  <rect x="262" y="140" width="60" height="36" rx="18" fill="{ICE}" opacity="0.9"/>',
        f'  <rect x="248" y="152" width="16" height="8" fill="{ICE_DEEP}"/>',
        f'  <rect x="186" y="150" width="8" height="12" rx="4" fill="{ICE_DEEP}"/>',
        f'  <rect x="318" y="150" width="8" height="12" rx="4" fill="{ICE_DEEP}"/>',
    ])


def glasses_aviators() -> str:
    return "\n".join([
        f'  <path d="M190 144 h58 l-8 34 h-34 a18 18 0 0 1 -16 -18 Z" fill="{GOLD}"/>',
        f'  <path d="M322 144 h-58 l8 34 h34 a18 18 0 0 0 16 -18 Z" fill="{GOLD}"/>',
        f'  <path d="M248 148 h16" stroke="{GOLD}" stroke-width="6"/>',
        f'  <path d="M194 148 h50 l-7 26 h-28 a14 14 0 0 1 -15 -14 Z" fill="{RED_DEEP}" opacity="0.8"/>',
        f'  <path d="M318 148 h-50 l7 26 h28 a14 14 0 0 0 15 -14 Z" fill="{RED_DEEP}" opacity="0.8"/>',
    ])


def glasses_visor() -> str:
    return "\n".join([
        f'  <path d="M182 140 h148 a14 14 0 0 1 14 14 v10 a34 34 0 0 1 -34 26 '
        f'h-108 a34 34 0 0 1 -34 -26 v-10 a14 14 0 0 1 14 -14 Z" fill="{MINT}"/>',
        f'  <path d="M196 150 h120 a6 6 0 0 1 6 6 v6 a20 20 0 0 1 -20 14 '
        f'h-92 a20 20 0 0 1 -20 -14 v-6 a6 6 0 0 1 6 -6 Z" fill="{WHITE}" opacity="0.35"/>',
    ])


# slug -> (slot, draw function). Slugs are also the on-disk filenames and the
# image_url the seed migration writes, so renaming one means a migration.
ITEMS = {
    "classic-crew-cut": ("hair", hair_crew_cut),
    "windblown-waves": ("hair", hair_windblown),
    "cola-curls": ("hair", hair_cola_curls),
    "neon-faux-hawk": ("hair", hair_faux_hawk),
    "sunrise-bucket-hat": ("hat", hat_bucket),
    "winter-toque-deluxe": ("hat", hat_toque),
    "polar-snapback": ("hat", hat_snapback),
    "fest-crown": ("hat", hat_crown),
    "cola-classic-tee": ("top", top_classic_tee),
    "polar-hoodie": ("top", top_polar_hoodie),
    "limited-cold-brew-jacket": ("top", top_cold_brew_jacket),
    "bottle-cap-vest": ("top", top_bottle_cap_vest),
    "soda-pop-shorts": ("bottom", bottom_shorts),
    "retro-racer-tracksuit-pants": ("bottom", bottom_track_pants),
    "chill-cargo-pants": ("bottom", bottom_cargo_pants),
    "glacier-skirt": ("bottom", bottom_glacier_skirt),
    "bubbles-running-shoes": ("shoes", shoes_bubbles),
    "fizzy-kicks": ("shoes", shoes_fizzy_kicks),
    "midnight-cola-high-tops": ("shoes", shoes_midnight_high_tops),
    "bear-paws": ("shoes", shoes_bear_paws),
    "polar-shades": ("accessory", glasses_polar_shades),
    "ice-cool-sunglasses": ("accessory", glasses_ice_cool),
    "retro-cola-aviators": ("accessory", glasses_aviators),
    "visor-shield": ("accessory", glasses_visor),
}


def main() -> None:
    avatar_dir = MEDIA / "avatar"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    (avatar_dir / "base-back.svg").write_text(svg("0 0 512 768", base_back()), encoding="utf-8")
    (avatar_dir / "base.svg").write_text(svg("0 0 512 768", base()), encoding="utf-8")

    written = 2
    for slug, (slot, draw) in ITEMS.items():
        body = draw()
        slot_dir = MEDIA / "clothing" / slot
        slot_dir.mkdir(parents=True, exist_ok=True)

        # Full layer: drawn in the avatar's coordinate space, stacked as-is.
        (slot_dir / f"{slug}.svg").write_text(svg("0 0 512 768", body), encoding="utf-8")
        # Thumbnail: identical shapes, viewBox cropped to the slot's anchor.
        (slot_dir / f"{slug}.thumb.svg").write_text(
            svg(THUMB[slot], body), encoding="utf-8"
        )
        written += 2

    print(f"Wrote {written} SVG files under {MEDIA}")
    print(f"{len(ITEMS)} clothing items across {len(set(s for s, _ in ITEMS.values()))} slots")


if __name__ == "__main__":
    main()
