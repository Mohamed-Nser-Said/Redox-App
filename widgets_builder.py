import os
import sys
# import qtmodern.styles
# import qtmodern.windows
from PySide2.QtCore import Qt, QSize, Signal
from PySide2 import QtWidgets, QtCore
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QComboBox, QLabel, QGridLayout, QWidget, QDoubleSpinBox, QPushButton, QHBoxLayout, \
    QListWidget, QListWidgetItem
from PySide2.QtWidgets import QDialog, QLineEdit, QMessageBox, QTreeView, QSizePolicy, QFileSystemModel
from PySide2.QtWidgets import QMainWindow, QSpinBox, QGroupBox, QApplication
from control_api import PortManger
import keyword


class Label(QLabel):
    def __init__(self, font_size=16, weight=36, text="new label"):
        super().__init__()
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred)
        f = self.font()
        f.setPointSize(font_size)
        # f.setWeight(weight)
        # self.setStyleSheet('background-color:#bfbfbf')
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
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred)

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

        self.pump_send_state_QPushButton = QPushButton("send")
        # self.pump_send_state_QPushButton.setCheckable(True)
        layout.addWidget(self.pump_send_state_QPushButton, 3, 1)
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
        self.setWindowIcon(icon("stepincrease.png"))

        layout = QGridLayout()
        self.Select_pump = QLabel('Select Pump')
        self.Select_pump_QComboBox = QComboBox()
        self.Select_pump_QComboBox.addItems(PortManger().get_ports_list)
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


class OpenProjectDialog(NewProjectSetNameDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Open Project")
        self.file_name_QLabel.setText("Project Name")
        self.warning_QLabel.setText("Select your Project Please")
        self.save_QPushButton.setText("Open")
        self.project_list_QComboBox = QComboBox()
        self.layout.addWidget(self.project_list_QComboBox, 2, 1, 1, 2)


class CreateNewGraphDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("New 2D Graph")
        self.setWindowIcon(icon("plus.png"))
        self.file_name_QLabel = QLabel("x axes dataset")
        self.warning_QLabel = QLabel("Please select the datasets for x and y axes")
        self.file_name2_QLabel = QLabel("y axes dataset")

        self.save_QPushButton = QPushButton("Create")
        self.cancel_QPushButton = QPushButton("Cancel")
        self.select_color_QPushButton = QPushButton("Select Color")

        self.x_dataset_list_QComboBox = QComboBox()
        self.y_dataset_list_QComboBox = QComboBox()
        self.size_QComboBox = QSpinBox()
        self.plot_name_QLabel = QLabel("Plot Name")
        self.title_QLabel = QLabel("Title")
        self.x_axis_name_QLabel = QLabel("X-Axis")
        self.y_axis_QLabel = QLabel("Y-Axis")
        self.size_QLabel = QLabel("Size")

        self.plot_name_QLineEdit = QLineEdit('Plot Name')
        self.title_QLineEdit = QLineEdit('Title')
        self.x_axis_name_QLineEdit = QLineEdit('X-Axis')
        self.y_axis_name_QLineEdit = QLineEdit('Y-Axis')

        self.layout = QGridLayout()

        self.layout.addWidget(self.warning_QLabel, 0, 0, 1, 3)
        self.layout.addWidget(self.file_name_QLabel, 2, 0)
        self.layout.addWidget(self.x_dataset_list_QComboBox, 2, 1, 1, 2)
        self.layout.addWidget(self.y_dataset_list_QComboBox, 3, 1, 1, 2)
        self.layout.addWidget(self.file_name2_QLabel, 3, 0)

        self.layout.addWidget(self.plot_name_QLabel, 4, 0)
        self.layout.addWidget(self.plot_name_QLineEdit, 4, 1, 1, 2)

        self.layout.addWidget(self.title_QLabel, 5, 0)
        self.layout.addWidget(self.title_QLineEdit, 5, 1, 1, 2)

        self.layout.addWidget(self.x_axis_name_QLabel, 6, 0)
        self.layout.addWidget(self.x_axis_name_QLineEdit, 6, 1, 1, 2)

        self.layout.addWidget(self.y_axis_QLabel, 7, 0)
        self.layout.addWidget(self.y_axis_name_QLineEdit, 7, 1, 1, 2)

        self.layout.addWidget(self.size_QLabel, 8, 0)
        self.layout.addWidget(self.size_QComboBox, 8, 1, 1, 2)

        self.layout.setVerticalSpacing(30)
        self.layout.addWidget(self.save_QPushButton, 9, 0)
        self.layout.addWidget(self.cancel_QPushButton, 9, 1)
        self.layout.addWidget(self.select_color_QPushButton, 9, 2)
        self.setLayout(self.layout)


class NewTableDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Create New Table")
        self.setWindowIcon(icon("plus.png"))
        self.layout = QGridLayout()
        self.warning_QLabel = QLabel("These are the available data sets stored in this project "
                                     "please drag and drop the preferred data")

        self.table_name_QLabel = QLabel("Table Name")
        self.table_name_QLineEdit = QLineEdit()

        self.save_QPushButton = QPushButton("Create")
        self.cancel_QPushButton = QPushButton("Cancel")

        self.dataset_QListWidget = QListWidget()
        self.dataset_QListWidget.setAcceptDrops(False)
        self.dataset_QListWidget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ContiguousSelection)

        self.setGeometry(300, 350, 500, 300)
        self.layout_h = QHBoxLayout()
        self.layout_h.addWidget(self.save_QPushButton)
        self.layout_h.addWidget(self.cancel_QPushButton)

        self.layout.addWidget(self.warning_QLabel, 0, 0, 1, 2)
        self.layout.addWidget(self.table_name_QLabel, 1, 0)
        self.layout.addWidget(self.table_name_QLineEdit, 1, 1)
        self.layout.addWidget(self.dataset_QListWidget, 2, 0, 1, 2)
        self.layout.addLayout(self.layout_h, 3, 0, 1, 2)

        self.setLayout(self.layout)

    def add_list(self, items=['data set1', 'data set 2', 'data set3', 'data set 4']):

        for i, j in enumerate(items):
            l = QListWidgetItem(j)
            l.setCheckState(Qt.CheckState.Unchecked)
            self.dataset_QListWidget.insertItem(i + 1, l)


class FileTreeViewer(QTreeView):
    FileOpenedSignal = Signal(dict)

    def __init__(self, parent):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.project_name = None

        self.model = QFileSystemModel()

    def new_project_added(self):
        self.setModel(self.model)
        self.model.setRootPath(os.getcwd())
        self.setRootIndex(self.model.index(os.path.join(os.getcwd(), 'saved_projects', self.project_name)))
        self.hideColumn(1)
        self.hideColumn(2)
        self.hideColumn(3)

    def mouseDoubleClickEvent(self, e):
        try:
            file_path = self.model.filePath(self.currentIndex())
            file_name = self.currentIndex().data().split(".")[0]
            file_type = os.path.splitext(file_path)[1]

            file = {'file_path': file_path,
                    'file_name': file_name,
                    'file_type': file_type
                    }

            self.FileOpenedSignal.emit(file)

        except Exception as e:
            self.error_message(str(e))

    def error_message(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

    def sizeHint(self):
        return QSize(150, 200)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    win = NewTableDialog()
    win.show()

    app.exec_()
