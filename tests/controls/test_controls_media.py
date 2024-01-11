from motion_analysis_2d.controls import MediaControls


def test_controls_edit(qtbot):
    widget = MediaControls()
    qtbot.addWidget(widget)

    check_seek_bar_value(widget)

    def play(output):
        if output:
            assert widget.play_button.isChecked()
        else:
            assert not widget.play_button.isChecked()

    def previous_frame():
        assert widget.sender() is widget.previous_button

    def next_frame():
        assert widget.sender() is widget.next_button

    def seek_bar_moved(val):
        assert val == widget.seek_bar.value()

    def track_enabled(output):
        if output:
            assert widget.track_button.isChecked()
        else:
            assert not widget.track_button.isChecked()

    widget.play.connect(play)
    widget.previous_frame.connect(previous_frame)
    widget.next_frame.connect(next_frame)
    widget.seek_bar_moved.connect(seek_bar_moved)
    widget.track_enabled.connect(track_enabled)

    for _ in range(3):
        widget.play_button.click()
        widget.track_button.click()

    widget.previous_button.click()
    widget.next_button.click()
    widget.set_seek_bar_value(1)


def check_seek_bar_value(widget):
    widget.set_seeking_props(100)

    widget.set_seek_bar_value(50)
    assert widget.seek_bar.value() == 50

    widget.set_seek_bar_value(-1)
    assert widget.seek_bar.value() == 0

    widget.set_seek_bar_value(120)
    assert widget.seek_bar.value() == 100

    widget.set_seek_bar_value(10.5)
    assert widget.seek_bar.value() == 10
