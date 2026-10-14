"""Profession and everyday clothing drawings."""
from clothing_art_base import *  # noqa: F401,F403


# ---------------------------------------------------------------- hats

def beanie(base, shade, pom=None):
    parts = []
    if pom:
        parts.append(circ(256, 44, 20, pom))
    parts += [path("M180 130 A76 76 0 0 1 332 130 Z", base),
              path("M256 54 A76 76 0 0 1 332 130 L256 130 Z", shade),
              rect(172, 116, 168, 32, shade, 16),
              line("M196 132 H316", base, 4)]
    return parts


def cap(base, shade, visor, logo=None):
    parts = [path("M182 126 A74 74 0 0 1 330 126 L330 136 L182 136 Z", base),
             path("M256 52 A74 74 0 0 1 330 126 L256 126 Z", shade),
             rect(178, 124, 156, 18, shade, 9),
             path("M300 128 Q392 126 382 148 Q330 154 300 142 Z", visor)]
    if logo:
        parts.append(circ(256, 98, 10, logo))
    return parts


HATS = {
    "Chef Toque": (250, "A tall white toque for a master chef.", [
        circ(204, 88, 30, W), circ(256, 70, 38, W), circ(308, 88, 30, W),
        rect(186, 106, 140, 40, W, 10), rect(186, 134, 140, 12, FURD, 6),
        line("M226 112 V132 M256 112 V132 M286 112 V132", FURD, 4)]),
    "Firefighter Helmet": (350, "Keeps the head safe when things get hot.", [
        path("M170 132 A86 86 0 0 1 342 132 Z", R), path("M256 46 A86 86 0 0 1 342 132 L256 132 Z", RD),
        rect(246, 44, 20, 70, RD, 10), rect(156, 122, 200, 22, RD, 11),
        path("M228 78 L284 78 L292 112 L220 112 Z", G), path("M256 84 L270 100 H242 Z", GD)]),
    "Hard Hat": (300, "Yellow site-safety helmet. Safety first.", [
        path("M172 134 A84 84 0 0 1 340 134 Z", G), path("M256 50 A84 84 0 0 1 340 134 L256 134 Z", GD),
        rect(238, 48, 36, 80, GD, 12), rect(150, 124, 212, 22, GD, 11), rect(238, 52, 36, 8, G, 4)]),
    "Police Cap": (320, "Officer cap with a shiny badge.", [
        path("M178 128 Q178 66 256 64 Q334 66 334 128 Z", DEND), path("M256 64 Q334 66 334 128 L256 128 Z", "#27415F"),
        rect(172, 108, 168, 22, INK, 6), ell(256, 140, 96, 14, INK),
        path("M256 82 l10 8 -4 12 h-12 l-4 -12 Z", G)]),
    "Pilot Cap": (330, "Captain's cap with golden wings.", [
        path("M176 126 Q178 68 256 66 Q334 68 336 126 Z", DEN), path("M256 66 Q334 68 336 126 L256 126 Z", DEND),
        rect(172, 110, 168, 20, SLD, 8), ell(256, 138, 92, 12, SLD),
        path("M228 98 L256 88 L284 98 L256 108 Z", G), circ(256, 98, 5, GD)]),
    "Surgeon Cap": (220, "Mint scrub cap for the operating room.", [
        path("M176 140 A80 80 0 0 1 336 140 Z", MINT), path("M256 60 A80 80 0 0 1 336 140 L256 140 Z", MINTD),
        rect(172, 124, 168, 20, MINTD, 10), circ(334, 138, 9, MINT), line("M338 144 L352 164", MINT, 6)]),
    "Space Helmet": (600, "Pressurised helmet with a mirrored visor.", [
        circ(256, 160, 112, ICE, ' opacity="0.28"'), ring(256, 160, 112, W, 18), ring(256, 160, 100, ICED, 6),
        line("M196 120 Q220 96 252 94", W, 8),
        rect(176, 236, 160, 24, W, 12), rect(176, 248, 160, 12, FURD, 6)]),
    "Straw Hat": (240, "Wide-brim straw hat for a day in the field.", [
        ell(256, 134, 100, 24, GD), path("M196 134 A60 66 0 0 1 316 134 Z", G),
        path("M256 68 A60 66 0 0 1 316 134 L256 134 Z", GD), rect(196, 112, 120, 14, R)]),
    "Wizard Hat": (550, "Pointy hat for those who read ancient books.", [
        path("M172 142 L256 12 L340 142 Z", DEN), path("M256 12 L340 142 L256 142 Z", DEND),
        ell(256, 142, 100, 18, DEND), rect(176, 120, 160, 16, G),
        star(240, 84, 12, G), star(278, 62, 8, G), star(286, 108, 7, GD)]),
    "Pirate Hat": (480, "Three corners, one skull and a lot of treasure.", [
        path("M150 142 Q256 6 362 142 Q256 118 150 142 Z", INK), path("M256 32 Q320 60 362 142 Q300 124 256 118 Z", SLD),
        line("M156 138 Q256 114 356 138", G, 6),
        circ(256, 88, 14, W), rect(246, 98, 20, 10, W, 3), circ(250, 86, 3.5, INK), circ(262, 86, 3.5, INK),
        line("M232 112 L280 70 M280 112 L232 70", W, 4)]),
    "Sailor Cap": (200, "A neat white cap for a sailor on shore leave.", [
        path("M172 134 A84 78 0 0 1 340 134 Z", W), path("M256 56 A84 78 0 0 1 340 134 L256 134 Z", FURD),
        rect(160, 118, 192, 28, DEND, 14), rect(160, 128, 192, 6, W)]),
    "Graduation Cap": (420, "Mortarboard and tassel: top of the class.", [
        rect(198, 100, 116, 40, SLD, 12), path("M150 96 L256 58 L362 96 L256 134 Z", INK),
        path("M256 58 L362 96 L256 134 Z", SLD), line("M256 96 L346 100 V132", G, 5), rect(340, 128, 12, 26, G, 5)]),
    "Cowboy Hat": (350, "Ten-gallon hat with a golden band.", [
        path("M146 132 Q256 164 366 132 Q340 110 256 116 Q172 110 146 132 Z", BRN),
        path("M188 126 Q194 58 256 62 Q318 58 324 126 Z", BRN), path("M256 62 Q318 58 324 126 L256 126 Z", BRND),
        rect(190, 108, 134, 14, G)]),
    "Traffic Cone Hat": (150, "A bright orange safety traffic cone worn proudly on the head.", [
        path("M196 140 L256 22 L316 140 Z", ORG), path("M256 22 L316 140 L256 140 Z", ORGD),
        path("M224 84 L288 84 L296 100 L216 100 Z", W), rect(168, 134, 176, 18, ORGD, 9)]),
    "Festival Cowboy Hat": (350, "A festival cowboy hat in cola red.", [
        path("M146 132 Q256 164 366 132 Q340 110 256 116 Q172 110 146 132 Z", RD),
        path("M188 126 Q194 58 256 62 Q318 58 324 126 Z", R), path("M256 62 Q318 58 324 126 L256 126 Z", RD),
        rect(190, 108, 134, 14, W), circ(256, 115, 7, G)]),
    "Denim Baseball Cap": (250, "A classic baseball cap in blue denim.", cap(DEN, DEND, DEND, W)),
    "Fest Snapback": (200, "Festival snapback in white and red.", cap(W, FURD, R, R)),
    "Slate Flat Cap": (300, "A flat cap for a quiet stroll.", [
        path("M170 130 Q180 84 256 80 Q336 84 344 130 Q256 150 170 130 Z", SL),
        path("M256 80 Q336 84 344 130 Q300 142 256 140 Z", SLD),
        path("M318 124 Q380 126 372 140 Q340 148 310 138 Z", SLD), circ(256, 94, 5, G)]),
    "Olive Beanie": (300, "Warm olive knit beanie.", beanie(OL, OLD)),
    "Denim Beanie": (300, "Blue knit beanie.", beanie(DEN, DEND)),
    "Cola Red Beanie": (300, "Cola red knit beanie with a pom-pom.", beanie(R, RD, W)),
    "Fitted Ice Beanie": (300, "Icy blue beanie, fits snug.", beanie(ICE, ICED)),
    "Mint Beret": (300, "A tilted mint beret.", [
        ell(256, 112, 92, 38, MINT), path("M256 74 Q348 80 348 112 Q320 140 256 150 Z", MINTD),
        rect(170, 118, 172, 22, MINTD, 11), circ(256, 70, 8, MINTD)]),
    "Mint Bucket Hat": (250, "A relaxed mint bucket hat.", [
        path("M186 128 L196 66 Q256 54 316 66 L326 128 Z", MINT), path("M256 58 L316 66 L326 128 L256 128 Z", MINTD),
        ell(256, 130, 100, 20, MINTD), rect(190, 112, 132, 12, W)]),
    "Festival Top Hat": (400, "Tall top hat with a red ribbon.", [
        rect(196, 22, 120, 108, INK, 10), rect(256, 22, 60, 108, SLD, 10), ell(256, 132, 100, 16, INK),
        rect(196, 100, 120, 20, R), rect(196, 112, 120, 8, RD)]),
    "Golden Crown": (500, "A crown fit for the king of the festival.", [
        path("M178 140 L190 62 L222 100 L256 50 L290 100 L322 62 L334 140 Z", G),
        path("M256 50 L290 100 L322 62 L334 140 L256 140 Z", GD), rect(176, 128, 160, 20, GD, 8),
        circ(190, 62, 8, R), circ(256, 50, 8, R), circ(322, 62, 8, R), circ(256, 138, 7, W)]),
}


