import copy
import templates as T

def load_template(name):
    mapping = {
        "manifests/bp_manifest.json": T.BP_MANIFEST,
        "manifests/rp_manifest.json": T.RP_MANIFEST,
        "items/sword.json": T.SWORD,
        "items/axe.json": T.AXE,
        "items/bow.json": T.BOW,
        "items/food.json": T.FOOD,
        "items/potion.json": T.POTION,
        "items/item_texture.json": T.ITEM_TEXTURE,
        "armor/armor_piece.json": T.ARMOR_PIECE,
        "entities/hostile.json": T.HOSTILE,
        "entities/passive.json": T.PASSIVE,
        "entities/companion.json": T.COMPANION,
        "entities/entity_client.json": T.ENTITY_CLIENT,
        "entities/render_controller.json": T.RENDER_CONTROLLER,
        "recipes/shaped.json": T.RECIPE_SHAPED,
        "recipes/shapeless.json": T.RECIPE_SHAPELESS,
        "recipes/furnace.json": T.RECIPE_FURNACE,
        "recipes/loot_table.json": T.LOOT_TABLE,
    }
    return copy.deepcopy(mapping[name])

def fill(template, values):
    text = json.dumps(template, ensure_ascii=False)
    for key, val in values.items():
        if isinstance(val, (dict, list)):
            placeholder = f'"{{{{{key}}}}}"'
            replacement = json.dumps(val, ensure_ascii=False)
            text = text.replace(placeholder, replacement)
        else:
            text = text.replace(f"{{{{{key}}}}}", str(val))
    return json.loads(text)

def generate_uuids():
    return {
        "BP_UUID_HEADER": gen_uuid(),
        "BP_UUID_MODULE": gen_uuid(),
        "RP_UUID_HEADER": gen_uuid(),
        "RP_UUID_MODULE": gen_uuid(),
    }

SATURATION_MAP = {
    "low": "low", "normal": "normal",
    "good": "good", "max": "supernatural"
}

ARMOR_SLOTS = {
    "helmet": {"slot": "head", "protection": 3},
    "chestplate": {"slot": "chest", "protection": 8},
    "leggings": {"slot": "legs", "protection": 6},
    "boots": {"slot": "feet", "protection": 3},
}

EGG_COLORS = {
    "red": "#FF0000", "blue": "#0000FF", "green": "#00FF00",
    "black": "#000000", "white": "#FFFFFF", "purple": "#800080",
    "orange": "#FFA500", "yellow": "#FFFF00", "pink": "#FFC0CB", "gray": "#808080",
}

def build_item(data):
    uuids = generate_uuids()
    ns = data.get("namespace", "mymod")
    item_id = data["item_id"]
    display = data["display_name"]
    item_type = data.get("item_type", "sword")
    pack_name = data.get("pack_name", display)
    pack_desc = data.get("pack_desc", f"Adds {display}")

    values = {
        **uuids,
        "NAMESPACE": ns,
        "ITEM_ID": item_id,
        "DISPLAY_NAME": display,
        "PACK_NAME": pack_name,
        "PACK_DESCRIPTION": pack_desc,
    }

    files = {}

    bp_tmpl = load_template("manifests/bp_manifest.json")
    files["BP/manifest.json"] = fill(bp_tmpl, values)

    rp_tmpl = load_template("manifests/rp_manifest.json")
    files["RP/manifest.json"] = fill(rp_tmpl, values)

    if item_type == "sword":
        tmpl = load_template("items/sword.json")
        values.update({
            "DAMAGE": data.get("damage", 10),
            "DURABILITY": data.get("durability", 500),
            "MINING_SPEED": data.get("mining_speed", 1.5),
            "REPAIR_ITEM": data.get("repair_item", "minecraft:diamond"),
            "EVENTS": _build_item_events(data.get("effects", []), ns),
        })
    elif item_type == "axe":
        tmpl = load_template("items/axe.json")
        values.update({
            "DAMAGE": data.get("damage", 8),
            "DURABILITY": data.get("durability", 400),
            "MINING_SPEED": data.get("mining_speed", 4.0),
        })
    elif item_type == "bow":
        tmpl = load_template("items/bow.json")
        values.update({
            "DURABILITY": data.get("durability", 384),
            "DRAW_DURATION": data.get("draw_duration", 1.0),
        })
    elif item_type in ("food", "potion"):
        tmpl = load_template(f"items/{item_type}.json")
        food_effects = _build_food_effects(data.get("effects", []))
        values.update({
            "STACK_SIZE": data.get("stack_size", 16),
            "NUTRITION": data.get("nutrition", 4),
            "SATURATION": SATURATION_MAP.get(data.get("saturation", "normal"), "normal"),
            "CAN_ALWAYS_EAT": str(data.get("can_always_eat", False)).lower(),
            "FOOD_EFFECTS": food_effects,
            "POTION_EFFECTS": food_effects,
        })
    else:
        tmpl = load_template("items/sword.json")
        values.update({
            "DAMAGE": data.get("damage", 5),
            "DURABILITY": data.get("durability", 300),
            "MINING_SPEED": 1.0,
            "REPAIR_ITEM": "minecraft:iron_ingot",
            "EVENTS": {},
        })

    files[f"BP/items/{item_id}.json"] = fill(tmpl, values)

    item_tex_tmpl = load_template("items/item_texture.json")
    files["RP/textures/item_texture.json"] = fill(item_tex_tmpl, values)
    files[f"RP/textures/items/{item_id}.png"] = None

    return files

