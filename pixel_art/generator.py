"""
generator.py — مولّد صور البيكسل آرت
ينتج PNG حقيقي 16×16 لكل آيتم وكيان
"""

import io
from PIL import Image, ImageFilter, ImageDraw
from .shapes import get_shape, ENTITY_SKIN_HEAD, ENTITY_SKIN_BODY
from .colors import (
    get_item_colors, get_entity_colors,
    EFFECT_COLORS, ARMOR_MATERIAL_COLORS,
    BASE_COLORS, darken, lighten
)

SIZE = 16  # حجم الصورة الأساسي
ENTITY_W = 64
ENTITY_H = 32


# ════════════════════════════════════════════════════════
#  دوال مساعدة
# ════════════════════════════════════════════════════════

def pixels_to_image(pixels, base, shadow, highlight, glow=None, scale=1):
    """يحول بيانات البيكسل إلى صورة PIL"""
    img = Image.new("RGBA", (SIZE * scale, SIZE * scale), (0, 0, 0, 0))

    color_map = {
        1: base + (255,),
        2: shadow + (255,),
        3: highlight + (255,),
        4: glow + (200,) if glow else base + (180,),
        0: (0, 0, 0, 0),
    }

    for y, row in enumerate(pixels):
        for x, val in enumerate(row):
            color = color_map.get(val, (0, 0, 0, 0))
            if scale == 1:
                img.putpixel((x, y), color)
            else:
                for dy in range(scale):
                    for dx in range(scale):
                        img.putpixel((x * scale + dx, y * scale + dy), color)

    return img


def add_glow_effect(img, glow_color, intensity=0.4):
    """يضيف تأثير توهج حول الآيتم"""
    if not glow_color:
        return img

    glow_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)

    # ارسم نقاط التوهج حول البيكسلات غير الشفافة
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            if pixels[x, y][3] > 0:
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < img.width and 0 <= ny < img.height:
                            if pixels[nx, ny][3] == 0:
                                alpha = int(80 * intensity)
                                glow_draw.point((nx, ny),
                                    fill=glow_color + (alpha,))

    return Image.alpha_composite(glow_img, img)


def add_shimmer(img, highlight_color):
    """يضيف لمعان خفيف"""
    shimmer = img.copy()
    draw = ImageDraw.Draw(shimmer)
    # نقاط لمعان عشوائية ثابتة
    shimmer_points = [(2,2), (4,1), (1,5), (6,3), (3,7)]
    for x, y in shimmer_points:
        if x < img.width and y < img.height:
            draw.point((x, y), fill=highlight_color + (200,))
    return Image.alpha_composite(img, shimmer)


def image_to_bytes(img):
    """يحول الصورة إلى bytes لحفظها في الـ ZIP"""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ════════════════════════════════════════════════════════
#  مولّد صور الآيتمز
# ════════════════════════════════════════════════════════

def generate_item_texture(item_type, color="gray", effects=None):
    """
    يولّد صورة PNG 16×16 للآيتم
    item_type: sword, axe, bow, food, potion, generic...
    color: اللون الأساسي
    effects: قائمة التأثيرات
    """
    if effects is None:
        effects = []

    # احصل على الألوان
    base, shadow, highlight, glow = get_item_colors(color, effects)

    # احصل على الشكل
    shape = get_shape(item_type)

    # ولّد الصورة
    img = pixels_to_image(shape, base, shadow, highlight, glow)

    # أضف تأثير التوهج إذا وجد
    if glow and effects:
        img = add_glow_effect(img, glow, intensity=0.6)

    # أضف لمعان
    img = add_shimmer(img, highlight)

    return image_to_bytes(img)


# ════════════════════════════════════════════════════════
#  مولّد صور الدرع
# ════════════════════════════════════════════════════════

def generate_armor_texture(piece_type, color="gray", protection="medium"):
    """
    يولّد صورة PNG 16×16 لقطعة الدرع
    piece_type: helmet, chestplate, leggings, boots
    """
    base, shadow, highlight, glow = get_item_colors(color)

    # لون خاص حسب مستوى الحماية
    if protection == "high":
        base = tuple(min(255, c + 20) for c in base)
    elif protection == "low":
        base = tuple(max(0, c - 20) for c in base)

    shape = get_shape(piece_type)
    img = pixels_to_image(shape, base, shadow, highlight)
    img = add_shimmer(img, highlight)

    return image_to_bytes(img)


