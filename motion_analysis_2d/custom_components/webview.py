from motion_analysis_2d.defs import QtWebEngineWidgets, Signal


class WebView(QtWebEngineWidgets.QWebEngineView):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def closeEvent(self, event):
        self.closed.emit()
