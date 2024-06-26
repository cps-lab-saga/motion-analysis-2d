from motion_analysis_2d.custom_components.gui_save_base import BaseGuiSave
from motion_analysis_2d.defs import QtCore, QtWidgets, Signal


class BaseDock(QtWidgets.QDockWidget, BaseGuiSave):
    layout_direction_changed = Signal(object)

    def __init__(self):
        super().__init__()

        self.setObjectName(self.__class__.__name__)
        self.save_heading = self.__class__.__name__

        self.setStyleSheet(style_sheet)

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
            QtWidgets.QBoxLayout.TopToBottom, self.dock_contents
        )

        self.dockLocationChanged.connect(self.change_layout_based_on_dock_area)

    def change_layout_based_on_dock_area(self, area):
        if area in [QtCore.Qt.TopDockWidgetArea, QtCore.Qt.BottomDockWidgetArea]:
            self.dock_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)
            self.layout_direction_changed.emit(QtWidgets.QBoxLayout.LeftToRight)
        else:
            self.dock_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
            self.layout_direction_changed.emit(QtWidgets.QBoxLayout.TopToBottom)


style_sheet = """
QDockWidget::title {
    text-align: left; /* align the text to the left */
    background: lightgray;
    padding-left: 5px;
}
"""

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = BaseDock()
    widget.show()

    app.exec()