# ════════════════════════════════════════════════════════
#  مولّد texture الكيان (64×32)
# ════════════════════════════════════════════════════════

def generate_entity_texture(color1="red", color2="black"):
    """
    يولّد texture الكيان 64×32
    هذا الجلد الكامل للكيان في ماين كرافت
    """
    img = Image.new("RGBA", (ENTITY_W, ENTITY_H), (0, 0, 0, 0))

    base1, shadow1, highlight1 = get_entity_colors(color1)
    base2, shadow2, highlight2 = get_entity_colors(color2)

    def draw_section(start_x, start_y, width, height, base, shadow, highlight, pattern=None):
        """يرسم قسم من الـ texture"""
        for y in range(height):
            for x in range(width):
                # نمط بسيط: حواف داكنة، وسط فاتح
                if x == 0 or y == 0 or x == width-1 or y == height-1:
                    color = shadow + (255,)
                elif x == 1 or y == 1:
                    color = highlight + (255,)
                else:
                    # تناوب خفيف للإضافة تفاصيل
                    if (x + y) % 4 == 0:
                        color = highlight + (255,)
                    elif (x + y) % 4 == 2:
                        color = shadow + (220,)
                    else:
                        color = base + (255,)
                img.putpixel((start_x + x, start_y + y), color)

    # ── رسم أجزاء الكيان ───────────────────────────────
    # الرأس (8×8 في الموضع 0,0)
    draw_section(0, 0, 8, 8, base1, shadow1, highlight1)
    # غطاء الرأس (8×8 في الموضع 32,0)
    draw_section(32, 0, 8, 8, base2, shadow2, highlight2)

    # الجسم (8×12 في الموضع 16,16)
    draw_section(16, 16, 8, 12, base1, shadow1, highlight1)

    # الذراع الأيمن (4×12 في الموضع 40,16)
    draw_section(40, 16, 4, 12, base2, shadow2, highlight2)

    # الذراع الأيسر (4×12 في الموضع 32,48) — للـ 1.8+
    # نكتفي بالـ texture الأساسي هنا

    # الساق اليمنى (4×12 في الموضع 0,16)
    draw_section(0, 16, 4, 12, base1, shadow1, highlight1)

    # الساق اليسرى (4×12 في الموضع 16,48)
    # نكتفي بنسخ الساق اليمنى بلون مختلف قليلاً
    draw_section(16, 16, 4, 12, base2, shadow2, highlight2)

    # أضف تفاصيل على الوجه (عيون)
    eye_color = (20, 20, 20, 255)
    # عين يمنى
    for ex, ey in [(1,2),(2,2),(1,3),(2,3)]:
        img.putpixel((ex, ey), eye_color)
    # عين يسرى
    for ex, ey in [(5,2),(6,2),(5,3),(6,3)]:
        img.putpixel((ex, ey), eye_color)

    # فم
    mouth_color = (60, 20, 20, 255)
    for ex in range(2, 6):
        img.putpixel((ex, 6), mouth_color)

    return image_to_bytes(img)


# ════════════════════════════════════════════════════════
#  مولّد صورة Spawn Egg
# ════════════════════════════════════════════════════════

