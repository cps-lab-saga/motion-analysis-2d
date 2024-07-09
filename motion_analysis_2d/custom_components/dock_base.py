from motion_analysis_2d.custom_components.gui_save_base import BaseGuiSave
from qtpy import QtCore, QtWidgets


class BaseDock(QtWidgets.QDockWidget, BaseGuiSave):
    layout_direction_changed = QtCore.Signal(object)

    def __init__(self):
        super().__init__()

        self.setObjectName(self.__class__.__name__)
        self.save_heading = self.__class__.__name__

        self.dock_contents = QtWidgets.QFrame(parent=self)
        self.dock_contents.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.setWidget(self.dock_contents)
        self.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self.setFeatures(
            self.DockWidgetFeature.DockWidgetFloatable
            | self.DockWidgetFeature.DockWidgetMovable
            | self.DockWidgetFeature.DockWidgetClosable
        )

        self.dock_layout = QtWidgets.QBoxLayout(
            QtWidgets.QBoxLayout.Direction.TopToBottom, self.dock_contents
        )

        self.dockLocationChanged.connect(self.change_layout_based_on_dock_area)

    def change_layout_based_on_dock_area(self, area):
        if area in [QtCore.Qt.TopDockWidgetArea, QtCore.Qt.BottomDockWidgetArea]:
            self.dock_layout.setDirection(QtWidgets.QBoxLayout.Direction.LeftToRight)
            self.layout_direction_changed.emit(
                QtWidgets.QBoxLayout.Direction.LeftToRight
            )
        else:
            self.dock_layout.setDirection(QtWidgets.QBoxLayout.Direction.TopToBottom)
            self.layout_direction_changed.emit(
                QtWidgets.QBoxLayout.Direction.TopToBottom
            )


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = BaseDock()
    widget.show()

    app.exec()
