BASE_COLORS = {
    "red":     (220, 50,  50),
    "blue":    (50,  100, 220),
    "green":   (50,  180, 80),
    "black":   (40,  40,  40),
    "white":   (240, 240, 240),
    "purple":  (150, 60,  200),
    "orange":  (230, 130, 40),
    "yellow":  (230, 210, 50),
    "pink":    (230, 130, 180),
    "gray":    (140, 140, 140),
    "cyan":    (50,  200, 210),
    "brown":   (130, 80,  40),
    "gold":    (255, 200, 0),
    "silver":  (190, 190, 200),
    "darkred": (150, 20,  20),
    "lime":    (100, 230, 50),
}

def darken(color, factor=0.6):
    return tuple(max(0, int(c * factor)) for c in color)

def lighten(color, factor=1.4):
    return tuple(min(255, int(c * factor)) for c in color)

EFFECT_COLORS = {
    "fire":    {"glow": (255, 120, 0),   "tint": (255, 80, 0)},
    "poison":  {"glow": (80,  200, 80),  "tint": (60, 180, 60)},
    "freeze":  {"glow": (100, 180, 255), "tint": (120, 200, 255)},
    "wither":  {"glow": (80,  0,   120), "tint": (100, 20, 140)},
    "heal":    {"glow": (100, 255, 150), "tint": (80, 230, 130)},
    "speed":   {"glow": (255, 255, 100), "tint": (220, 220, 80)},
    "strength":{"glow": (200, 50,  50),  "tint": (180, 40, 40)},
    "none":    {"glow": None,            "tint": None},
}

ARMOR_MATERIAL_COLORS = {
    "iron":     (180, 180, 190),
    "gold":     (255, 200, 0),
    "diamond":  (80,  220, 220),
    "netherite":(60,  50,  70),
    "leather":  (160, 100, 60),
    "custom":   (150, 60,  200),
}

ENTITY_SKIN_COLORS = {
    "red":    [(220,50,50),   (160,30,30),  (240,80,80)],
    "blue":   [(50,100,220),  (30,70,160),  (80,130,240)],
    "green":  [(50,180,80),   (30,130,50),  (80,210,100)],
    "black":  [(40,40,40),    (20,20,20),   (70,70,70)],
    "white":  [(240,240,240), (200,200,200),(255,255,255)],
    "purple": [(150,60,200),  (100,30,150), (180,90,230)],
    "orange": [(230,130,40),  (180,90,20),  (255,160,60)],
    "yellow": [(230,210,50),  (180,160,20), (255,235,80)],
    "gray":   [(140,140,140), (100,100,100),(170,170,170)],
    "brown":  [(130,80,40),   (90,50,20),   (160,110,60)],
}

def get_entity_colors(color_name):
    colors = ENTITY_SKIN_COLORS.get(color_name, ENTITY_SKIN_COLORS["gray"])
    return colors[0], colors[1], colors[2]

def get_item_colors(color_name, effects=None):
    base = BASE_COLORS.get(color_name, BASE_COLORS["gray"])
    shadow = darken(base)
    highlight = lighten(base)
    glow = None
    if effects:
        for eff in effects:
            if eff in EFFECT_COLORS and EFFECT_COLORS[eff]["glow"]:
                glow = EFFECT_COLORS[eff]["glow"]
                break
    return base, shadow, highlight, glow
