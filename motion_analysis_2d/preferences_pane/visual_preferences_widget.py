from motion_analysis_2d.custom_components import ColorButton
from motion_analysis_2d.defs import QtCore, QtWidgets, Signal, visual_preferences_file
from motion_analysis_2d.preferences_pane.default_preferences import visual_preferences
from motion_analysis_2d.preferences_pane.load_preferences import (
    load_preferences,
    save_preferences,
)


class VisualPreferencesWidget(QtWidgets.QWidget):
    closed = Signal()
    load_error = Signal(str)
    update_preferences = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("Visual Preferences")

        self.preferences_file = visual_preferences_file()
        if self.preferences_file.is_file():
            try:
                self.visual_preferences = load_preferences(self.preferences_file)

                # ignore file if outdated
                if visual_preferences.keys() != self.visual_preferences.keys():
                    self.shortcuts = visual_preferences.copy()
            except Exception as e:
                self.load_error.emit(f"{self.preferences_file} is corrupted!\n{str(e)}")
                self.visual_preferences = visual_preferences.copy()
        else:
            self.visual_preferences = visual_preferences.copy()

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_contents = QtWidgets.QWidget(self)
        self.scroll_area.setWidget(self.scroll_contents)
        self.scroll_area_layout = QtWidgets.QVBoxLayout(self.scroll_contents)
        self.main_layout.addWidget(self.scroll_area)

        self.form_layout = QtWidgets.QFormLayout()
        self.scroll_area_layout.addLayout(self.form_layout)

        self.visual_widgets = {}
        for key, value in self.visual_preferences.items():
            self.generate_row(key, value)

        self.default_button = QtWidgets.QPushButton("Restore Defaults")
        self.default_button.clicked.connect(self.restore_defaults)
        self.scroll_area_layout.addWidget(self.default_button)

        contents_size = (
            self.sizeHint() + self.scroll_area.verticalScrollBar().sizeHint()
        )
        self.scroll_area.setMinimumWidth(contents_size.width())

    def generate_row(self, key, value):
        preference_type = key.split("_")[-1]
        if preference_type == "color":
            widget = ColorButton(self)
            widget.set_rbg(value)
            widget.color_changed.connect(self.change_preferences)

        elif preference_type in ["width", "length", "size", "height"]:
            widget = QtWidgets.QSpinBox(self)
            widget.setRange(0, 100)
            widget.setValue(value)
            widget.valueChanged.connect(self.change_preferences)

        elif preference_type == "radius":
            widget = QtWidgets.QSpinBox(self)
            widget.setRange(0, 400)
            widget.setValue(value)
            widget.valueChanged.connect(self.change_preferences)

        elif preference_type == "transparency":
            widget = QtWidgets.QSpinBox(self)
            widget.setRange(0, 255)
            widget.setValue(value)
            widget.valueChanged.connect(self.change_preferences)

        else:
            widget = QtWidgets.QTextEdit(self)
            widget.setText(str(value))

        widget.setObjectName(key)
        self.form_layout.addRow(key.replace("_", " ").title(), widget)
        self.visual_widgets[key] = widget
        return widget

    def change_preferences(self):
        widget = self.sender()
        key = widget.objectName()
        if isinstance(widget, ColorButton):
            self.visual_preferences[key] = widget.get_rgb()
        elif isinstance(widget, QtWidgets.QSpinBox):
            self.visual_preferences[key] = widget.value()
        else:
            self.visual_preferences[key] = widget.text()
        self.save_preferences()

    def restore_defaults(self):
        self.visual_preferences = visual_preferences.copy()
        for key, value in visual_preferences.items():
            preference_type = key.split("_")[-1]
            widget = self.visual_widgets[key]
            widget.blockSignals(True)
            if preference_type == "color":
                widget.set_rbg(value)
            elif preference_type in [
                "width",
                "length",
                "size",
                "height",
                "radius",
                "transparency",
            ]:
                widget.setValue(value)
            else:
                widget.setText(str(value))
            widget.blockSignals(False)
        self.save_preferences()

    def save_preferences(self):
        self.preferences_file.parent.mkdir(exist_ok=True, parents=True)
        save_preferences(self.preferences_file, self.visual_preferences)
        self.update_preferences.emit(self.visual_preferences)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    pref_widget = VisualPreferencesWidget()
    pref_widget.show()

    app.exec()
