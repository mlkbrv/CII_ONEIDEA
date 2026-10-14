"""Funny and hero clothing drawings."""
from clothing_art_base import *  # noqa: F401,F403
from clothing_art_work import HEART, boot, clog, pants, top


# ---------------------------------------------------------------- funny and heroes

GRN, GRND = "#2E9B5F", "#1F7A47"
PNK, PNKD = "#F7B2C9", "#E48DAE"
SIL, SILD = "#C9D3DD", "#9AA6B5"
CRUST = "#D9923B"


def small_heart(cx, cy, s, fill):
    d = HEART.format(x=220, a=196, b=210, c=216, d=224, e=230, f=244)
    return f'<path transform="translate({cx} {cy}) scale({s}) translate(-220 -160)" d="{d}" fill="{fill}"/>'


FUN_HATS = {
    "Pizza Slice Hat": (180, "A fresh slice, extra cheese, worn on the head.", [
        path("M198 128 L314 128 L256 28 Z", G), path("M256 28 L314 128 L256 128 Z", GD),
        rect(188, 122, 136, 22, CRUST, 11), circ(242, 92, 11, R), circ(272, 74, 9, R), circ(262, 108, 9, RD), circ(236, 66, 6, OL)]),
    "Rubber Duck Hat": (220, "Quack. The duck is staying.", [
        ell(256, 104, 76, 38, G), circ(304, 62, 32, G), path("M330 54 L366 64 L330 76 Z", ORG), circ(310, 54, 5, INK),
        path("M214 102 Q250 136 288 102 Q250 90 214 102 Z", GD), ell(256, 138, 90, 10, ICE, ' opacity="0.7"')]),
    "Watermelon Hat": (200, "Juicy, green and a little heavy.", [
        path("M170 142 A86 86 0 0 1 342 142 Z", GRN), path("M184 138 A72 72 0 0 1 328 138 Z", R),
        path("M256 56 A72 72 0 0 1 328 138 L256 138 Z", RD), ell(226, 100, 5, 8, INK), ell(256, 84, 5, 8, INK),
        ell(288, 100, 5, 8, INK), ell(240, 120, 5, 8, INK), ell(274, 122, 5, 8, INK), rect(170, 138, 172, 8, GRND, 4)]),
    "Paper Crown": (150, "Fast-food royalty.", [
        path("M180 140 L184 70 L218 100 L256 64 L294 100 L328 70 L332 140 Z", ORG),
        path("M256 64 L294 100 L328 70 L332 140 L256 140 Z", ORGD), rect(180, 118, 152, 22, R, 4),
        circ(204, 129, 5, W), circ(256, 129, 5, W), circ(308, 129, 5, W)]),
    "Light Bulb Hat": (260, "A bright idea.", [
        line("M256 14 V2 M196 34 L186 24 M316 34 L326 24", G, 5),
        circ(256, 62, 42, "#FFF3B0"), ring(256, 62, 42, G, 5), line("M240 70 Q256 40 272 70", GD, 4),
        rect(236, 98, 40, 26, SL, 6), rect(236, 108, 40, 6, SLD)]),
    "Cola Bottle Hat": (300, "A bottle of fizz balancing on your head.", [
        rect(244, 28, 24, 36, RD, 6), rect(226, 58, 60, 70, R, 20), rect(226, 82, 60, 24, W), rect(238, 18, 36, 14, GD, 5),
        rect(204, 124, 104, 18, SLD, 9)]),
    "Dino Hood": (330, "A roaring green hood with spikes.", [
        path("M172 142 A84 82 0 0 1 340 142 Z", GRN), path("M256 60 A84 82 0 0 1 340 142 L256 142 Z", GRND),
        path("M210 72 L222 42 L236 66 Z", GRND), path("M240 62 L256 26 L272 62 Z", GRND), path("M276 66 L290 42 L302 72 Z", GRND),
        circ(216, 102, 14, W), circ(296, 102, 14, W), circ(219, 104, 6, INK), circ(293, 104, 6, INK), rect(172, 128, 168, 14, GRND, 7)]),
    "Winged Helmet": (480, "A silver helmet with little wings.", [
        path("M176 136 A80 74 0 0 1 336 136 Z", SIL), path("M256 62 A80 74 0 0 1 336 136 L256 136 Z", SILD),
        rect(168, 124, 176, 20, SILD, 10), path("M176 104 Q146 94 140 52 Q168 62 186 86 Z", G),
        path("M336 104 Q366 94 372 52 Q344 62 326 86 Z", G), rect(246, 70, 20, 54, SILD, 8)]),
    "Armored Hero Helmet": (650, "Gold and red armor with glowing eyes.", [
        path("M168 130 Q168 62 256 60 Q344 62 344 130 L344 214 Q344 244 312 250 L200 250 Q168 244 168 214 Z", R),
        path("M256 60 Q344 62 344 130 L344 214 Q344 244 312 250 L256 250 Z", RD),
        path("M196 118 H316 V204 Q316 230 290 234 H222 Q196 230 196 204 Z", G), path("M256 118 H316 V204 Q316 230 290 234 H256 Z", GD),
        path("M212 150 L246 156 L246 168 L212 164 Z", W), path("M300 150 L266 156 L266 168 L300 164 Z", W),
        line("M232 206 H280", GD, 4), line("M238 218 H274", GD, 4)]),
    "Night Cowl": (500, "Pointy-eared cowl for patrolling at night.", [
        path("M166 150 Q166 70 256 66 Q346 70 346 150 L346 178 Q300 152 256 170 Q212 152 166 178 Z", SLD),
        path("M256 66 Q346 70 346 150 L346 178 Q300 152 256 170 Z", INK),
        path("M184 80 L174 26 L216 66 Z", SLD), path("M328 80 L338 26 L296 66 Z", INK),
        path("M198 150 L238 160 L228 174 L202 166 Z", W), path("M314 150 L274 160 L284 174 L310 166 Z", W)]),
}

