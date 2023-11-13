import qtawesome as qta

from defs import QtCore, QtWidgets, Signal
from motion_analysis_2d.custom_components import BaseDock


class TrackingDock(BaseDock):
    track_enabled = Signal(bool)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Tracking")

        grid_layout = QtWidgets.QGridLayout()
        self.dock_layout.addLayout(grid_layout)

        icon_size = 18
        # self.skip_button = QtWidgets.QPushButton(self)
        # self.skip_button.setIcon(qta.icon("mdi.debug-step-over"))
        # self.skip_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        # self.skip_button.setCheckable(True)
        # self.skip_button.setFlat(True)
        # self.skip_button.setText("Skip Tracked")
        # self.skip_button.setToolTip("Skip ahead to untracked data.")
        # grid_layout.addWidget(self.skip_button, 0, 0)

        self.track_button = QtWidgets.QPushButton(self)
        self.track_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.tracking_icon = qta.icon(
            "fa.spinner", animation=qta.Spin(self.track_button, interval=10, step=10)
        )
        self.tracking_not_icon = qta.icon("fa.spinner")
        self.track_button.setIcon(self.tracking_not_icon)
        self.track_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.track_button.setCheckable(True)
        self.track_button.setFlat(True)
        self.track_button.setText("Tracking Active")
        self.track_button.setToolTip("Activate marker trackers.")
        self.track_button.toggled.connect(self.track_button_toggled)
        grid_layout.addWidget(self.track_button, 0, 0, 1, 2)

        row_layout = QtWidgets.QHBoxLayout()
        self.dock_layout.addLayout(row_layout)

        self.continue_button = QtWidgets.QPushButton(self)
        self.continue_icon = qta.icon("mdi.playlist-play")
        self.continue_button.setIcon(self.continue_icon)
        self.continue_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.continue_button.setCheckable(True)
        self.continue_button.setFlat(True)
        self.continue_button.setText("Continue")
        self.continue_button.setToolTip(
            "Automatically continue to next video in queue."
        )
        grid_layout.addWidget(self.continue_button, 1, 0)

        self.reset_trackers_button = QtWidgets.QPushButton(self)
        self.reset_trackers_icon = qta.icon("mdi.reload")
        self.reset_trackers_button.setIcon(self.reset_trackers_icon)
        self.reset_trackers_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.reset_trackers_button.setFlat(True)
        self.reset_trackers_button.setText("Reset")
        self.reset_trackers_button.setToolTip("Reset trackers.")
        grid_layout.addWidget(self.reset_trackers_button, 1, 1)

        self.dock_layout.addStretch()

    def track_button_toggled(self):
        self.track_enabled.emit(self.track_button.isChecked())

    def set_tracking(self, tracking):
        if tracking:
            self.track_button.setIcon(self.tracking_icon)
        else:
            self.track_button.setIcon(self.tracking_not_iconn)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = TrackingDock()
    widget.show()

    app.exec()
