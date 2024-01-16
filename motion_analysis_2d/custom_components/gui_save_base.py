import inspect
from distutils.util import strtobool

from defs import QtWidgets
from motion_analysis_2d.custom_components.path_edit import PathEdit


class BaseGuiSave:
    """Default save gui behaviour

    Save ui state using variable names.
    """

    def __init__(self):
        self.save_heading = "Gui"

        self.gui_save_exceptions = []

    def gui_save(self, settings):
        for name, obj in inspect.getmembers(self):
            if obj in self.gui_save_exceptions:
                continue
            value = None
            if isinstance(obj, QtWidgets.QLineEdit):
                value = obj.text()
            elif isinstance(obj, QtWidgets.QSpinBox):
                value = obj.value()
            elif isinstance(obj, QtWidgets.QDoubleSpinBox):
                value = obj.value()
            elif isinstance(obj, (QtWidgets.QRadioButton, QtWidgets.QCheckBox)):
                value = obj.isChecked()
            elif isinstance(obj, QtWidgets.QPushButton) and obj.isCheckable():
                value = obj.isChecked()
            elif isinstance(obj, QtWidgets.QComboBox):
                value = obj.currentText()
            if value is not None:
                settings.setValue(f"{self.save_heading}/{name}", value)

    def gui_restore(self, settings):
        for name, obj in inspect.getmembers(self):
            if obj in self.gui_save_exceptions:
                continue
            if value := settings.value(f"{self.save_heading}/{name}"):
                if isinstance(obj, (QtWidgets.QLineEdit, PathEdit)):
                    obj.setText(value)
                elif isinstance(obj, QtWidgets.QSpinBox):
                    obj.setValue(int(value))
                elif isinstance(obj, QtWidgets.QDoubleSpinBox):
                    obj.setValue(float(value))
                elif isinstance(
                    obj,
                    (
                        QtWidgets.QRadioButton,
                        QtWidgets.QCheckBox,
                        QtWidgets.QPushButton,
                    ),
                ):
                    obj.setChecked(strtobool(value))
                elif isinstance(obj, QtWidgets.QComboBox):
                    obj.setCurrentText(value)