def generate_spawn_egg(color1="red", color2="black"):
    """يولّد أيقونة بيضة الإنشاء 16×16"""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    base1 = BASE_COLORS.get(color1, (200, 50, 50))
    base2 = BASE_COLORS.get(color2, (40, 40, 40))
    shadow1 = darken(base1)
    highlight1 = lighten(base1)

    # شكل بيضة دائري
    egg_shape = [
        [0,0,0,0,0,2,2,2,2,2,0,0,0,0,0,0],
        [0,0,0,0,2,1,1,1,1,1,2,0,0,0,0,0],
        [0,0,0,2,1,1,3,1,1,1,1,2,0,0,0,0],
        [0,0,2,1,1,3,1,1,1,1,1,1,2,0,0,0],
        [0,2,1,1,3,1,1,1,1,1,1,1,1,2,0,0],
        [2,1,1,1,1,1,1,1,1,1,1,1,1,1,2,0],
        [2,1,1,1,1,1,1,1,1,1,1,1,1,1,2,0],
        [2,1,1,1,1,1,1,1,1,1,1,1,1,1,2,0],
        [2,1,1,1,1,1,1,1,1,1,1,1,1,1,2,0],
        [0,2,1,1,1,1,1,1,1,1,1,1,1,2,0,0],
        [0,0,2,1,1,1,1,1,1,1,1,1,2,0,0,0],
        [0,0,0,2,1,1,1,1,1,1,1,2,0,0,0,0],
        [0,0,0,0,2,1,1,1,1,1,2,0,0,0,0,0],
        [0,0,0,0,0,2,2,2,2,2,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    ]

    color_map = {
        0: (0, 0, 0, 0),
        1: base1 + (255,),
        2: shadow1 + (255,),
        3: highlight1 + (255,),
    }

    # النصف السفلي بلون ثانٍ
    for y, row in enumerate(egg_shape):
        for x, val in enumerate(row):
            if val == 0:
                continue
            if y >= 7:  # النصف السفلي
                c = base2 + (255,) if val == 1 else darken(base2) + (255,)
            else:
                c = color_map.get(val, (0, 0, 0, 0))
            img.putpixel((x, y), c)

    return image_to_bytes(img)


# ════════════════════════════════════════════════════════
#  الدالة الرئيسية
# ════════════════════════════════════════════════════════

def generate_all_textures(mod_data):
    """
    يولّد كل الصور المطلوبة للمود
    يرجع قاموس path -> bytes
    """
    textures = {}
    mod_type = mod_data.get("mod_type", "item")
    color = mod_data.get("color1", "gray")
    effects = mod_data.get("effects", [])

    if mod_type == "item":
        item_id = mod_data.get("item_id", "custom_item")
        item_type = mod_data.get("item_type", "sword")
        textures[f"RP/textures/items/{item_id}.png"] = generate_item_texture(
            item_type, color, effects
        )

    elif mod_type == "food":
        item_id = mod_data.get("item_id", "custom_food")
        food_subtype = mod_data.get("food_subtype", "food")
        textures[f"RP/textures/items/{item_id}.png"] = generate_item_texture(
            food_subtype, color, effects
        )

    elif mod_type == "armor":
        armor_name = mod_data.get("armor_name", "custom_armor")
        protection = mod_data.get("protection", "medium")
        pieces = mod_data.get("pieces", ["helmet","chestplate","leggings","boots"])
        for piece in pieces:
            textures[f"RP/textures/items/{armor_name}_{piece}.png"] = generate_armor_texture(
                piece, color, protection
            )

    elif mod_type == "entity":
        entity_id = mod_data.get("entity_id", "custom_entity")
        color2 = mod_data.get("color2", "black")

        # Texture الكيان الكامل
        textures[f"RP/textures/entity/{entity_id}.png"] = generate_entity_texture(
            color, color2
        )

        # Spawn Egg
        textures[f"RP/textures/items/spawn_egg_{entity_id}.png"] = generate_spawn_egg(
            color, color2
        )

    return textures


def scale_texture_for_preview(img_bytes, scale=8):
    """يكبّر الصورة x8 للعرض الواضح في تيليغرام"""
    img = Image.open(io.BytesIO(img_bytes))
    scaled = img.resize(
        (img.width * scale, img.height * scale),
        Image.NEAREST
    )
    buf = io.BytesIO()
    scaled.save(buf, format="PNG")
    return buf.getvalue()


def get_preview_texture(mod_data):
    """يرجع صورة المعاينة الرئيسية للمود"""
    mod_type = mod_data.get("mod_type", "item")
    color = mod_data.get("color1", "gray")
    effects = mod_data.get("effects", [])

    if mod_type == "item":
        item_type = mod_data.get("item_type", "sword")
        raw = generate_item_texture(item_type, color, effects)
        return scale_texture_for_preview(raw, scale=8)

    elif mod_type == "food":
        raw = generate_item_texture("food", color, effects)
        return scale_texture_for_preview(raw, scale=8)

    elif mod_type == "armor":
        raw = generate_armor_texture("helmet", color, mod_data.get("protection","medium"))
        return scale_texture_for_preview(raw, scale=8)

    elif mod_type == "entity":
        color2 = mod_data.get("color2", "black")
        raw = generate_entity_texture(color, color2)
        return scale_texture_for_preview(raw, scale=4)

    return None
