from pathlib import Path

from airflow.configuration import conf


def version_tag(team_dir):
    """The DAG's version chip: v<version.txt> in prod, the config's version_tag where it's set.

    Dev runs main, which is ahead of the last release, so dev sets config.platform.version_tag to
    "main" (Helm values) instead of showing a version it isn't running.
    """
    return conf.get("platform", "version_tag", fallback=None) or "v" + (Path(team_dir) / "version.txt").read_text().strip()