# ---------------------------------------------------------------- tops

def top(base, sleeve, *extras, short=False):
    h = 62 if short else 104
    return [rect(112, 286, 52, h, sleeve, 26), rect(348, 286, 52, h, sleeve, 26), path(TORSO, base)] + list(extras)


TOPS = {
    "Doctor Coat": (400, "A clean white coat with a stethoscope.", top(
        W, ICE, path("M224 284 L256 342 L288 284 Z", MINT), line("M256 342 V490", ICED, 4),
        rect(168, 420, 52, 40, ICE, 8), rect(292, 420, 52, 40, ICE, 8),
        line("M222 292 C208 344 240 366 256 354", INK, 5), circ(256, 354, 8, ICED))),
    "Chef Jacket": (380, "Double-breasted chef jacket.", top(
        W, FURD, path("M222 282 L290 282 L256 324 Z", R),
        *[circ(x, y, 7, INK) for x in (230, 282) for y in (368, 408, 448)], line("M256 330 V490", FURD, 4))),
    "Firefighter Jacket": (450, "Heavy jacket with reflective stripes.", top(
        R, RD, rect(150, 404, 212, 18, G), rect(150, 436, 212, 10, G), rect(112, 330, 52, 14, G), rect(348, 330, 52, 14, G),
        rect(252, 296, 8, 196, RD), path("M214 284 L256 316 L298 284 L284 272 L256 290 L228 272 Z", RD))),
    "Police Uniform": (420, "Uniform with a golden badge.", top(
        SL, SLD, path("M224 284 L256 332 L288 284 Z", W), rect(250, 304, 12, 76, INK, 6),
        path("M296 340 h22 v20 q0 14 -11 20 q-11 -6 -11 -20 Z", G), rect(116, 300, 42, 20, G, 6), rect(354, 300, 42, 20, G, 6))),
    "Construction Vest": (350, "High-visibility orange vest.", top(
        ORG, SL, rect(196, 296, 18, 196, G), rect(298, 296, 18, 196, G), rect(150, 440, 212, 14, G),
        path("M224 284 L256 330 L288 284 L274 272 L256 296 L238 272 Z", ORGD))),
    "Pilot Jacket": (440, "Bomber jacket with captain's stripes.", top(
        SL, SLD, rect(112, 334, 52, 8, G), rect(112, 350, 52, 8, G), rect(348, 334, 52, 8, G), rect(348, 350, 52, 8, G),
        path("M214 282 Q256 336 298 282 Q256 296 214 282 Z", W), rect(252, 310, 8, 182, SLD))),
    "Space Suit": (650, "Mission-ready space suit.", top(
        W, ICE, rect(206, 332, 100, 72, ICE, 12), circ(232, 354, 8, R), circ(256, 354, 8, G), circ(280, 354, 8, DEN),
        rect(120, 310, 36, 22, R, 4), rect(150, 458, 212, 14, DEN), rect(236, 380, 40, 10, ICED, 4))),
    "Sailor Shirt": (320, "Striped shirt with a navy collar.", top(
        W, W, *[rect(150, y, 212, 12, DEND) for y in (338, 372, 406, 440)],
        rect(112, 314, 52, 10, DEND), rect(348, 314, 52, 10, DEND),
        path("M200 284 L256 352 L312 284 L292 274 L256 314 L220 274 Z", DEND), circ(256, 336, 7, R))),
    "Farmer Overalls Top": (330, "Red plaid shirt under denim bib overalls.", top(
        R, RD, rect(196, 340, 120, 152, DEN, 14), rect(196, 288, 20, 62, DEN), rect(296, 288, 20, 62, DEN),
        circ(206, 350, 7, G), circ(306, 350, 7, G), rect(226, 408, 60, 40, DEND, 8),
        line("M150 340 H196 M316 340 H362 M150 400 H196 M316 400 H362", RD, 6))),
    "Referee Shirt": (300, "Black and white stripes. Whistle not included.", top(
        INK, INK, *[rect(x, 296, 16, 196, W) for x in (176, 224, 272, 320)],
        rect(124, 286, 10, 104, W), rect(142, 286, 10, 104, W), rect(360, 286, 10, 104, W), rect(378, 286, 10, 104, W))),
    "Basketball Jersey": (350, "Sleeveless jersey with a big number one.", [
        path(TORSO, R), path("M200 284 A56 40 0 0 0 312 284 L296 284 A40 26 0 0 1 216 284 Z", W),
        rect(150, 452, 212, 12, W), rect(250, 366, 16, 64, W, 4), path("M232 380 L250 366 V384 Z", W)]),
    "Scrubs Top": (260, "Comfortable mint scrubs.", top(
        MINT, MINTD, path("M222 282 L256 330 L290 282 Z", MINTD), rect(290, 392, 46, 34, MINTD, 6), short=True)),
    "Pirate Shirt": (380, "Loose white shirt with a red sash.", top(
        W, FURD, rect(150, 450, 212, 30, R), path("M222 282 L256 336 L290 282 Z", FURD),
        line("M240 300 L272 312 M240 320 L272 332", INK, 3))),
    "Emo Striped Tee": (250, "Black tee with red stripes.", top(
        INK, INK, *[rect(150, y, 212, 14, R) for y in (346, 384, 422, 460)], short=True)),
}


