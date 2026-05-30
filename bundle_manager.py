import json
import uuid
import copy


def gen_uuid():
    return str(uuid.uuid4())


def merge_packs(mods_list):
    if not mods_list:
        return {}

    bp_uuid_header = gen_uuid()
    bp_uuid_module = gen_uuid()
    rp_uuid_header = gen_uuid()
    rp_uuid_module = gen_uuid()

    merged = {}
    bp_items = {}
    bp_entities = {}
    bp_recipes = {}
    bp_loot = {}
    rp_entities = {}
    rp_rc = {}
    rp_textures = {}
    item_textures = {}

    for mod_files in mods_list:
        for path, content in mod_files.items():
            if "manifest.json" in path:
                continue
            if path.startswith("BP/items/"):
                bp_items[path] = content
            elif path.startswith("BP/entities/"):
                bp_entities[path] = content
            elif path.startswith("BP/recipes/"):
                bp_recipes[path] = content
            elif path.startswith("BP/loot_tables/"):
                bp_loot[path] = content
            elif path.startswith("RP/entity/"):
                rp_entities[path] = content
            elif path.startswith("RP/render_controllers/"):
                rp_rc[path] = content
            elif isinstance(content, bytes):
                rp_textures[path] = content
            elif path == "RP/textures/item_texture.json":
                if content and "texture_data" in content:
                    item_textures.update(content["texture_data"])
            else:
                merged[path] = content

    merged["BP/manifest.json"] = {
        "format_version": 2,
        "header": {
            "name": "Merged Pack BP",
            "description": "Merged Bedrock Add-on Pack",
            "uuid": bp_uuid_header,
            "version": [1, 0, 0],
            "min_engine_version": [1, 20, 0]
        },
        "modules": [{"type": "data", "uuid": bp_uuid_module, "version": [1, 0, 0]}],
        "dependencies": [{"uuid": rp_uuid_header, "version": [1, 0, 0]}]
    }

    merged["RP/manifest.json"] = {
        "format_version": 2,
        "header": {
            "name": "Merged Pack RP",
            "description": "Merged Bedrock Add-on Pack",
            "uuid": rp_uuid_header,
            "version": [1, 0, 0],
            "min_engine_version": [1, 20, 0]
        },
        "modules": [{"type": "resources", "uuid": rp_uuid_module, "version": [1, 0, 0]}],
        "dependencies": [{"uuid": bp_uuid_header, "version": [1, 0, 0]}]
    }

    merged.update(bp_items)
    merged.update(bp_entities)
    merged.update(bp_recipes)
    merged.update(bp_loot)
    merged.update(rp_entities)
    merged.update(rp_rc)
    merged.update(rp_textures)

    if item_textures:
        merged["RP/textures/item_texture.json"] = {
            "resource_pack_name": "merged_pack",
            "texture_name": "atlas.items",
            "texture_data": item_textures
        }

    return merged


def get_bundle_summary(mods_data):
    lines = ["📦 ملخص الحزمة:\n━━━━━━━━━━━━━━━"]
    for i, mod in enumerate(mods_data, 1):
        mod_type = mod.get("mod_type", "item")
        name = mod.get("display_name", "مود")
        emoji = {"item": "⚔️", "food": "🍖", "armor": "🛡️", "entity": "🐉"}.get(mod_type, "📦")
        lines.append(f"{i}. {emoji} {name}")
    lines.append("━━━━━━━━━━━━━━━")
    return "\n".join(lines)
