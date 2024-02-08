import qtawesome as qta

from motion_analysis_2d.defs import QtWidgets, QtGui


class FileToolBar(QtWidgets.QToolBar):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("File")

        self.add_video_action = QtGui.QAction("Add Video", self)
        self.add_video_action.setIcon(qta.icon("mdi.plus"))
        self.addAction(self.add_video_action)

        self.settings_action = QtGui.QAction("Settings", self)
        self.settings_action.setIcon(qta.icon("ri.settings-5-fill"))
        self.addAction(self.settings_action)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = FileToolBar()
    widget.show()

    app.exec()