# ---------------------------------------------------------------- bottoms

def pants(base, shade, *extras, band=None):
    return [path(LEGS, base), rect(174, 446, 164, 22, band or shade, 11)] + list(extras)


BOTTOMS = {
    "Firefighter Pants": (380, "Heat-proof pants with reflective bands.", pants(
        R, RD, rect(180, 584, 56, 12, G), rect(278, 584, 56, 12, G), rect(180, 604, 56, 6, G), rect(278, 604, 56, 6, G))),
    "Police Trousers": (340, "Dark trousers with a gold side stripe.", pants(
        SL, SLD, rect(176, 470, 8, 178, G), rect(328, 470, 8, 178, G), band=INK)),
    "Chef Checked Pants": (300, "Black and white checked pants.", pants(
        W, FURD, *([rect(x, y, 18, 18, INK) for x in (190, 226, 288, 308) for y in (486, 540, 594)] +
                   [rect(x, y, 18, 18, INK) for x in (208, 290) for y in (513, 567)]), band=ICED)),
    "Scrubs Pants": (240, "Comfortable mint scrub pants.", pants(
        MINT, MINTD, rect(186, 500, 40, 34, MINTD, 8), band=MINTD)),
    "Work Pants": (320, "Tough work pants with kneepads.", pants(
        OL, OLD, rect(188, 566, 42, 36, ORG, 10), rect(282, 566, 42, 36, ORG, 10), rect(186, 500, 40, 34, OLD, 8))),
    "Space Suit Pants": (500, "Suit trousers with a mission stripe.", pants(
        W, FURD, rect(174, 446, 164, 22, DEN, 11), rect(176, 470, 8, 178, R), rect(328, 470, 8, 178, R),
        rect(188, 566, 42, 30, ICE, 10), rect(282, 566, 42, 30, ICE, 10))),
    "Farmer Jeans": (310, "Patched jeans with rolled cuffs.", pants(
        DEN, DEND, rect(190, 540, 34, 34, G, 6), rect(180, 628, 62, 24, DEND, 6), rect(272, 628, 62, 24, DEND, 6))),
    "Pilot Trousers": (330, "Smart trousers with a golden stripe.", pants(
        DEND, "#27415F", rect(176, 470, 6, 176, G), rect(330, 470, 6, 176, G), band=INK)),
    "Sailor Trousers": (280, "White sailor trousers.", pants(
        W, FURD, rect(176, 628, 64, 8, DEND), rect(272, 628, 64, 8, DEND), band=DEND)),
    "Wizard Robe": (500, "A long robe sprinkled with stars.", [
        path("M174 452 L338 452 L352 652 L160 652 Z", DEND), path("M256 452 L338 452 L352 652 L256 652 Z", "#27415F"),
        rect(160, 636, 192, 16, GD, 8), rect(174, 446, 164, 20, G, 10),
        star(206, 520, 11, G), star(300, 566, 9, G), star(232, 598, 8, GD), star(320, 500, 7, GD)]),
    "Referee Shorts": (240, "Black shorts with white stripes.", [
        path("M174 452 L338 452 L336 566 L272 566 L256 508 L240 566 L176 566 Z", INK),
        rect(174, 446, 164, 22, SLD, 11), rect(178, 470, 7, 94, W), rect(327, 470, 7, 94, W)]),
    "Emo Slim Jeans": (330, "Skinny black jeans with a chain.", [
        path("M178 452 L334 452 L318 656 L274 656 L256 530 L238 656 L194 656 Z", SLD),
        rect(178, 446, 156, 20, INK, 10), line("M178 476 Q208 510 206 540", G, 3), circ(206, 544, 4, G)]),
    "Cargo Pants Olive": (320, "Roomy cargo pants.", pants(
        OL, OLD, rect(182, 530, 46, 52, OLD, 8), rect(284, 530, 46, 52, OLD, 8))),
}


