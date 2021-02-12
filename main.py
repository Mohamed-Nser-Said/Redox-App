from io import StringIO
from random import randint
import threading

import h5py
import qtmodern
from PySide2.QtCore import QSize, Qt, QAbstractTableModel, Signal, QTimer, QRunnable, Slot, QThreadPool
from PySide2.QtGui import QIcon, QKeySequence, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide2.QtWidgets import QApplication, QMainWindow, QStatusBar, QToolBar, QFileDialog, QTabWidget, QTextEdit, \
    QAction, QVBoxLayout
from PySide2.QtWidgets import QLabel, QLineEdit, QGridLayout, QHBoxLayout, QGroupBox, QComboBox, QWidget, QPlainTextEdit
from PySide2.QtWidgets import QMdiArea, QMdiSubWindow, QDockWidget, QTableView, QSizePolicy, QMessageBox, QPushButton
from control_api import PumpMode, Pump, PumpModbusCommandSender, ModbusBuilder
from widgets_builder import NewProjectSetNameDialog, SetNewTableDialog, ErrorMassage, Label, FileTreeViewer
from widgets_builder import PumpAbstract, icon, special_characters_detector, StepIncreaseWindow, OpenProjectDialog
import numpy as np
# import qtmodern.windows
# import tables as tb
import os
import sys
import pyvisa

MAIN_PROJECTS_SAVED_FILE = "saved_projects"
SUB_MAIN_PROJECTS_SAVED_FILE = ["hsf5-data", 'Graphs', 'Reports', 'Notes', 'Procedure']

if not os.path.exists(MAIN_PROJECTS_SAVED_FILE):
    os.mkdir(MAIN_PROJECTS_SAVED_FILE)

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import pyqtgraph as pg
from pyqtgraph import PlotWidget, plot

matplotlib.use("Qt5Agg")


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=10):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)


class GraphMaker1(QMainWindow):
    def __init__(self):
        super().__init__()

        sc = MplCanvas(self, width=5, height=4, dpi=100)
        sc.axes.plot([0, 1, 2, 3, 4], [10, 1, 20, 3, 40])

        # Create toolbar, passing canvas as first parament, parent (self, the MainWindow) as second.
        toolbar = NavigationToolbar(sc, self)

        layout = QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(sc)

        # Create a placeholder widget to hold our toolbar and canvas.
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)


class GraphMaker2(QMainWindow):
    def __init__(self):
        super().__init__()

        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)

        hour = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        temperature = [30, 32, 34, 32, 33, 31, 29, 32, 35, 45]

        # plot data: x, y values
        self.graphWidget.plot(hour, temperature)


class GraphMaker(QMainWindow):
    def __init__(self):
        super().__init__()

        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)

        self.x = list(range(100))  # 100 time points
        self.y = [randint(0, 100) for _ in range(100)]  # 100 data points

        self.graphWidget.setBackground("w")

        pen = pg.mkPen(color=(255, 0, 0))
        self.data_line = self.graphWidget.plot(self.x, self.y, pen=pen)  # <1>

        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def update_plot_data(self):
        self.x = self.x[1:]  # Remove the first y element.
        self.x.append(self.x[-1] + 1)  # Add a new value 1 higher than the last.

        self.y = self.y[1:]  # Remove the first
        self.y.append(randint(0, 100))  # Add a new random value.

        self.data_line.setData(self.x, self.y)  # Update the data.


class CreateNewGraphAction(QAction):
    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.setText("New Graph")
        self.setStatusTip("Creat a New Graph")
        self.setIcon(icon("line-graph.png"))

        self.triggered.connect(self.create_new_graph)

    def create_new_graph(self):
        self.parent().add_sub_win(GraphMaker())


class StepFunction(StepIncreaseWindow):
    def __init__(self):
        super(StepFunction, self).__init__()

    def start_it(self):
        pass


class StepFunctionAction(QAction):
    StepFunctionAddedSignal = Signal(str)

    def __init__(self, parent):
        super().__init__()
        self.setText("step function")
        self.setIcon(icon("stepincrease.png"))
        self.setStatusTip("step function tool")
        self.setParent(parent)
        self.triggered.connect(self.clicked)

    def clicked(self):
        self.parent().add_sub_win(StepFunction())


class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio  # free up some memory
        sys.stdout = self._stdout


