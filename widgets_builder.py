import os
import sys
import qtmodern.styles
import qtmodern.windows
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PySide2.QtCore import Qt, QSize
from PySide2 import QtWidgets, QtCore
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QComboBox, QLabel, QGridLayout, QWidget, QDoubleSpinBox, QPushButton, QHBoxLayout
from PySide2.QtWidgets import QDialog, QLineEdit, QMessageBox, QTreeView, QSizePolicy, QFileSystemModel
from PySide2.QtWidgets import QMainWindow, QSpinBox, QGroupBox, QApplication
from control_api import PortManger
import keyword

matplotlib.use("Qt5Agg")


class Label(QLabel):
    def __init__(self, font_size=16, weight=36, text="new label"):
        super().__init__()
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum)
        f = self.font()
        f.setPointSize(font_size)
        f.setWeight(weight)
        self.setFont(f)
        self.setText(text)
        self.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

    def sizeHint(self):
        self.update()
        return QSize(700, 300)


def icon(icon_name, root="icons"):
    return QIcon(os.path.join(root, icon_name))


def special_characters_detector(name):
    special_characters = "!@  # $%^&*()-+?=,<>/"
    check_list = list((n in special_characters for n in name))
    if True in check_list or name in keyword.kwlist:
        ErrorMassage("Name is not compatible", "The selected name should not contain"
                                               "\nspaces or any special characterises"
                                               "\nand should not be python keyword")
        return True


class ErrorMassage(QMainWindow):
    """error handler for general use """

    def __init__(self, title, message):
        super().__init__()
        self.title = title
        self.message = message
        self.setWindowIcon(QIcon('icons/warning.png'))
        QMessageBox.warning(self, self.title, self.message)


class PumpAbstract(QWidget):
    def __init__(self, name):
        super().__init__()
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum)

        layout = QGridLayout()

        self.pump_port_selection_QComboBox = QComboBox()
        self.pump_port_selection_QComboBox.setMaximumSize(80, 70)
        self.pump_port_selection_QComboBox.addItems(PortManger().get_ports_list)
        self.pump_port_selection_QLabel = QLabel('Select port')

        layout.addWidget(self.pump_port_selection_QLabel, 0, 0)
        layout.addWidget(self.pump_port_selection_QComboBox, 0, 1)

        self.pump_speed_QLabel = QLabel('Speed')
        self.pump_speed_QDoubleSpinBox = QDoubleSpinBox()
        layout.addWidget(self.pump_speed_QLabel, 1, 0)
        layout.addWidget(self.pump_speed_QDoubleSpinBox, 1, 1)

        self.pump_direction_QLabel = QLabel('Direction')
        self.pump_direction_QComboBox = QComboBox()
        self.pump_direction_QComboBox.addItems(["CW", "CCW"])
        layout.addWidget(self.pump_direction_QLabel, 2, 0)
        layout.addWidget(self.pump_direction_QComboBox, 2, 1)

        self.start_stop_QPushButton = QPushButton("Start")
        self.start_stop_QPushButton.setCheckable(True)
        layout.addWidget(self.start_stop_QPushButton, 3, 1)
        layout.setSpacing(3)
        group_box_pump = QGroupBox(name)
        group_box_pump.setLayout(layout)
        v = QHBoxLayout()
        v.addWidget(group_box_pump)
        self.setLayout(v)

    def sizeHint(self):
        return QtCore.QSize(100, 70)


