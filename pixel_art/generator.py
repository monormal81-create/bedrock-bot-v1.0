import io
from PIL import Image, ImageDraw
from .shapes import get_shape
from .colors import get_item_colors, get_entity_colors, BASE_COLORS, darken, lighten

SIZE = 16
ENTITY_W = 64
ENTITY_H = 32

def pixels_to_image(pixels, base, shadow, highlight, glow=None):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    color_map = {
        1: base + (255,),
        2: shadow + (255,),
        3: highlight + (255,),
        4: glow + (200,) if glow else base + (180,),
        0: (0, 0, 0, 0),
    }
    for y, row in enumerate(pixels):
        for x, val in enumerate(row):
            img.putpixel((x, y), color_map.get(val, (0, 0, 0, 0)))
    return img

def add_glow_effect(img, glow_color):
    if not glow_color:
        return img
    glow_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_img)
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            if pixels[x, y][3] > 0:
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < img.width and 0 <= ny < img.height:
                            if pixels[nx, ny][3] == 0:
                                draw.point((nx, ny), fill=glow_color + (60,))
    return Image.alpha_composite(glow_img, img)

def image_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def generate_item_texture(item_type, color="gray", effects=None):
    if effects is None:
        effects = []
    base, shadow, highlight, glow = get_item_colors(color, effects)
    shape = get_shape(item_type)
    img = pixels_to_image(shape, base, shadow, highlight, glow)
    if glow:
        img = add_glow_effect(img, glow)
    return image_to_bytes(img)

def generate_armor_texture(piece_type, color="gray", protection="medium"):
    base, shadow, highlight, _ = get_item_colors(color)
    if protection == "high":
        base = tuple(min(255, c + 20) for c in base)
    elif protection == "low":
        base = tuple(max(0, c - 20) for c in base)
    shape = get_shape(piece_type)
    img = pixels_to_image(shape, base, shadow, highlight)
    return image_to_bytes(img)

def generate_entity_texture(color1="red", color2="black"):
    img = Image.new("RGBA", (ENTITY_W, ENTITY_H), (0, 0, 0, 0))
    base1, shadow1, highlight1 = get_entity_colors(color1)
    base2, shadow2, highlight2 = get_entity_colors(color2)

    def draw_section(sx, sy, w, h, base, shadow, highlight):
        for y in range(h):
            for x in range(w):
                if x == 0 or y == 0 or x == w-1 or y == h-1:
                    c = shadow + (255,)
                elif x == 1 or y == 1:
                    c = highlight + (255,)
                elif (x + y) % 4 == 0:
                    c = highlight + (255,)
                elif (x + y) % 4 == 2:
                    c = shadow + (220,)
                else:
                    c = base + (255,)
                img.putpixel((sx + x, sy + y), c)

    draw_section(0, 0, 8, 8, base1, shadow1, highlight1)
    draw_section(32, 0, 8, 8, base2, shadow2, highlight2)
    draw_section(16, 16, 8, 12, base1, shadow1, highlight1)
    draw_section(40, 16, 4, 12, base2, shadow2, highlight2)
    draw_section(0, 16, 4, 12, base1, shadow1, highlight1)

    eye = (20, 20, 20, 255)
    for ex, ey in [(1,2),(2,2),(1,3),(2,3)]:
        img.putpixel((ex, ey), eye)
    for ex, ey in [(5,2),(6,2),(5,3),(6,3)]:
        img.putpixel((ex, ey), eye)
    for ex in range(2, 6):
        img.putpixel((ex, 6), (60, 20, 20, 255))

    return image_to_bytes(img)

def generate_spawn_egg(color1="red", color2="black"):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    base1 = BASE_COLORS.get(color1, (200, 50, 50))
    base2 = BASE_COLORS.get(color2, (40, 40, 40))
    shadow1 = darken(base1)
    highlight1 = lighten(base1)
    egg = [
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
    cmap = {0:(0,0,0,0),1:base1+(255,),2:shadow1+(255,),3:highlight1+(255,)}
    for y, row in enumerate(egg):
        for x, v in enumerate(row):
            if v == 0:
                continue
            if y >= 7:
                c = base2+(255,) if v==1 else darken(base2)+(255,)
            else:
                c = cmap.get(v,(0,0,0,0))
            img.putpixel((x,y),c)
    return image_to_bytes(img)

def generate_all_textures(mod_data):
    textures = {}
    mod_type = mod_data.get("mod_type","item")
    color = mod_data.get("color1","gray")
    effects = mod_data.get("effects",[])

    if mod_type == "item":
        item_id = mod_data.get("item_id","custom_item")
        item_type = mod_data.get("item_type","sword")
        textures[f"RP/textures/items/{item_id}.png"] = generate_item_texture(item_type, color, effects)

    elif mod_type == "food":
        item_id = mod_data.get("item_id","custom_food")
        textures[f"RP/textures/items/{item_id}.png"] = generate_item_texture("food", color, effects)

    elif mod_type == "armor":
        armor_name = mod_data.get("armor_name","custom_armor")
        protection = mod_data.get("protection","medium")
        pieces = mod_data.get("pieces",["helmet","chestplate","leggings","boots"])
        for piece in pieces:
            textures[f"RP/textures/items/{armor_name}_{piece}.png"] = generate_armor_texture(piece, color, protection)

    elif mod_type == "entity":
        entity_id = mod_data.get("entity_id","custom_entity")
        color2 = mod_data.get("color2","black")
        textures[f"RP/textures/entity/{entity_id}.png"] = generate_entity_texture(color, color2)
        textures[f"RP/textures/items/spawn_egg_{entity_id}.png"] = generate_spawn_egg(color, color2)

    return textures