class TextEditor(QMainWindow):
    AddProcedureClickedSignal = Signal(str)

    def __init__(self):
        super().__init__()

        t = """ModbusBuilder = ModbusBuilder()
start = ModbusBuilder.build_start()
stop = ModbusBuilder.build_stop()
speed = ModbusBuilder.build_change_speed(1)
direction_cc = ModbusBuilder.build_flow_direction("cw")
direction_ccw = ModbusBuilder.build_flow_direction("ccw")
p = PumpModbusCommandSender()
p.send_pump(data=stop, send_to=Pump.MASTER)"""
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout = QGridLayout()
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.out_put_TextEdit = QTextEdit()
        # self.out_put_TextEdit.setMaximumHeight(150)
        self.out_put_TextEdit.setReadOnly(True)
        self.out_put_TextEdit.setStyleSheet("color: blue;")
        self.out_put_TextEdit_dock = CreateDockWindows(title="OutPut", parent=self,
                                                       widget=self.out_put_TextEdit,
                                                       area=Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.out_put_TextEdit_dock)

        self.toolbar = QToolBar("main toolbar")
        self.toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(self.toolbar)

        run_action = QAction(icon("play.png"), "Run", self)
        run_action.setStatusTip("Run your procedure")
        run_action.triggered.connect(self.run)
        self.toolbar.addAction(run_action)

        self.toolbar.addSeparator()

        save_action = QAction(icon("save.png"), "Save", self)
        save_action.setStatusTip("Save your procedure")
        save_action.triggered.connect(self.procedure_save)
        self.toolbar.addAction(save_action)

        self.toolbar.addSeparator()

        add_action = QAction(icon("add.png"), "Add Procedure", self)
        add_action.setStatusTip("Add your procedure to the toolbar")
        add_action.triggered.connect(self.add_procedure)
        self.toolbar.addAction(add_action)

        self.file_name_QLineEdit = QLineEdit()
        self.file_name_QLineEdit.setText('procedure.py')
        self.file_name_QLabel = QLabel("Procedure Name")

        self.procedure_QTextEdit = QTextEdit()
        self.procedure_QTextEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        Highlighter(self.procedure_QTextEdit.document())
        self.procedure_QTextEdit.append(t)

        f = self.font()
        f.setFamily('verdana')
        f.setPointSize(11)
        self.procedure_QTextEdit.setFont(f)
        self.procedure_QTextEdit.setStyleSheet("color: black;")

        layout.addWidget(self.file_name_QLabel, 0, 0, 1, 1)
        layout.addWidget(self.file_name_QLineEdit, 0, 1, 1, 1)
        layout.addWidget(self.procedure_QTextEdit, 1, 0, 3, 3)

    def error_message(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

    def add_procedure(self):
        self.AddProcedureClickedSignal.emit(self.file_name_QLineEdit.text())

    def procedure_save(self):
        project_name = window.project_name
        file_name = self.file_name_QLineEdit.text()

        if file_name == "":
            file_name = "no_name.py"

        elif ".py" not in file_name and len(file_name) > 1:
            file_name += '.py'

        path = os.path.join(os.getcwd(), MAIN_PROJECTS_SAVED_FILE, project_name,
                            SUB_MAIN_PROJECTS_SAVED_FILE[4], file_name)

        text = self.procedure_QTextEdit.toPlainText()
        try:
            with open(path, 'w') as f:
                f.write(text)

        except Exception as e:
            self.error_message(str(e))

        # self.parent().hide()

    def procedure_open(self, path, name):
        try:
            with open(path) as f:
                text = f.read()

        except Exception as e:
            self.dialog_critical(str(e))

        else:
            self.procedure_QTextEdit.setPlainText(text)
            self.file_name_QLineEdit.setText(name)

    def run(self):

        def __exc():
            try:
                self.out_put_TextEdit.setStyleSheet("color: blue;")
                with Capturing() as output:
                    exec(self.procedure_QTextEdit.toPlainText())
                for _ in output:
                    self.out_put_TextEdit.append(str(_))
            except Exception as e:
                self.out_put_TextEdit.setStyleSheet("color: red;")
                self.out_put_TextEdit.append(str(e))

        t = threading.Thread(target=__exc)
        t.start()

    def sizeHint(self):
        return QSize(900, 700)


class NewTextEditorAction(QAction):
    NewTextEditorAddedSignal = Signal(str)

    def __init__(self, parent):
        super().__init__()
        # self.thread_pool = QThreadPool()
        self.setText("New Procedure")
        self.setIcon(icon("procedure.png"))
        self.setStatusTip("start a new procedure")
        self.setParent(parent)
        self.triggered.connect(self.clicked)

    def clicked(self):
        self.parent().add_sub_win(TextEditor())


class Highlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        _format = QTextCharFormat()
        # _format.setFontWeight(QFont.Bold)

        key_list_1 = ['False', 'None', 'True', 'and', 'as', 'break', 'class',
                      'continue', 'def', 'elif', 'else', 'except', 'finally', 'for', 'from',
                      'if', 'import', 'in', 'is', 'lambda', 'not', 'or', 'pass', 'raise', 'return',
                      'try', 'while', 'with', 'not', 'yield', 'str', 'int', 'self', 'range', 'print', ]

        key_list_2 = [':', '(', ')', '=', '>', '<', ',',
                      '!', '/', '"', "."]

        key_list_3 = [str(i) for i in range(10)]

        for expression in key_list_2 + key_list_1 + key_list_3:

            try:
                index = text.index(expression)
                if expression in key_list_1:
                    _format.setForeground(Qt.darkMagenta)
                elif expression in key_list_2:
                    _format.setForeground(Qt.red)

                elif expression in key_list_3:
                    _format.setForeground(Qt.blue)

            except Exception as e:
                str(e)
                index = -1

            while index >= 0:
                length = len(expression)
                self.setFormat(index, length, _format)

                try:
                    index = text.index(expression, index + length)
                except:
                    index = -1


class NotePad(QWidget):

    def __init__(self):
        super().__init__()
        layout = QGridLayout()

        self.setLayout(layout)
        self.note_QPlainTextEdit = QPlainTextEdit()
        self.note_name_QLineEdit = QLineEdit()
        self.note_name_QLabel = QLabel("Note Name")

        layout.addWidget(self.note_name_QLabel, 0, 0, 1, 1)
        layout.addWidget(self.note_name_QLineEdit, 0, 1, 1, 1)
        layout.addWidget(self.note_QPlainTextEdit, 1, 0, 3, 3)

        save_note = QPushButton(icon("save.png"), "Save", self)
        save_note.clicked.connect(self.note_save)

        cancel_note = QPushButton("Cancel", self)
        cancel_note.clicked.connect(lambda: self.parent().close())

        layout.addWidget(save_note, 4, 0, 1, 1)
        layout.addWidget(cancel_note, 4, 1, 1, 1)

    def error_message(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

    def note_save(self):
        project_name = window.project_name
        note_name = self.note_name_QLineEdit.text()
        if note_name == "":
            note_name = "no_name"
        path = os.path.join(os.getcwd(), MAIN_PROJECTS_SAVED_FILE, project_name,
                            SUB_MAIN_PROJECTS_SAVED_FILE[3], f"{note_name}.txt")

        text = self.note_QPlainTextEdit.toPlainText()
        try:
            with open(path, 'w') as f:
                f.write(text)

        except Exception as e:
            self.error_message(str(e))

        self.parent().hide()

    def note_open(self, path, name):
        try:
            with open(path) as f:
                text = f.read()

        except Exception as e:
            self.dialog_critical(str(e))

        else:
            self.note_QPlainTextEdit.setPlainText(text)
            self.note_name_QLineEdit.setText(name)


class CreateNotePadAction(QAction):
    CreateNewNoteClicked = Signal(object)

    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.setText("Create New Note")
        self.setIcon(icon("note.png"))
        self.setStatusTip("Create New Note")
        self.triggered.connect(self.clicked)

    def clicked(self):
        self.CreateNewNoteClicked.emit(NotePad())


class TableModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.DisplayRole:
            # See below for the nested-list data structure.
            # .row() indexes into the outer list,
            # .column() indexes into the sub-list
            return self._data[index.row()][index.column()]

    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return len(self._data[0])


class TableViewer(QMainWindow):
    def __init__(self, data=None):
        super().__init__()

        self.table = QTableView()
        if data is None:
            data = np.arange(0, 100).reshape(20, 5)

        self.model = TableModel(data)
        self.table.setModel(self.model)

        self.setCentralWidget(self.table)


class CreateNewProjectFileTree:
    def __init__(self, project_name):
        self.project_name = project_name
        self.back_dir = os.getcwd()
        if not os.path.exists(MAIN_PROJECTS_SAVED_FILE):
            os.mkdir(MAIN_PROJECTS_SAVED_FILE)
        os.chdir(MAIN_PROJECTS_SAVED_FILE)

    def create_dir(self):

        if os.path.exists(self.project_name):
            ErrorMassage("Name already exist", "this name is already exist\nplease try different name")
            os.chdir(self.back_dir)
            return False
        elif special_characters_detector(self.project_name):
            os.chdir(self.back_dir)
            return False
        else:
            for file in SUB_MAIN_PROJECTS_SAVED_FILE:
                path = os.path.join(self.project_name, file)
                os.makedirs(path)

            os.chdir(self.back_dir)
            return True


class PumpQWidget(QWidget):
    PumpSignalSend = Signal(dict)

    def __init__(self):
        super().__init__()

        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        # self.PumpModbusCommandSender = PumpModbusCommandSender()
        self.pump_mode_state = PumpMode.COUPLED
        group_box_pump_mode = QGroupBox("Mode")
        self.mode_QLabel = QLabel("Pump Mode")
        self.mode_QComboBox = QComboBox()
        self.mode_QComboBox.addItems(["coupled", "decoupled"])
        self.mode_QComboBox.currentTextChanged.connect(self.pump_mode_changed)
        h_layout_pump_mode = QHBoxLayout()
        h_layout_pump_mode.addWidget(self.mode_QLabel)
        h_layout_pump_mode.addWidget(self.mode_QComboBox)
        group_box_pump_mode.setLayout(h_layout_pump_mode)

        self.pump1 = PumpAbstract("Pump 1")
        self.pump1.pump_send_state_QPushButton.clicked.connect(lambda: self.send_to_pump(self.pump1))
        self.pump2 = PumpAbstract("Pump 2")
        self.pump2.pump_send_state_QPushButton.clicked.connect(lambda: self.send_to_pump(self.pump2))
        self.pump2.setDisabled(True)

        g_layout = QGridLayout()
        g_layout.addWidget(group_box_pump_mode, 0, 0, 1, 1)
        g_layout.addWidget(self.pump1, 1, 0, 2, 1)
        g_layout.addWidget(self.pump2, 3, 0, 2, 1)
        g_layout.setSpacing(0)
        self.setLayout(g_layout)

    def sizeHint(self):
        return QSize(100, 50)

    def pump_mode_changed(self):
        if self.mode_QComboBox.currentText() == "coupled":
            self.pump2.setDisabled(True)
            self.pump_mode_state = PumpMode.COUPLED
        else:
            self.pump2.setDisabled(False)
            self.pump_mode_state = PumpMode.DECOUPLED

    def send_to_pump(self, pump):
        parameters = {
            'pump_mode': self.pump_mode_state,
            'port': pump.pump_port_selection_QComboBox.currentText(),
            'speed': pump.pump_speed_QDoubleSpinBox.value(),
            'direction': pump.pump_direction_QComboBox.currentText()
        }

        self.PumpSignalSend.emit(parameters)


class SCPICommandLine(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout = QGridLayout()
        self.setLayout(layout)

        self.rm = pyvisa.ResourceManager()
        a = self.rm.list_resources()

        self.pyvisaQLineEdit = QLineEdit()
        self.historyQPlainTextEdit = QPlainTextEdit()
        self.historyQPlainTextEdit.setReadOnly(True)
        self.historyQPlainTextEdit.setStyleSheet("color: blue;")
        self.pyvisa_list_resources_QComboBox = QComboBox()
        self.pyvisa_list_resources_QComboBox.addItems(a)
        self.pyvisa_list_resources_QComboBox.setFixedSize(80, 20)

        layout.addWidget(self.pyvisa_list_resources_QComboBox, 0, 0, 1, 1)
        layout.addWidget(self.historyQPlainTextEdit, 1, 0, 2, 2)
        layout.addWidget(self.pyvisaQLineEdit, 2, 0, 1, 2)

        f = self.font()
        f.setFamily('verdana')
        f.setPointSize(14)
        # f.setWeight(5)
        self.pyvisaQLineEdit.setFont(f)
        self.pyvisaQLineEdit.setStyleSheet("color: red;")
        self.pyvisaQLineEdit.clear()
        # self.setEnabled(False)
        self.pyvisaQLineEdit.returnPressed.connect(self.pressed)

    def sizeHint(self):
        return QSize(1080, 100)

    def pressed(self):
        # my_instrument = self.rm.open_resource(self.pyvisa_list_resources_QComboBox.currentText())
        cmd = self.pyvisaQLineEdit.text()
        self.historyQPlainTextEdit.appendPlainText(f'>> {cmd}')
        # my_instrument.write(cmd)

        self.pyvisaQLineEdit.clear()


class NewProjectAction(QAction):
    NewProjectAddedSignal = Signal(str)

    def __init__(self, parent):
        super().__init__()

        self.NewProjectSetNameDialog = NewProjectSetNameDialog()
        self.triggered.connect(self.NewProjectSetNameDialog.show)
        self.NewProjectSetNameDialog.save_QPushButton.clicked.connect(self.save_project_name_dialog)
        self.NewProjectSetNameDialog.cancel_QPushButton.clicked.connect(self.NewProjectSetNameDialog.close)
        self.setText("New Project")
        self.setIcon(icon("new_project.png"))
        self.setStatusTip("start a new project")
        self.setParent(parent)
        self.setShortcut(QKeySequence("Ctrl+n"))

    def save_project_name_dialog(self):
        project_name = self.NewProjectSetNameDialog.file_name_QLineEdit.text()

        if CreateNewProjectFileTree(project_name).create_dir():
            DataBase(project_name).create_new_hdf5_file()

            self.NewProjectSetNameDialog.hide()
            self.NewProjectAddedSignal.emit(project_name)


class OpenProjectAction(QAction):
    OpenProjectActionClickedSignal = Signal(str)

    def __init__(self, parent):
        super().__init__()
        self.setText("Open")
        self.setParent(parent)
        self.setShortcut(QKeySequence("Ctrl+o"))
        self.setIcon(icon("open.png"))
        self.setStatusTip("open old project")

        self.OpenProjectDialog = OpenProjectDialog()
        self.OpenProjectDialog.save_QPushButton.clicked.connect(self.clicked)
        self.OpenProjectDialog.cancel_QPushButton.clicked.connect(self.OpenProjectDialog.close)

        self.triggered.connect(self.triggered_open)

    def triggered_open(self):
        self.OpenProjectDialog.project_list_QComboBox.clear()
        self.OpenProjectDialog.project_list_QComboBox.addItems(os.listdir('saved_projects'))

        self.OpenProjectDialog.show()

    def clicked(self):
        # file, _ = QFileDialog.getOpenFileName(self.parent(), "Open Project", os.path.join(os.getcwd(),
        #                                                                                   MAIN_PROJECTS_SAVED_FILE))
        self.OpenProjectActionClickedSignal.emit(self.OpenProjectDialog.project_list_QComboBox.currentText())
        self.OpenProjectDialog.hide()


class CreatNewTableAction(QAction):
    NewTableCreatedSignal = Signal(dict)

    def __init__(self, parent):
        super().__init__()
        self.setText("New Table")
        self.setStatusTip("Creat a New Table")
        self.setIcon(icon("new_table"))
        self.SetNewTableDialog = SetNewTableDialog()
        self.SetNewTableDialog.cancel_QPushButton.clicked.connect(self.SetNewTableDialog.close)
        self.SetNewTableDialog.save_QPushButton.clicked.connect(self.create_new_table)
        self.triggered.connect(self.show_table_dialog)
        self.setParent(parent)

    def create_new_table(self):
        table_name = self.SetNewTableDialog.file_name_QLineEdit.text()
        project_name = self.SetNewTableDialog.table_QComboBox.currentText()  # HDF5 file
        n_row = self.SetNewTableDialog.table_row_QSpinBox.value()
        n_col = self.SetNewTableDialog.table_col_QSpinBox.value()

        if special_characters_detector(table_name):
            return

        data = DataBase(project_name).create_new_array(name=table_name, data=np.arange(0, 100).reshape(20, 5))
        self.NewTableCreatedSignal.emit(
            {"table_name": table_name, "project_name": project_name, "data": data, "size": (n_row, n_col)})
        self.SetNewTableDialog.hide()

    def show_table_dialog(self):
        self.SetNewTableDialog.table_QComboBox.clear()
        self.SetNewTableDialog.table_QComboBox.addItems(os.listdir(MAIN_PROJECTS_SAVED_FILE))
        self.SetNewTableDialog.show()


class DataBase:
    def __init__(self, project_name):
        self.main_file = os.path.join(os.getcwd(), MAIN_PROJECTS_SAVED_FILE, project_name,
                                      SUB_MAIN_PROJECTS_SAVED_FILE[0], f"{project_name}.h5")

    def create_new_hdf5_file(self):
        with h5py.File(self.main_file, "a") as t:
            pass

    # def create_new_table(self, table_name):
    #
    #     class Description(tb.IsDescription):
    #         time_stamp = tb.Int32Col()
    #         pump_1_speed = tb.Float64Col()
    #         pump_2_speed = tb.Float64Col()
    #         voltage = tb.Float64Col()
    #         note = tb.StringCol(itemsize=5)
    #
    #     try:
    #         with tb.open_file(self.main_file, "a") as t:
    #             a = t.create_table(t.root, table_name, Description)
    #             # a.append(image)
    #
    #     except tb.exceptions.NodeError:
    #         return ErrorMassage("Name already exist", "this name is already exist\nplease try different name")
    #
    def create_new_array(self, name, size=None, data=np.array([])):
        try:
            with h5py.File(self.main_file, "a") as f:
                a = f.create_dataset(name=name, data=data)
                print(a)
                return a
        except:
            return ErrorMassage("Error", "something went wrong try again")


class HelpAction(QAction):
    def __init__(self):
        super().__init__()
        self.setText("Help")
        self.setStatusTip("Need Help")
        self.triggered.connect(self.clicked)
        self.setShortcut(QKeySequence("Ctrl+h"))

    def clicked(self):
        pass


class AboutAction(QAction):
    def __init__(self):
        super().__init__()
        self.setText("About")
        self.triggered.connect(self.clicked)

    def clicked(self):
        print("about")


class MonitorAction(QAction):
    def __init__(self):
        super().__init__()
        self.setText("Monitor")
        self.triggered.connect(self.clicked)

    def clicked(self):
        print("Monitor ...")


class DarkModeAction(QAction):
    def __init__(self):
        super().__init__()
        self.setText("DarkMode")
        self.setIcon(icon("dark_mode.png"))
        self.triggered.connect(self.clicked)
        self.setCheckable(True)

    @staticmethod
    def clicked(s):
        if s:
            # qtmodern.
            qtmodern.styles.dark(app)
        else:
            qtmodern.styles.light(app)


class CreateDockWindows(QDockWidget):
    def __init__(self, title="No title", parent=None, widget=None, area=None):
        super().__init__()
        self.setWindowTitle(title)
        self.setParent(parent)
        self.setAllowedAreas(area)
        self.setWidget(widget)


class RemoteAction(QAction):
    def __init__(self, parent):
        super().__init__()
        self.setText("Remote")
        self.setStatusTip("start remote connection")
        self.setParent(parent)
        self.setCheckable(True)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.remote = False
        self.project_name = None

        self.setDocumentMode(True)
        self.setWindowTitle("RedoX App 2.1")
        self.setWindowIcon(icon("app.png"))

        self.label = Label(text="Create New Project Ctrl+N")
        self.setCentralWidget(self.label)

        self.mdi = QMdiArea()

        # QDocks
        self.PumpQWidget = PumpQWidget()
        self.PumpQWidget_dock = CreateDockWindows(title="Pump control", parent=self, widget=self.PumpQWidget,
                                                  area=Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.FileTreeViewer = FileTreeViewer(self)
        self.FileTreeViewer_dock = CreateDockWindows(title="File Tree", parent=self, widget=self.FileTreeViewer,
                                                     area=Qt.LeftDockWidgetArea)

        self.SCPICommandLine = SCPICommandLine()
        self.SCPICommandLine_dock = CreateDockWindows(title="SCPI Command Line", parent=self,
                                                      widget=self.SCPICommandLine,
                                                      area=Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)

        self.addDockWidget(Qt.RightDockWidgetArea, self.PumpQWidget_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.FileTreeViewer_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.SCPICommandLine_dock)

        # all actions
        self.help_action = HelpAction()
        self.about_action = AboutAction()
        self.monitor = MonitorAction()

        self.dark_mode_action = DarkModeAction()
        self.NewProjectAction = NewProjectAction(self)
        self.OpenProjectAction = OpenProjectAction(self)
        self.CreatNewTableAction = CreatNewTableAction(self)
        self.CreateNotePadAction = CreateNotePadAction(self)
        self.NewTextEditorAction = NewTextEditorAction(self)
        self.StepFunctionAction = StepFunctionAction(self)
        self.CreateNewGraphAction = CreateNewGraphAction(self)
        self.RemoteAction = RemoteAction(self)


        #####################
        # signals and slots
        self.CreateNotePadAction.CreateNewNoteClicked.connect(self.add_sub_win)
        self.FileTreeViewer.FileOpenedSignal.connect(self.file_opened)
        self.NewProjectAction.NewProjectAddedSignal.connect(self.new_project_created)
        self.OpenProjectAction.OpenProjectActionClickedSignal.connect(self.new_project_created)
        self.PumpQWidget.PumpSignalSend.connect(lambda _: print(_))
        self.RemoteAction.triggered.connect(self.remote_trigger)

        # self.CreatNewTableAction.NewTableCreatedSignal.connect(self.NewProjectTab.append_new_tabel)
        #########################
        self.menu = self.menuBar()
        self.file = self.menu.addMenu("File")
        self.file.addAction(self.NewProjectAction)
        self.file.addAction(self.OpenProjectAction)

        self.tools = self.menu.addMenu("Tools")
        self.tools.addAction(self.CreateNotePadAction)
        self.tools.addAction(self.StepFunctionAction)
        self.tools.addAction(self.NewTextEditorAction)

        self.view = self.menu.addMenu("View")
        self.appearance = self.view.addMenu("Appearance")
        self.appearance.addAction(self.dark_mode_action)

        self.table = self.menu.addMenu("Tables")
        self.table.addAction(self.CreatNewTableAction)

        self.graph = self.menu.addMenu("Graph")
        self.graph.addAction(self.CreateNewGraphAction)

        self.remote_menu = self.menu.addMenu("Remote")
        self.remote_menu.addAction(self.RemoteAction)

        self.help = self.menu.addMenu("Help")

        self.help.addAction(self.help_action)
        self.help.addAction(self.about_action)

        self.toolbar = QToolBar("main toolbar")
        self.toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(self.toolbar)

        self.toolbar.addAction(self.NewProjectAction)
        self.toolbar.addAction(self.OpenProjectAction)
        self.toolbar.addAction(self.CreateNotePadAction)
        self.toolbar.addAction(self.NewTextEditorAction)

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.dark_mode_action)
        self.toolbar.addSeparator()

        self.project_toolbar = QToolBar("project")
        # self.addToolBar(Qt.RightToolBarArea, self.project_toolbar)
        self.addToolBar(self.project_toolbar)
        self.project_toolbar.setIconSize(QSize(16, 16))
        self.project_toolbar.setMovable(False)

        self.project_toolbar.addAction(self.CreatNewTableAction)

        self.setStatusBar(QStatusBar(self))
        self.set_disable_enable_widgets(True)

    def sizeHint(self):
        return QSize(1080, 650)

    def new_project_created(self, name):
        self.set_disable_enable_widgets(False)
        self.project_name = name
        self.FileTreeViewer.project_name = name
        self.FileTreeViewer.new_project_added()

    def set_disable_enable_widgets(self, boo):
        self.remote_menu.setDisabled(boo)
        self.tools.setDisabled(boo)
        self.SCPICommandLine.setDisabled(boo)
        self.CreateNotePadAction.setDisabled(boo)
        self.FileTreeViewer.setDisabled(boo)
        self.graph.setDisabled(boo)
        self.table.setDisabled(boo)
        self.PumpQWidget.setDisabled(boo)
        self.CreatNewTableAction.setDisabled(boo)
        if not boo:
            self.setCentralWidget(self.mdi)

    def add_sub_win(self, obj):
        sub = QMdiSubWindow()
        sub.setWindowIcon(icon("new_project.png"))
        sub.setWidget(obj)
        self.mdi.addSubWindow(sub)
        sub.show()

    def file_opened(self, file):
        if file['file_type'] == '.txt':
            obj = NotePad()
            obj.note_open(file['file_path'], file['file_name'])
            self.add_sub_win(obj)
        elif file['file_type'] == '.py':
            obj = TextEditor()
            obj.procedure_open(file['file_path'], file['file_name'])
            self.add_sub_win(obj)

    def remote_trigger(self, s):
        print(self.remote)
        self.remote = s
        print(self.remote)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # dark_stylesheet = qdarkstyle.load_stylesheet_pyside2()
    # app.setStyle(dark_stylesheet)
    app.setStyle('Fusion')
    window = MainWindow()

    # qtmodern.styles.dark(app)
    # mw = qtmodern.windows.ModernWindow(window)
    # mw.show()
    window.show()
    app.exec_()