class StepIncreaseWindow(QMainWindow):
    """
    Steps increase window GUI
    """

    def __init__(self):
        super().__init__()
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred)
        self.setWindowTitle("speed adjusting")
        self.setWindowIcon(QIcon(r"../QtIcons/settings.png"))

        layout = QGridLayout()
        self.Select_pump = QLabel('Select Pump')
        self.Select_pump_QComboBox = QComboBox()
        self.Select_pump_QComboBox.addItems(["pump 1", "Pump 2", "Both"])
        layout.addWidget(self.Select_pump, 0, 0)
        layout.addWidget(self.Select_pump_QComboBox, 0, 1)

        self.start_QLabel = QLabel('Start Speed (rpm)')
        self.start_QSpinBox = QSpinBox()
        self.start_QSpinBox.setMaximum(300)
        self.start_QSpinBox.setMinimum(0)
        layout.addWidget(self.start_QLabel, 1, 0)
        layout.addWidget(self.start_QSpinBox, 1, 1)
        self.start_QSpinBox.setValue(2)

        self.stop_QLabel = QLabel('Stop Speed (rpm)')
        self.stop_QSpinBox = QSpinBox()
        layout.addWidget(self.stop_QLabel, 2, 0)
        layout.addWidget(self.stop_QSpinBox, 2, 1)
        self.stop_QSpinBox.setMaximum(300)
        self.stop_QSpinBox.setMinimum(0)
        self.stop_QSpinBox.setValue(10)

        self.step_QLabel = QLabel('Increasing Steps (rpm)')
        self.step_QSpinBox = QSpinBox()
        layout.addWidget(self.step_QLabel, 3, 0)
        layout.addWidget(self.step_QSpinBox, 3, 1)
        self.step_QSpinBox.setMaximum(300)
        self.step_QSpinBox.setMinimum(1)
        self.step_QSpinBox.setValue(1)

        self.duration_QLabel = QLabel('Duration (S)')
        self.duration_QSpinBox = QSpinBox()
        layout.addWidget(self.duration_QLabel, 4, 0)
        layout.addWidget(self.duration_QSpinBox, 4, 1)
        self.duration_QSpinBox.setValue(1)

        # Ok button Setting
        self.start_ = QPushButton("Start")
        self.start_.clicked.connect(self.start_it)
        layout.addWidget(self.start_, 5, 0)
        gb = QGroupBox()
        gb.setLayout(layout)
        self.setCentralWidget(gb)

    def start_it(self):
        print("starting ...")

    def sizeHint(self):
        return QtCore.QSize(100, 70)


class NewProjectSetNameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Create New Project")
        self.file_name_QLabel = QLabel("Project Name")
        self.warning_QLabel = QLabel("Project Name must be one word or multiple\nwords connected with '_'")
        self.save_QPushButton = QPushButton("Create")
        self.cancel_QPushButton = QPushButton("Cancel")
        self.layout = QGridLayout()
        self.file_name_QLineEdit = QLineEdit()
        self.layout.addWidget(self.warning_QLabel, 0, 0, 1, 3)
        self.layout.addWidget(self.file_name_QLabel, 2, 0)
        self.layout.addWidget(self.file_name_QLineEdit, 2, 1, 1, 2)
        self.layout.setVerticalSpacing(30)
        self.layout.addWidget(self.save_QPushButton, 4, 1)
        self.layout.addWidget(self.cancel_QPushButton, 4, 2)
        self.setLayout(self.layout)
        self.setWindowIcon(icon("plus.png"))


class SetNewTableDialog(NewProjectSetNameDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create New Table")
        self.file_name_QLabel.setText("Table Name")
        self.warning_QLabel.setText("You Have to choose where you want to save this table\nand the table Name"
                                    " must be one word or multiple\nwords connected with '_'")
        self.layout.setVerticalSpacing(12)
        self.table_QComboBox = QComboBox()
        self.table_QLabel = QLabel("Project Name")
        self.layout.addWidget(self.table_QLabel, 1, 0)
        self.layout.addWidget(self.table_QComboBox, 1, 1, 1, 2)
        self.size_QLabel = QLabel("Size (n x m)")
        self.layout.addWidget(self.size_QLabel, 3, 0)

        self.table_col_QSpinBox = QSpinBox()
        self.table_row_QSpinBox = QSpinBox()

        self.layout.addWidget(self.table_col_QSpinBox, 3, 1)
        self.layout.addWidget(self.table_row_QSpinBox, 3, 2)


class FileTreeViewer(QTreeView):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        model = QFileSystemModel()
        model.setRootPath(os.getcwd())

        # tree = QTreeView()
        self.setModel(model)

        self.setRootIndex(model.index(os.path.join(os.getcwd(), 'saved_projects')))
        self.hideColumn(1)
        self.hideColumn(2)
        self.hideColumn(3)

    def sizeHint(self):
        return QSize(150, 200)


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    win = StepIncreaseWindow()

    qtmodern.styles.dark(app)
    # mw = qtmodern.windows.ModernWindow(win)
    win.show()

    app.exec_()