# ---------------------------------------------------------------- shoes

def boot(base, shade, accent):
    out = []
    for x in (164, 250):
        out += [path(f"M{x + 6} 628 h80 v82 a14 14 0 0 1 -14 14 h-52 a14 14 0 0 1 -14 -14 Z", base),
                rect(x + 2, 708, 88, 18, shade, 9), rect(x + 6, 628, 80, 14, accent, 6)]
    return out


def clog(base, shade, extras=()):
    out = []
    for x in (164, 250):
        out += [path(f"M{x} 664 h96 v50 a14 14 0 0 1 -14 14 h-68 a14 14 0 0 1 -14 -14 Z", base),
                rect(x, 712, 96, 14, shade, 7)]
    return out + list(extras)


SHOES = {
    "Firefighter Boots": (420, "Rubber boots with a golden band.", boot(INK, RD, G)),
    "Work Boots": (350, "Sturdy brown work boots.", boot(BRN, INK, BRND) + [line("M176 660 H238 M176 676 H238 M262 660 H324 M262 676 H324", W, 3)]),
    "Chef Clogs": (260, "White clogs for a busy kitchen.", clog(W, FURD, [
        circ(190, 686, 5, ICED), circ(212, 686, 5, ICED), circ(276, 686, 5, ICED), circ(298, 686, 5, ICED)])),
    "Police Shoes": (300, "Polished black shoes.", clog(INK, SLD, [line("M178 684 H236 M264 684 H322", W, 4, ' opacity="0.6"')])),
    "Scrub Clogs": (240, "Comfortable mint clogs.", clog(MINT, MINTD, [rect(172, 662, 80, 10, MINTD, 5), rect(258, 662, 80, 10, MINTD, 5)])),
    "Space Boots": (480, "Moon-walking boots.", boot(W, R, DEN)),
    "Rain Boots": (260, "Bright yellow rain boots.", boot(G, GD, GD)),
    "Cowboy Boots": (420, "Brown boots with golden stitching.", boot(BRN, BRND, G) + [line("M184 668 L222 700 M270 668 L308 700", G, 3)]),
    "Pilot Boots": (360, "Leather flight boots with straps.", boot(SL, SLD, G)),
    "Polar Treads": (350, "Chunky ice-grip treads.", [
        path("M162 660 h104 v48 a16 16 0 0 1 -16 16 h-72 a16 16 0 0 1 -16 -16 Z", ICE),
        path("M246 660 h104 v48 a16 16 0 0 1 -16 16 h-72 a16 16 0 0 1 -16 -16 Z", ICE),
        rect(158, 712, 112, 18, SL, 9), rect(242, 712, 112, 18, SL, 9),
        line("M176 721 H252 M260 721 H336", ICED, 3), rect(176, 676, 76, 8, ICED, 4), rect(262, 676, 76, 8, ICED, 4)]),
}


