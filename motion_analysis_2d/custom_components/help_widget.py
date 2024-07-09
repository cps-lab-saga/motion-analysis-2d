import qtawesome as qta
from qtpy import QtCore, QtWidgets, QtWebEngineWidgets


class HelpView(QtWidgets.QMainWindow):
    closed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.webview = QtWebEngineWidgets.QWebEngineView(self)
        self.setCentralWidget(self.webview)
        self.resize(600, 400)

        self.setWindowTitle("Help")
        self.setWindowIcon(qta.icon("mdi6.help"))
        self.webview.setUrl(
            QtCore.QUrl("https://cps-lab-saga.github.io/motion-analysis-2d/")
        )

    def closeEvent(self, event):
        self.closed.emit()
