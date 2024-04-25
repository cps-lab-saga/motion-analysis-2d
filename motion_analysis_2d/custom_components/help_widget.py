from motion_analysis_2d.defs import QtCore, QtWidgets, QtWebEngineWidgets, Signal


class HelpView(QtWidgets.QMainWindow):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.webview = QtWebEngineWidgets.QWebEngineView(self)
        self.setCentralWidget(self.webview)
        self.resize(800, 600)

        self.setWindowTitle("Help")
        self.webview.setUrl(
            QtCore.QUrl("https://cps-lab-saga.github.io/motion-analysis-2d/")
        )

    def closeEvent(self, event):
        self.closed.emit()
