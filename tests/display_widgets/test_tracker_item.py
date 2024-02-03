import numpy as np

from motion_analysis_2d.display_widgets import FrameWidget


def test_add_tracker(qtbot):
    widget = FrameWidget()

    black_img = np.zeros([100, 100, 3], dtype=np.uint8)
    widget.update_frame(black_img, 0, 0)

    assert (widget.im_item.image == black_img).all()
