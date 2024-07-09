from pathlib import Path

from platformdirs import user_config_path, user_log_path

project_name = "motion-analysis-2d"
app_version = "0.1.8"

module_name = project_name.replace("-", "_")


def config_dir() -> Path:
    return user_config_path(project_name, ensure_exists=True)


def project_root() -> Path:
    Path(__file__).parent.parent.mkdir(exist_ok=True, parents=True)
    return Path(__file__).parent.parent


def ui_file() -> Path:
    return config_dir() / f"{module_name}_restore.ini"


def shortcuts_file():
    return config_dir() / f"{module_name}_shortcuts.json"


def visual_preferences_file():
    return config_dir() / f"{module_name}_visual.json"


def log_file() -> Path:
    return user_log_path(project_name, ensure_exists=True) / f"{project_name}.log"


def resource_dir() -> Path:
    return project_root() / module_name / "resource"


def readme_file() -> Path:
    return project_root() / "README.md"
