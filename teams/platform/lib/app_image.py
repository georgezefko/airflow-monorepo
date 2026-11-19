"""Image of a team's app: teams/<team>/apps/<path> -> <registry>/<team>/<path>:<content hash>.

The tag is a hash of the app folder's files, so the same code always means the same tag. CI tags
images with it, and DAGs compute it from their own checkout: a team's release tag pins its images.
Run it to list every app: python teams/platform/lib/app_image.py
"""
import hashlib
import os
import sys
from pathlib import Path

# Each environment's own registry (Helm env APPS_REGISTRY); dev's when unset: local, CI and tests.
REGISTRY = os.environ.get("APPS_REGISTRY", "us-central1-docker.pkg.dev/project-09344e23-c1cd-49df-a40/airflow-monorepo")


def app_hash(app_dir):
    h = hashlib.sha256()
    for f in sorted(app_dir.rglob("*")):
        rel = f.relative_to(app_dir)
        # Local-only files (.venv, caches) aren't in the image; keep in step with each .dockerignore
        if f.is_file() and not any(p.startswith(".") and p != ".dockerignore" or p == "__pycache__" for p in rel.parts):
            h.update(rel.as_posix().encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()[:12]


def image(app_dir):
    app_dir = Path(app_dir).resolve()
    team, _apps, *path = app_dir.parts[app_dir.parts.index("teams") + 1 :]
    return f"{REGISTRY}/{team}/{'/'.join(path)}:{app_hash(app_dir)}"


def all_apps(repo):
    return sorted(d.parent for d in Path(repo).glob("teams/*/apps/**/Dockerfile"))


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[3]
    for d in all_apps(repo):
        print(d.relative_to(repo), image(d))
