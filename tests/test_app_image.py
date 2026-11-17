import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "teams" / "platform" / "lib"))
from app_image import REGISTRY, all_apps, image  # noqa: E402


def make_app(root):
    app = root / "teams" / "sales" / "apps" / "forecast"
    app.mkdir(parents=True)
    (app / "Dockerfile").write_text("FROM scratch\n")
    (app / "main.py").write_text("print(1)\n")
    return app


def test_image_name_and_tag_follow_the_folder(tmp_path):
    app = make_app(tmp_path)
    name, tag = image(app).rsplit(":", 1)
    assert name == f"{REGISTRY}/sales/forecast" and len(tag) == 12
    assert all_apps(tmp_path) == [app]


def test_tag_changes_with_the_code_not_with_local_files(tmp_path):
    app = make_app(tmp_path)
    before = image(app)
    (app / ".venv").mkdir()
    (app / ".venv" / "x").write_text("local")
    (app / "__pycache__").mkdir()
    (app / "__pycache__" / "main.pyc").write_text("cache")
    assert image(app) == before
    (app / "main.py").write_text("print(2)\n")
    assert image(app) != before