def _build_item_events(effects, ns):
    if not effects:
        return {}
    events = {}
    for eff in effects:
        if eff == "fire":
            events[f"{ns}:on_hit"] = {
                "sequence": [{"damage": {"type": "fire", "target": "other", "amount": 3}}]
            }
        elif eff == "poison":
            events[f"{ns}:on_hit"] = {
                "sequence": [{"add_mob_effect": {"effect": "poison", "target": "other", "duration": 100, "amplifier": 1}}]
            }
        elif eff == "freeze":
            events[f"{ns}:on_hit"] = {
                "sequence": [{"add_mob_effect": {"effect": "slowness", "target": "other", "duration": 100, "amplifier": 3}}]
            }
        elif eff == "wither":
            events[f"{ns}:on_hit"] = {
                "sequence": [{"add_mob_effect": {"effect": "wither", "target": "other", "duration": 80, "amplifier": 1}}]
            }
        elif eff == "heal":
            events[f"{ns}:on_hit"] = {
                "sequence": [{"add_mob_effect": {"effect": "instant_health", "target": "self", "duration": 1, "amplifier": 1}}]
            }
    return events

def _build_food_effects(effects):
    result = []
    effect_map = {
        "speed": "speed", "strength": "strength", "regeneration": "regeneration",
        "fire_resistance": "fire_resistance", "night_vision": "night_vision",
        "invisibility": "invisibility", "poison": "poison", "weakness": "weakness",
        "slowness": "slowness", "heal": "instant_health", "absorption": "absorption"
    }
    for eff in effects:
        if eff in effect_map:
            result.append({
                "name": effect_map[eff],
                "duration": 600,
                "amplifier": 0,
                "chance": 1.0
            })
    return result

def build_armor(data):
    uuids = generate_uuids()
    ns = data.get("namespace", "mymod")
    armor_name = data["armor_name"]
    pack_name = data.get("pack_name", armor_name)
    pack_desc = data.get("pack_desc", f"Adds {armor_name} armor")
    protection = data.get("protection", "medium")
    prot_map = {"low": [2,5,4,2], "medium": [3,8,6,3], "high": [4,10,8,4]}
    prot_values = prot_map.get(protection, prot_map["medium"])
    durability = data.get("durability", 500)

    values = {
        **uuids,
        "NAMESPACE": ns,
        "PACK_NAME": pack_name,
        "PACK_DESCRIPTION": pack_desc,
    }

    files = {}
    files["BP/manifest.json"] = fill(load_template("manifests/bp_manifest.json"), values)
    files["RP/manifest.json"] = fill(load_template("manifests/rp_manifest.json"), values)

    piece_names = ["helmet", "chestplate", "leggings", "boots"]
    for i, piece in enumerate(piece_names):
        item_id = f"{armor_name}_{piece}"
        display = f"{data.get('display_prefix', armor_name)} {piece.capitalize()}"
        tmpl = load_template("armor/armor_piece.json")
        slot_info = ARMOR_SLOTS[piece]
        v = {**values,
             "ITEM_ID": item_id,
             "DISPLAY_NAME": display,
             "DURABILITY": durability,
             "PROTECTION": prot_values[i],
             "SLOT": slot_info["slot"]}
        files[f"BP/items/{item_id}.json"] = fill(tmpl, v)

    return files