# ---------------------------------------------------------------- accessories

HEART = "M{x} 180 C{a} 162 {a} 142 {b} 142 C{c} 142 {x} 148 {x} 150 C{x} 148 {d} 142 {e} 142 C{f} 142 {f} 162 {x} 180 Z"


def heart(cx, fill):
    return path(HEART.format(x=cx, a=cx - 24, b=cx - 10, c=cx - 4, d=cx + 4, e=cx + 10, f=cx + 24), fill)


ACCESSORIES = {
    "Safety Goggles": (180, "Clear goggles for the lab.", [
        rect(188, 138, 136, 46, ICE, 22, ' opacity="0.35"'), frame(188, 138, 136, 46, 22, ICED, 8),
        rect(250, 150, 12, 22, ICED, 4), rect(180, 154, 12, 14, INK, 4), rect(320, 154, 12, 14, INK, 4)]),
    "Surgical Mask": (160, "Mint surgical mask.", [
        path("M204 194 H308 V228 Q256 248 204 228 Z", MINT), line("M214 208 H298 M214 218 H298", MINTD, 3),
        line("M204 198 L192 178 M308 198 L320 178", ICE, 4)]),
    "Quarantine Mask": (150, "A plain white face mask.", [
        path("M204 194 H308 V228 Q256 248 204 228 Z", W), line("M214 208 H298 M214 218 H298", FURD, 3),
        line("M204 198 L190 176 M308 198 L322 176", FURD, 4)]),
    "Cyber Full-Face Mask": (480, "A glowing full-face visor from the future.", [
        path("M196 128 H316 V210 Q256 244 196 210 Z", SLD), rect(206, 148, 100, 22, MINT, 11),
        rect(214, 154, 40, 6, W, 3, ' opacity="0.7"'), line("M216 196 H296", MINT, 4), line("M236 208 H276", MINT, 4)]),
    "Monocle": (200, "A gentleman's monocle.", [
        circ(292, 158, 22, ICE, ' opacity="0.3"'), ring(292, 158, 22, G, 5), line("M310 174 C322 200 318 226 304 240", G, 3)]),
    "Scientist Glasses": (200, "Round glasses for big ideas.", [
        circ(220, 158, 26, ICE, ' opacity="0.25"'), circ(292, 158, 26, ICE, ' opacity="0.25"'),
        ring(220, 158, 26, INK, 6), ring(292, 158, 26, INK, 6), line("M246 156 H266", INK, 6)]),
    "Pilot Goggles": (260, "Brass-rimmed flight goggles.", [
        circ(218, 158, 28, ICE, ' opacity="0.5"'), circ(294, 158, 28, ICE, ' opacity="0.5"'),
        ring(218, 158, 28, GD, 9), ring(294, 158, 28, GD, 9), line("M246 158 H266", GD, 8), line("M190 150 H176 M322 150 H336", SLD, 8)]),
    "Big Mustache": (120, "An impressive mustache.", [
        path("M256 212 C242 192 210 200 202 224 C224 216 242 222 256 212 C270 222 288 216 310 224 C302 200 270 192 256 212 Z", INK)]),
    "Pirate Eyepatch": (140, "Arrr. Eyepatch included.", [
        ell(292, 160, 22, 18, INK), line("M272 146 L194 124 M312 150 L336 136", INK, 5)]),
    "Heart Glasses": (180, "Rose-tinted glasses.", [heart(220, R), heart(292, R), line("M240 156 H272", RD, 5)]),
    "3D Glasses": (170, "Red and blue cinema glasses.", [
        rect(190, 140, 58, 40, R, 8, ' opacity="0.7"'), rect(264, 140, 58, 40, DEN, 8, ' opacity="0.7"'),
        frame(190, 140, 58, 40, 8, W, 6), frame(264, 140, 58, 40, 8, W, 6), line("M248 156 H264", W, 6)]),
    "Round Shades": (200, "Round black shades with golden rims.", [
        circ(220, 158, 26, INK), circ(292, 158, 26, INK), ring(220, 158, 26, G, 5), ring(292, 158, 26, G, 5),
        line("M246 156 H266", G, 5), rect(204, 148, 14, 6, W, 3, ' opacity="0.5"')]),
}