FUN_TOPS = {
    "Dino Costume": (380, "Green dino onesie with a soft belly.", top(
        GRN, GRN, ell(256, 420, 64, 58, "#B7E4B8"), path("M150 330 L132 296 L172 312 Z", GRND), path("M362 330 L380 296 L340 312 Z", GRND),
        circ(188, 400, 9, GRND), circ(326, 372, 9, GRND), circ(196, 452, 7, GRND), circ(318, 456, 7, GRND))),
    "Bow Tie Tee": (260, "A tuxedo printed on a tee. Very formal.", top(
        W, W, path("M200 286 L256 380 L228 290 Z", INK), path("M312 286 L256 380 L284 290 Z", INK),
        path("M256 318 L226 300 V336 Z", R), path("M256 318 L286 300 V336 Z", R), circ(256, 318, 8, RD),
        *[circ(256, y, 5, INK) for y in (396, 424, 452)], short=True)),
    "Medal Jacket": (420, "Covered in medals. Nobody knows what for.", top(
        DEN, DEND, *[circ(x, y, 15, G) for x in (200, 256, 312) for y in (350, 410)] +
        [circ(x, y, 7, R) for x in (200, 256, 312) for y in (350, 410)] + [rect(194, 468, 124, 8, G, 4)])),
    "Hawaiian Shirt": (300, "Loud flowers, relaxed mood.", top(
        MINT, MINTD, circ(196, 360, 16, R), circ(310, 340, 14, G), circ(244, 420, 18, W), circ(320, 440, 15, R), circ(188, 450, 12, G),
        path("M222 282 L256 330 L290 282 Z", MINTD), short=True)),
    "Swim Ring": (240, "An inflatable ring around the belly.", [
        '<ellipse cx="256" cy="400" rx="112" ry="52" stroke="#E4002B" stroke-width="34" fill="none"/>',
        '<ellipse cx="256" cy="400" rx="112" ry="52" stroke="#FFFFFF" stroke-width="34" stroke-dasharray="64 58" fill="none"/>']),
    "Hero Suit": (500, "Blue suit with a golden star on the chest.", top(
        DEN, R, circ(256, 374, 46, G), star(256, 374, 28, R), rect(150, 452, 212, 20, G), rect(112, 300, 52, 12, G), rect(348, 300, 52, 12, G))),
    "Power Armor": (700, "Red and gold armor with a glowing core.", top(
        R, G, circ(256, 366, 30, GD), circ(256, 366, 20, W), ring(256, 366, 30, ICE, 5),
        rect(150, 290, 60, 26, GD, 10), rect(302, 290, 60, 26, GD, 10), rect(150, 452, 212, 20, GD, 8),
        path("M180 400 H332 L318 440 H194 Z", RD))),
    "Hero Cape": (450, "A flowing red cape with a golden clasp.", [
        path("M146 290 Q92 400 102 540 L152 512 L158 320 Z", R), path("M366 290 Q420 400 410 540 L360 512 L354 320 Z", RD),
        path("M146 284 Q256 330 366 284 L366 306 Q256 352 146 306 Z", R), circ(256, 322, 12, G), circ(256, 322, 5, GD)]),
    "Web Suit": (600, "Red and blue suit with a web pattern.", top(
        R, DEND, line("M256 296 V490 M170 340 Q256 384 342 340 M160 400 Q256 444 352 400 M158 456 Q256 486 354 456", INK, 3),
        ell(256, 372, 11, 15, INK), line("M236 360 L218 346 M276 360 L294 346 M238 380 L220 394 M274 380 L292 394", INK, 3))),
}

