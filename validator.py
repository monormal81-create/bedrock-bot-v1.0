import json
import re
import uuid

VALID_FORMAT_VERSIONS_ITEM = ["1.20.0", "1.19.0", "1.18.0"]
VALID_FORMAT_VERSIONS_ENTITY = ["1.19.0", "1.18.0", "1.17.0"]
VALID_FORMAT_VERSIONS_MANIFEST = [2, "2"]

UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)

class ValidationError:
    def __init__(self, file, issue, severity="ERROR"):
        self.file = file
        self.issue = issue
        self.severity = severity
    def __str__(self):
        icon = "❌" if self.severity == "ERROR" else "⚠️"
        return f"{icon} [{self.file}] {self.issue}"

class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed = []
    @property
    def is_valid(self):
        return len(self.errors) == 0
    def add_error(self, file, issue):
        self.errors.append(ValidationError(file, issue, "ERROR"))
    def add_warning(self, file, issue):
        self.warnings.append(ValidationError(file, issue, "WARNING"))
    def add_pass(self, check):
        self.passed.append(f"✅ {check}")
    def summary(self):
        lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━",
                 "📋 تقرير الفحص النهائي",
                 "━━━━━━━━━━━━━━━━━━━━━━━━━"]
        if self.is_valid:
            lines.append("✅ الملف اجتاز الفحص بنجاح!")
        else:
            lines.append(f"❌ يوجد {len(self.errors)} خطأ")
        if self.errors:
            lines.append("\n🔴 الأخطاء:")
            for e in self.errors:
                lines.append(f"  {e}")
        if self.warnings:
            lines.append("\n🟡 تحذيرات:")
            for w in self.warnings:
                lines.append(f"  {w}")
        if self.passed:
            lines.append("\n🟢 اجتاز:")
            for p in self.passed:
                lines.append(f"  {p}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

def validate_uuid(value):
    return bool(UUID_PATTERN.match(str(value)))

def validate_manifest(path, data, result):
    fv = data.get("format_version")
    if fv not in VALID_FORMAT_VERSIONS_MANIFEST:
        result.add_error(path, f"format_version غير صحيح: {fv}")
    else:
        result.add_pass(f"format_version صحيح في {path}")
    header = data.get("header", {})
    if not header:
        result.add_error(path, "header مفقود")
        return
    h_uuid = header.get("uuid", "")
    if not validate_uuid(h_uuid):
        result.add_error(path, f"UUID في header غير صالح: {h_uuid}")
    else:
        result.add_pass(f"UUID header صحيح في {path}")
    if not header.get("name", "").strip():
        result.add_error(path, "name فارغ في header")
    ver = header.get("version", [])
    if not isinstance(ver, list) or len(ver) != 3:
        result.add_error(path, "version يجب أن يكون [x, y, z]")
    modules = data.get("modules", [])
    if not modules:
        result.add_error(path, "modules فارغ")
    else:
        for mod in modules:
            mod_uuid = mod.get("uuid", "")
            if not validate_uuid(mod_uuid):
                result.add_error(path, f"UUID في module غير صالح: {mod_uuid}")
            else:
                result.add_pass(f"UUID module صحيح في {path}")

def validate_item(path, data, result):
    fv = data.get("format_version", "")
    if fv not in VALID_FORMAT_VERSIONS_ITEM:
        result.add_warning(path, f"format_version {fv} قد لا يكون مدعوماً")
    item = data.get("minecraft:item", {})
    if not item:
        result.add_error(path, "minecraft:item مفقود")
        return
    desc = item.get("description", {})
    identifier = desc.get("identifier", "")
    if not identifier:
        result.add_error(path, "identifier مفقود")
    elif ":" not in identifier:
        result.add_error(path, f"identifier يجب أن يحتوي namespace")
    else:
        result.add_pass(f"identifier صحيح: {identifier}")
    components = item.get("components", {})
    if not components:
        result.add_error(path, "components فارغ")
    else:
        if "minecraft:icon" not in components:
            result.add_warning(path, "minecraft:icon مفقود")
        if "minecraft:display_name" not in components:
            result.add_warning(path, "minecraft:display_name مفقود")
        else:
            result.add_pass(f"components أساسية موجودة في {path}")

def validate_entity(path, data, result):
    entity = data.get("minecraft:entity", {})
    if not entity:
        result.add_error(path, "minecraft:entity مفقود")
        return
    desc = entity.get("description", {})
    identifier = desc.get("identifier", "")
    if not identifier:
        result.add_error(path, "identifier مفقود")
    elif ":" not in identifier:
        result.add_error(path, "identifier يجب أن يحتوي namespace")
    else:
        result.add_pass(f"identifier صحيح: {identifier}")
    components = entity.get("components", {})
    if not components:
        result.add_error(path, "components فارغ")
    else:
        if "minecraft:health" not in components:
            result.add_error(path, "minecraft:health مفقود")
        else:
            result.add_pass("minecraft:health موجود")
        if "minecraft:physics" not in components:
            result.add_warning(path, "minecraft:physics مفقود")

def validate_recipe(path, data, result):
    has_shaped = "minecraft:recipe_shaped" in data
    has_shapeless = "minecraft:recipe_shapeless" in data
    has_furnace = "minecraft:recipe_furnace" in data
    if not any([has_shaped, has_shapeless, has_furnace]):
        result.add_error(path, "نوع الوصفة غير معروف")
        return
    if has_shaped:
        recipe = data["minecraft:recipe_shaped"]
        if "pattern" not in recipe:
            result.add_error(path, "pattern مفقود")
        if "key" not in recipe:
            result.add_error(path, "key مفقود")
        if "result" not in recipe:
            result.add_error(path, "result مفقود")
        else:
            result.add_pass(f"وصفة shaped صحيحة")
    if has_furnace:
        recipe = data["minecraft:recipe_furnace"]
        if "input" not in recipe:
            result.add_error(path, "input مفقود")
        if "output" not in recipe:
            result.add_error(path, "output مفقود")
        else:
            result.add_pass("وصفة furnace صحيحة")

def validate_pack(files):
    result = ValidationResult()
    file_paths = [p for p in files.keys() if files[p] is not None]
    has_bp = any(p == "BP/manifest.json" for p in file_paths)
    has_rp = any(p == "RP/manifest.json" for p in file_paths)
    if not has_bp:
        result.add_error("Pack", "BP/manifest.json مفقود")
    else:
        result.add_pass("BP/manifest.json موجود")
    if not has_rp:
        result.add_warning("Pack", "RP/manifest.json مفقود")
    else:
        result.add_pass("RP/manifest.json موجود")
    for path, content in files.items():
        if content is None:
            result.add_warning(path, "Texture غير مضمنة — أضفها يدوياً")
            continue
        if not isinstance(content, dict):
            result.add_error(path, "المحتوى ليس JSON صحيح")
            continue
        if "manifest.json" in path:
            validate_manifest(path, content, result)
        elif "BP/items/" in path:
            validate_item(path, content, result)
        elif "BP/entities/" in path:
            validate_entity(path, content, result)
        elif "BP/recipes/" in path or "loot_tables" in path:
            validate_recipe(path, content, result)
        elif "RP/entity/" in path:
            if "minecraft:client_entity" not in content:
                result.add_error(path, "minecraft:client_entity مفقود")
            else:
                result.add_pass(f"client entity صحيح في {path}")
    total = len([p for p, v in files.items() if v is not None])
    result.add_pass(f"إجمالي الملفات المفحوصة: {total}")
    return result