# ---------------------------------------------------------------- hair

def crew(base, shade):
    return [path("M162 150 A94 94 0 0 1 350 150 L350 128 A94 94 0 0 0 162 128 Z", base),
            path("M162 132 A94 94 0 0 1 350 132 L350 112 A94 94 0 0 0 162 112 Z", shade)]


HAIR = {
    "Bob Cut": (250, "A neat bob.", [
        path("M156 176 A100 100 0 0 1 356 176 L356 220 Q356 238 336 238 L330 150 Q256 118 182 150 L176 238 Q156 238 156 220 Z", SLD),
        path("M168 144 Q256 84 344 144 Q256 120 168 144 Z", SL)]),
    "Long Waves": (300, "Long golden waves.", [
        path("M156 170 A100 100 0 0 1 356 170 Q300 118 256 126 Q212 118 156 170 Z", G),
        path("M164 150 Q140 214 160 268 Q184 276 192 252 L186 150 Z", GD), path("M348 150 Q372 214 352 268 Q328 276 320 252 L326 150 Z", GD)]),
    "Pigtails": (250, "Two cheerful pigtails.", crew(MINT, MINTD) + [
        circ(150, 182, 30, MINT), circ(362, 182, 30, MINT), circ(158, 150, 9, R), circ(354, 150, 9, R)]),
    "Big Afro": (300, "Big, bold and bouncy.", [
        circ(190, 118, 44, SLD), circ(256, 86, 52, SLD), circ(322, 118, 44, SLD), circ(160, 170, 30, SLD), circ(352, 170, 30, SLD),
        circ(256, 108, 30, SL, ' opacity="0.6"')]),
    "Spiky Hair": (260, "Icy spikes.", [
        path("M162 140 L170 84 L200 112 L216 64 L246 104 L270 58 L296 104 L324 70 L336 114 L352 90 L350 140 Q256 110 162 140 Z", ICE),
        path("M270 58 L296 104 L324 70 L336 114 L352 90 L350 140 Q300 118 270 120 Z", ICED)]),
    "Ponytail": (260, "A sporty ponytail.", crew(GD, G) + [
        path("M340 120 Q404 130 396 204 Q384 254 350 244 Q384 184 332 154 Z", GD), circ(340, 126, 9, R)]),
    "Top Knot": (240, "A tidy top knot.", crew(SL, SLD) + [circ(256, 62, 28, SLD), circ(256, 62, 12, SL), rect(236, 86, 40, 10, R, 5)]),
    "Crimson Mohawk": (300, "Loud and proud.", [
        path("M228 152 L222 72 L244 98 L256 40 L268 98 L290 72 L284 152 Z", R), path("M256 40 L268 98 L290 72 L284 152 L256 152 Z", RD)]),
    "Emo Swoop": (260, "A long side-swept fringe.", [
        path("M160 152 Q160 70 256 66 Q352 70 352 152 Q300 112 236 132 Q196 148 190 196 Q166 184 160 152 Z", SLD),
        path("M256 66 Q352 70 352 152 Q300 112 256 124 Z", INK)]),
}