def build_entity(data):
    uuids = generate_uuids()
    ns = data.get("namespace", "mymod")
    entity_id = data["entity_id"]
    display = data["display_name"]
    entity_type = data.get("entity_type", "passive")
    pack_name = data.get("pack_name", display)
    pack_desc = data.get("pack_desc", f"Adds {display} entity")
    color1 = EGG_COLORS.get(data.get("color1", "red"), "#FF0000")
    color2 = EGG_COLORS.get(data.get("color2", "black"), "#000000")

    values = {
        **uuids,
        "NAMESPACE": ns,
        "ENTITY_ID": entity_id,
        "DISPLAY_NAME": display,
        "PACK_NAME": pack_name,
        "PACK_DESCRIPTION": pack_desc,
        "HEALTH": data.get("health", 20),
        "DAMAGE": data.get("damage", 3),
        "SPEED": data.get("speed", 0.3),
        "WIDTH": data.get("width", 0.6),
        "HEIGHT": data.get("height", 1.8),
        "ATTACK_RADIUS": data.get("attack_radius", 16),
        "EGG_COLOR_1": color1,
        "EGG_COLOR_2": color2,
        "TAME_CHANCE": data.get("tame_chance", 0.3),
        "TAME_ITEM": data.get("tame_item", "minecraft:bone"),
    }

    files = {}
    files["BP/manifest.json"] = fill(load_template("manifests/bp_manifest.json"), values)
    files["RP/manifest.json"] = fill(load_template("manifests/rp_manifest.json"), values)

    if entity_type == "hostile":
        tmpl = load_template("entities/hostile.json")
    elif entity_type == "companion":
        tmpl = load_template("entities/companion.json")
    else:
        tmpl = load_template("entities/passive.json")

    files[f"BP/entities/{entity_id}.json"] = fill(tmpl, values)

    loot_entries = _build_loot(data.get("drops", []))
    loot_tmpl = load_template("recipes/loot_table.json")
    loot_vals = {**values, "MIN_ROLLS": 1, "MAX_ROLLS": 3, "LOOT_ENTRIES": loot_entries}
    files[f"BP/loot_tables/entities/{entity_id}.json"] = fill(loot_tmpl, loot_vals)

    files[f"RP/entity/{entity_id}.entity.json"] = fill(load_template("entities/entity_client.json"), values)
    files[f"RP/render_controllers/{entity_id}.json"] = fill(load_template("entities/render_controller.json"), values)

    return files

def _build_loot(drops):
    if not drops:
        return [{"type": "item", "name": "minecraft:bone", "weight": 1,
                 "functions": [{"function": "set_count", "count": {"min": 0, "max": 2}}]}]
    entries = []
    for drop in drops:
        entries.append({
            "type": "item",
            "name": drop.get("item", "minecraft:bone"),
            "weight": drop.get("weight", 1),
            "functions": [{"function": "set_count", "count": {"min": drop.get("min", 0), "max": drop.get("max", 2)}}]
        })
    return entries

def build_recipe(data, item_files=None):
    ns = data.get("namespace", "mymod")
    item_id = data["item_id"]
    recipe_type = data.get("recipe_type", "shaped")
    files = {}

    if recipe_type == "shaped":
        tmpl = load_template("recipes/shaped.json")
        pattern, key = _build_shaped_pattern(data.get("ingredients", []))
        values = {
            "NAMESPACE": ns, "ITEM_ID": item_id,
            "PATTERN": pattern, "KEY": key,
            "RESULT_COUNT": data.get("result_count", 1),
        }
        files[f"BP/recipes/recipe_{item_id}.json"] = fill(tmpl, values)

    elif recipe_type == "shapeless":
        tmpl = load_template("recipes/shapeless.json")
        ingredients = [{"item": ing} for ing in data.get("ingredients", [])]
        values = {
            "NAMESPACE": ns, "ITEM_ID": item_id,
            "INGREDIENTS": ingredients,
            "RESULT_COUNT": data.get("result_count", 1),
        }
        files[f"BP/recipes/recipe_{item_id}.json"] = fill(tmpl, values)

    elif recipe_type == "furnace":
        tmpl = load_template("recipes/furnace.json")
        values = {
            "NAMESPACE": ns, "ITEM_ID": item_id,
            "INPUT_ITEM": data.get("input_item", "minecraft:iron_ore"),
            "RESULT_COUNT": 1,
        }
        files[f"BP/recipes/furnace_{item_id}.json"] = fill(tmpl, values)

    return files

def _build_shaped_pattern(ingredients):
    symbols = ["A","B","C","D","E","F","G","H","I"]
    unique = list(dict.fromkeys(ingredients))
    key = {}
    for i, ing in enumerate(unique[:9]):
        key[symbols[i]] = {"item": ing}
    sym_map = {ing: symbols[i] for i, ing in enumerate(unique[:9])}
    padded = [sym_map.get(ing, " ") for ing in ingredients[:9]]
    while len(padded) < 9:
        padded.append(" ")
    pattern = [
        "".join(padded[0:3]),
        "".join(padded[3:6]),
        "".join(padded[6:9]),
    ]
    pattern = [row for row in pattern if row.strip()]
    return pattern, key