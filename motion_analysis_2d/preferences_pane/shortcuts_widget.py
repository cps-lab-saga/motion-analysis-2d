from motion_analysis_2d.defs import QtCore, QtWidgets, Signal, shortcuts_file
from motion_analysis_2d.preferences_pane.default_preferences import shortcut_keys
from motion_analysis_2d.preferences_pane.load_preferences import (
    load_preferences,
    save_preferences,
)


class ShortcutsWidget(QtWidgets.QWidget):
    closed = Signal()
    load_error = Signal(str)
    update_shortcuts = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("Shortcuts")

        self.shortcuts_file = shortcuts_file()
        if self.shortcuts_file.is_file():
            try:
                self.shortcuts = load_preferences(self.shortcuts_file)
            except Exception as e:
                self.load_error.emit(f"{self.shortcuts_file} is corrupted!\n{str(e)}")
                self.shortcuts = shortcut_keys
        else:
            self.shortcuts = shortcut_keys

        self.form_layout = QtWidgets.QFormLayout(self)

        self.keys_button = {}
        for command, key in self.shortcuts.items():
            self.generate_row(key, command)

    def generate_row(self, key, command):
        key_button = QtWidgets.QPushButton(self)
        key_button.setAutoExclusive(True)
        key_button.setCheckable(True)
        key_button.setText(key.split("_")[-1])
        key_button.setObjectName(command)

        self.form_layout.addRow(command.replace("_", " ").title(), key_button)
        self.keys_button[command] = key_button
        return key_button

    def keyPressEvent(self, event):
        for key_button in self.keys_button.values():
            if key_button.isChecked():
                key = QtCore.Qt.Key(event.key()).name
                command = key_button.objectName()

                key_button.setText(key.split("_")[-1])
                self.shortcuts[command] = key
                key_button.setAutoExclusive(False)
                key_button.setChecked(False)
                key_button.setAutoExclusive(True)

                self.save_shortcut()
                break

    def save_shortcut(self):
        self.shortcuts_file.parent.mkdir(exist_ok=True, parents=True)
        save_preferences(self.shortcuts_file, self.shortcuts)
        self.update_shortcuts.emit(self.shortcuts)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.processEvents()
    widget = ShortcutsWidget()
    widget.show()

    app.exec()
