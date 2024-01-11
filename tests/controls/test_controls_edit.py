from motion_analysis_2d.controls import EditControls
from motion_analysis_2d.display_widgets import MouseModes


def test_controls_edit(qtbot):
    widget = EditControls()

    def mode_change_output(output):
        assert output.upper() in MouseModes.__members__, "Invalid mode!"

        # check that at most one is checked
        num_checked = 0
        for b in widget.buttons:
            if b.isChecked():
                num_checked += 1
        assert num_checked <= 1, "More than one control has been checked!"

    qtbot.addWidget(widget)
    widget.mode_changed.connect(mode_change_output)

    # click once
    for button in widget.buttons:
        button.click()

    # click twice
    for button in widget.buttons:
        button.click()
        button.click()
