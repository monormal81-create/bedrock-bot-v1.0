import os
import shutil
import uuid
import zipfile


PROJECTS_DIR = "projects"


def gen_uuid():

    return str(uuid.uuid4())


def safe_name(name):

    return (
        name.lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def create_project_structure(project_name):

    project_id = gen_uuid()

    folder = safe_name(project_name)

    root = os.path.join(
        PROJECTS_DIR,
        folder
    )

    structure = [

        "BP",
        "BP/items",
        "BP/entities",
        "BP/recipes",
        "BP/loot_tables",
        "BP/functions",

        "RP",
        "RP/textures",
        "RP/textures/items",
        "RP/textures/entity",
        "RP/models",
        "RP/animations",
        "RP/sounds",

        "build",
        "temp",
        "exports",
    ]

    for path in structure:

        os.makedirs(
            os.path.join(root, path),
            exist_ok=True
        )

    return {
        "project_id": project_id,
        "project_name": project_name,
        "project_path": root,
    }


def project_exists(project_name):

    folder = safe_name(project_name)

    root = os.path.join(
        PROJECTS_DIR,
        folder
    )

    return os.path.isdir(root)


def delete_project(project_name):

    folder = safe_name(project_name)

    root = os.path.join(
        PROJECTS_DIR,
        folder
    )

    if os.path.isdir(root):

        shutil.rmtree(root)

        return True

    return False


def export_project(project_name):

    folder = safe_name(project_name)

    root = os.path.join(
        PROJECTS_DIR,
        folder
    )

    export_path = os.path.join(
        root,
        "exports",
        f"{folder}.mcaddon"
    )

    with zipfile.ZipFile(
        export_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zipf:

        for dirpath, dirs, files in os.walk(root):

            for file in files:

                full = os.path.join(
                    dirpath,
                    file
                )

                relative = os.path.relpath(
                    full,
                    root
                )

                if "exports" in relative:
                    continue

                zipf.write(
                    full,
                    relative
                )

    return export_path


def list_projects():

    if not os.path.isdir(PROJECTS_DIR):

        return []

    return os.listdir(PROJECTS_DIR)


def project_info(project_name):

    folder = safe_name(project_name)

    root = os.path.join(
        PROJECTS_DIR,
        folder
    )

    if not os.path.isdir(root):

        return None

    total_files = 0

    total_size = 0

    for dirpath, dirs, files in os.walk(root):

        total_files += len(files)

        for file in files:

            path = os.path.join(
                dirpath,
                file
            )

            total_size += os.path.getsize(path)

    return {
        "name": project_name,
        "path": root,
        "files": total_files,
        "size": total_size,
  }
