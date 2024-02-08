from motion_analysis_2d.defs import project_root
from motion_analysis_2d.display_widgets.frame_widget import FrameWidget
from motion_analysis_2d.funcs.load_settings import load_application_settings
from motion_analysis_2d.main_widget import MainWidget


def test_load_application_settings():
    settings_folder = project_root() / "tests" / "funcs" / "application_settings"
    for f in settings_folder.glob("*.json"):
        data = load_application_settings(f)
        check_format(data)
        check_shortcut_commands(data)
        check_visual_settings(data)


def check_format(data):
    assert isinstance(data, dict)
    assert isinstance(data["shortcut_keys"], dict)
    assert isinstance(data["visual_settings"], dict)


def check_shortcut_commands(data):
    for cmd in data["shortcut_keys"].values():
        assert callable(getattr(MainWidget, cmd))


def check_visual_settings(data):
    fw = FrameWidget()
    for s in data["visual_settings"].keys():
        assert s in fw.visual_settings