FUN_BOTTOMS = {
    "Hero Tights": (400, "Blue tights with red stripes.", pants(
        DEN, DEND, rect(176, 470, 6, 176, R), rect(330, 470, 6, 176, R), band=G)),
    "Track Pants": (260, "Red tracksuit pants with white stripes.", pants(
        R, RD, rect(176, 470, 6, 176, W), rect(330, 470, 6, 176, W), band=INK)),
    "Heart Boxers": (200, "Boxers with little red hearts.", [
        path("M174 452 L338 452 L336 548 L272 548 L256 504 L240 548 L176 548 Z", W), rect(174, 446, 164, 20, R, 10),
        small_heart(204, 500, 0.5, R), small_heart(300, 484, 0.5, R), small_heart(232, 526, 0.45, R), small_heart(312, 524, 0.45, R)]),
    "Plaid Kilt": (280, "A bold plaid kilt.", [
        path("M174 452 L338 452 L348 572 L164 572 Z", R), rect(174, 446, 164, 20, INK, 10),
        *[rect(x, 466, 8, 106, INK, extra=' opacity="0.55"') for x in (194, 226, 258, 290, 316)],
        *[rect(166, y, 182, 8, W, extra=' opacity="0.6"') for y in (490, 530)]]),
}

FUN_SHOES = {
    "Bunny Slippers": (240, "Pink slippers with floppy ears.", clog(PNK, PNKD, [
        ell(192, 656, 10, 22, PNK), ell(236, 656, 10, 22, PNK), ell(276, 656, 10, 22, PNK), ell(320, 656, 10, 22, PNK),
        ell(192, 658, 5, 14, PNKD), ell(236, 658, 5, 14, PNKD), ell(276, 658, 5, 14, PNKD), ell(320, 658, 5, 14, PNKD),
        circ(214, 690, 5, INK), circ(298, 690, 5, INK)])),
    "Donut Slides": (220, "Pink-iced donut slippers with sprinkles.", [
        ring(214, 692, 34, CRUST, 28), ring(214, 692, 34, PNK, 16), ring(298, 692, 34, CRUST, 28), ring(298, 692, 34, PNK, 16),
        rect(186, 672, 10, 4, W, 2), rect(220, 662, 10, 4, G, 2), rect(236, 690, 10, 4, W, 2), rect(190, 706, 10, 4, G, 2),
        rect(272, 672, 10, 4, W, 2), rect(306, 662, 10, 4, G, 2), rect(320, 690, 10, 4, W, 2), rect(276, 706, 10, 4, G, 2)]),
    "Socks and Sandals": (160, "The brave fashion choice.", [
        rect(184, 640, 60, 64, W, 20), rect(268, 640, 60, 64, W, 20), rect(184, 650, 60, 8, R), rect(268, 650, 60, 8, R),
        rect(170, 702, 88, 20, BRN, 10), rect(254, 702, 88, 20, BRN, 10), rect(184, 688, 60, 8, BRND, 4), rect(268, 688, 60, 8, BRND, 4)]),
    "Hero Boots": (420, "Red boots with white cuffs.", boot(R, RD, W)),
    "Rocket Boots": (600, "Jet-powered boots. Use with care.", boot(SL, SLD, ORG) + [
        path("M186 726 Q214 780 242 726 Z", ORG), path("M270 726 Q298 780 326 726 Z", ORG),
        path("M202 726 Q214 758 226 726 Z", G), path("M286 726 Q298 758 310 726 Z", G)]),
}

FUN_ACCESSORIES = {
    "Disguise Glasses": (160, "Fake nose, glasses and mustache. Nobody will know.", [
        ring(220, 158, 24, INK, 5), ring(292, 158, 24, INK, 5), line("M244 156 H268", INK, 5),
        ell(256, 196, 20, 15, "#E3A87C"), path("M256 214 C244 204 222 208 218 224 C234 218 246 222 256 214 C266 222 278 218 294 224 C290 208 268 204 256 214 Z", INK)]),
    "Unibrow": (100, "One magnificent eyebrow.", [
        path("M196 138 Q220 118 250 132 Q256 128 262 132 Q292 118 316 138 Q290 130 262 142 Q256 138 250 142 Q222 130 196 138 Z", INK)]),
    "Hero Mask": (300, "A classic eye mask for a secret identity.", [
        path("M188 144 Q220 128 256 144 Q292 128 324 144 Q330 178 298 182 Q276 184 266 170 L246 170 Q236 184 214 182 Q182 178 188 144 Z", DEND),
        ell(220, 158, 17, 12, W), ell(292, 158, 17, 12, W), circ(222, 158, 6, INK), circ(294, 158, 6, INK)]),
    "Web Mask": (550, "A full red mask with a web pattern.", [
        path("M184 104 Q256 66 328 104 L338 200 Q256 272 174 200 Z", R),
        line("M256 90 V254 M196 122 Q256 164 316 122 M184 164 Q256 204 328 164 M190 204 Q256 238 322 204", INK, 3),
        path("M200 150 Q224 132 246 156 Q226 178 204 170 Z", W), path("M312 150 Q288 132 266 156 Q286 178 308 170 Z", W)]),
    "Lightning Visor": (420, "A glowing visor with a bolt.", [
        rect(186, 138, 140, 44, SLD, 22), rect(196, 148, 120, 24, MINT, 12, ' opacity="0.85"'), rect(204, 152, 40, 6, W, 3, ' opacity="0.7"'),
        path("M268 136 L246 168 H262 L252 194 L284 156 H266 L276 136 Z", G)]),
}
