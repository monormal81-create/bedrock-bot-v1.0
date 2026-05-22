"""
pack_builder.py
يحوّل JSON الملفات من الـ AI إلى ملف .mcpack حقيقي
"""

import os
import re
import json
import uuid
import zipfile
import tempfile


def generate_uuid() -> str:
    return str(uuid.uuid4())


def parse_ai_response(ai_text: str) -> dict[str, str]:
    """
    يحلّل رد الـ AI ويستخرج منه كل ملف وموقعه.
    يبحث عن أنماط مثل:
        📁 BP/entities/my_mob.json
        ```json
        { ... }
        ```
    """
    files = {}

    # نمط: سطر مسار + كتلة كود
    pattern = re.compile(
        r'(?:📁\s*|Path:\s*|`{0,1})([\w/.\-]+\.(?:json|js))`?\s*\n'
        r'```(?:json|javascript|js)?\n([\s\S]*?)```',
        re.IGNORECASE
    )

    for match in pattern.finditer(ai_text):
        file_path = match.group(1).strip().lstrip("/")
        file_content = match.group(2).strip()
        files[file_path] = file_content

    # إذا ما لقى ملفات بالنمط الأول، جرّب نمط أبسط
    if not files:
        pattern2 = re.compile(
            r'```(?:json|javascript|js)\n([\s\S]*?)```',
            re.IGNORECASE
        )
        blocks = pattern2.findall(ai_text)
        # استخرج المسارات من الأسطر قبل كل كتلة
        lines = ai_text.split('\n')
        block_idx = 0
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if re.match(r'```(?:json|javascript|js)?$', line_clean, re.IGNORECASE):
                # ابحث عن مسار في السطور السابقة
                for back in range(1, 5):
                    prev = lines[i - back].strip() if i >= back else ""
                    path_match = re.search(r'[\w/.\-]+\.(?:json|js)', prev)
                    if path_match:
                        if block_idx < len(blocks):
                            clean_path = path_match.group(0).lstrip("/")
                            files[clean_path] = blocks[block_idx]
                            block_idx += 1
                        break
                else:
                    # ملف بدون مسار واضح، سمّه باسم تسلسلي
                    if block_idx < len(blocks):
                        files[f"BP/unknown_{block_idx}.json"] = blocks[block_idx]
                        block_idx += 1

    return files


def fix_uuids_in_manifest(content: str) -> str:
    """يستبدل أي UUID placeholder بـ UUID حقيقي"""
    # استبدل أي UUID ناقص أو placeholder
    placeholders = [
        "YOUR-UUID-HERE", "UUID-HERE", "HEADER-UUID", "DEP-UUID",
        "00000000-0000-0000-0000-000000000000",
        "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    ]
    for ph in placeholders:
        content = content.replace(ph, generate_uuid())
    return content


def ensure_manifest_uuids(content: str) -> str:
    """تأكد أن كل UUIDs في الـ manifest صحيحة وفريدة"""
    try:
        data = json.loads(content)
        if "header" in data:
            if not data["header"].get("uuid") or "0000" in data["header"].get("uuid", ""):
                data["header"]["uuid"] = generate_uuid()
        if "modules" in data:
            for mod in data["modules"]:
                if not mod.get("uuid") or "0000" in mod.get("uuid", ""):
                    mod["uuid"] = generate_uuid()
        if "dependencies" in data:
            for dep in data["dependencies"]:
                if not dep.get("uuid") or "0000" in dep.get("uuid", ""):
                    dep["uuid"] = generate_uuid()
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        return content


def build_mcpack(files: dict[str, str], pack_name: str) -> str:
    """
    يبني ملف .mcpack حقيقي (ZIP) ويرجع مساره المؤقت
    """
    # مجلد مؤقت
    tmp_dir = tempfile.mkdtemp()
    out_path = os.path.join(tmp_dir, f"{pack_name}.mcpack")

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, content in files.items():
            # إصلاح UUIDs في الـ manifests
            if "manifest.json" in file_path:
                content = fix_uuids_in_manifest(content)
                content = ensure_manifest_uuids(content)

            # تأكد أن JSON صالح
            if file_path.endswith(".json"):
                try:
                    parsed = json.loads(content)
                    content = json.dumps(parsed, indent=2, ensure_ascii=False)
                except json.JSONDecodeError as e:
                    # حاول إصلاح المشكلة الشائعة: فاصلة زائدة
                    content = re.sub(r',\s*([}\]])', r'\1', content)
                    try:
                        parsed = json.loads(content)
                        content = json.dumps(parsed, indent=2, ensure_ascii=False)
                    except Exception:
                        pass  # استخدم المحتوى كما هو

            zf.writestr(file_path, content.encode("utf-8"))

    return out_path


def extract_pack_name(ai_text: str) -> str:
    """يستخرج اسم المود من رد الـ AI"""
    # ابحث عن اسم في السطور الأولى
    for line in ai_text[:500].split('\n'):
        m = re.search(r'"name"\s*:\s*"([^"]+)"', line)
        if m:
            name = m.group(1).strip()
            # تنظيف الاسم ليصلح كاسم ملف
            name = re.sub(r'[^\w\s\-]', '', name).strip().replace(' ', '_')
            return name[:40] or "bedrock_addon"
    return "bedrock_addon"


def process_ai_response(ai_text: str) -> tuple[str, dict[str, str]]:
    """
    الدالة الرئيسية:
    - تحلّل رد الـ AI
    - تبني ملف .mcpack
    - ترجع (مسار الملف, قاموس الملفات)
    """
    files = parse_ai_response(ai_text)

    if not files:
        raise ValueError("لم يتم العثور على أي ملفات JSON في رد الـ AI")

    pack_name = extract_pack_name(ai_text)
    mcpack_path = build_mcpack(files, pack_name)

    return mcpack_path, files
