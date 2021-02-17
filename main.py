from io import StringIO
from random import randint
import threading
import h5py
from PySide2.QtCore import QSize, Qt, QAbstractTableModel, Signal, QTimer, QRunnable, Slot, QThreadPool
from PySide2.QtGui import QIcon, QKeySequence, QFont, QSyntaxHighlighter, QTextCharFormat, QPixmap, QImage, QPalette, \
    QColor
from PySide2.QtWebEngineWidgets import QWebEngineView
from PySide2.QtWidgets import QApplication, QMainWindow, QStatusBar, QToolBar, QFileDialog, QTabWidget, QTextEdit, \
    QAction, QVBoxLayout, QScrollArea, QColorDialog, QListWidget, QAbstractItemView, QListWidgetItem
from PySide2.QtWidgets import QLabel, QLineEdit, QGridLayout, QHBoxLayout, QGroupBox, QComboBox, QWidget, QPlainTextEdit
from PySide2.QtWidgets import QMdiArea, QMdiSubWindow, QDockWidget, QTableView, QSizePolicy, QMessageBox, QPushButton
from control_api import PumpMode, Pump, PumpModbusCommandSender, ModbusBuilder, RemoteManger, PortManger
from widgets_builder import NewProjectSetNameDialog, NewTableDialog, ErrorMassage, Label, FileTreeViewer, \
    CreateNewGraphDialog
from widgets_builder import PumpAbstract, icon, special_characters_detector, StepIncreaseWindow, OpenProjectDialog
import numpy as np
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


class GraphMaker(QMainWindow):
    def __init__(self, title="no title"):
        super().__init__()

        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)

        self.graphWidget.setBackground("w")
        self.graphWidget.setTitle(title, color="0000", size="10pt")

        self.graphWidget.addLegend()
        self.graphWidget.showGrid(x=True, y=True)

    def plot(self, x_data, y_data, plot_name='no name', color='b', x_axis_name="X Axis",  y_axis_name="Y Axis", size=3):
        styles = {"color": "0000", "font-size": "20px"}
        self.graphWidget.setLabel("left", y_axis_name, **styles)
        self.graphWidget.setLabel("bottom", x_axis_name, **styles)
        pen = pg.mkPen(color=color, width=size)
        self.graphWidget.plot(x_data, y_data, name=plot_name, pen=pen)


class NewGraphAction(QAction):

    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.setText("New Figure")
        self.setStatusTip("Create New Figure")
        self.setIcon(icon("line-graph.png"))
        self.database = None
        self.color = None
        self.CreateNewGraphDialog = None
        self.triggered.connect(self.new_triggered)

    def create_graph(self):
        x_data = self.CreateNewGraphDialog.x_dataset_list_QComboBox.currentText()
        y_data = self.CreateNewGraphDialog.y_dataset_list_QComboBox.currentText()
        title = self.CreateNewGraphDialog.title_QLineEdit.text()
        plot_name = self.CreateNewGraphDialog.plot_name_QLineEdit.text()
        x_name = self.CreateNewGraphDialog.x_axis_name_QLineEdit.text()
        y_name = self.CreateNewGraphDialog.y_axis_name_QLineEdit.text()
        size = self.CreateNewGraphDialog.size_QComboBox.value()
        if x_data is not None and y_data is not None:
            x_data = self.database.get_one_data_set(x_data)
            y_data = self.database.get_one_data_set(y_data)
            graph = GraphMaker(title)
            graph.plot(x_data=x_data, y_data=y_data,color=self.color, plot_name=plot_name, x_axis_name=x_name,
                       y_axis_name=y_name, size=size)
            self.parent().add_sub_win(graph)

        self.CreateNewGraphDialog.parent().hide()

    def new_triggered(self):
        self.CreateNewGraphDialog = CreateNewGraphDialog()
        self.CreateNewGraphDialog.select_color_QPushButton.clicked.connect(self.color_dialog)
        self.database = DataBase(self.parent().project_name)
        self.CreateNewGraphDialog.x_dataset_list_QComboBox.addItems(self.database.get_list_data_set())
        self.CreateNewGraphDialog.y_dataset_list_QComboBox.addItems(self.database.get_list_data_set())
        self.parent().add_sub_win(self.CreateNewGraphDialog)
        self.CreateNewGraphDialog.save_QPushButton.clicked.connect(self.create_graph)
        self.CreateNewGraphDialog.cancel_QPushButton.clicked.connect(self.CreateNewGraphDialog.parent().hide)

    def color_dialog(self):
        self.color =  QColorDialog.getColor()


class MonitorWidget(QMainWindow):
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


class GraphViewer(QMainWindow):
    def __init__(self, path):
        super().__init__()
        self.image_QLabel = QLabel()
        self.image_QLabel.setScaledContents(True)

        self.image = QImage(path)
        self.pixmap = QPixmap(self.image)
        self.image_QLabel.setPixmap(self.pixmap.scaled(self.size(), Qt.IgnoreAspectRatio))
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.image_QLabel)

        zoom_in_QPushButton = QAction(self, "zoom in +", icon=icon('zoom_in.png'))
        zoom_in_QPushButton.triggered.connect(self.zoom_in)

        zoom_out_QPushButton = QAction(self, "zoom out -", icon=icon('zoom_out.png'))
        zoom_out_QPushButton.triggered.connect(self.zoom_out)

        toolbar = QToolBar()
        toolbar.addAction(zoom_in_QPushButton)
        toolbar.addAction(zoom_out_QPushButton)
        toolbar.setMovable(False)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)

        self.setCentralWidget(self.scrollArea)

        self.scaleFactor = 1.0
        self.zoom_out()
        self.zoom_out()

    def zoom_in(self):
        self.scale_image(1.25)

    def zoom_out(self,):
        self.scale_image(0.8)

    def scale_image(self, factor):
        self.scaleFactor *= factor
        self.image_QLabel.resize(self.scaleFactor * self.image_QLabel.pixmap().size())

        self.adjust_scrollBar(self.scrollArea.horizontalScrollBar(), factor)
        self.adjust_scrollBar(self.scrollArea.verticalScrollBar(), factor)

    @staticmethod
    def adjust_scrollBar(scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value() + ((factor - 1) * scrollBar.pageStep() / 2)))


class OpenGraphAction(QAction):

    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.setText("Open Figure")
        self.setStatusTip("Open Figure")
        self.setIcon(icon("line-graph.png"))

        self.triggered.connect(self.open_figure)

    def open_figure(self):
        path = os.path.join(os.getcwd(), MAIN_PROJECTS_SAVED_FILE, self.parent().project_name,
                            SUB_MAIN_PROJECTS_SAVED_FILE[1])
        print(path)
        path, _ = QFileDialog.getOpenFileName(None, "Open file", dir=path)

        if path:
            self.parent().add_sub_win(GraphViewer(path))


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
stop = ModbusBuilder.build_stop()\n

p = PumpModbusCommandSender()\n
p.send_pump(data=stop, send_to='COM3')"""
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

        key_list_1 = ["Return", 'type', 'Parameter', '__init__()', 'False', 'None', 'True', 'and', 'as', 'break', 'class',
                      'continue', 'float', 'def', 'elif', 'else', 'except', 'finally', 'for', 'from',
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
            # Note: self._data[index.row()][index.column()] will also work
            value = self._data[index.column(), index.row()]
            return str(value)

    def rowCount(self, index):
        return self._data.shape[1]

    def columnCount(self, index):
        return self._data.shape[0]


class TableViewer(QMainWindow):
    def __init__(self, data=np.array([])):
        super().__init__()

        self.table = QTableView()

        self.model = TableModel(data)
        self.table.setModel(self.model)
        self.setCentralWidget(self.table)


class CreatNewTableAction(QAction):
    NewTableCreatedSignal = Signal(dict)

    def __init__(self, parent):
        super().__init__()
        self.setText("New Table")
        self.setStatusTip("Creat a New Table")
        self.setIcon(icon("new_table"))
        self.NewTableDialog = None
        self.triggered.connect(self.show_table_dialog)
        self.setParent(parent)
        self.database = None
        self.data_list = np.array([])

    def create_new_table(self):
        table_name = self.NewTableDialog.table_name_QLineEdit.text()

        for i in range(self.NewTableDialog.dataset_QListWidget.count()):
            if self.NewTableDialog.dataset_QListWidget.item(i).checkState() == Qt.Checked:
                data = self.database.get_one_data_set(self.NewTableDialog.dataset_QListWidget.item(i).text())
                self.data_list.append(data)

        self.data_list = np.array(self.data_list)
        if special_characters_detector(table_name):
            return

        self.parent().add_sub_win(TableViewer(data=self.data_list))
        # self.NewTableCreatedSignal.emit({"table_name": table_name})
        self.NewTableDialog.hide()

    def show_table_dialog(self):
        self.data_list = []
        self.NewTableDialog = NewTableDialog()
        self.NewTableDialog.cancel_QPushButton.clicked.connect(self.NewTableDialog.close)
        self.NewTableDialog.save_QPushButton.clicked.connect(self.create_new_table)

        self.database = DataBase(self.parent().project_name)
        self.NewTableDialog.add_list(self.database.get_list_data_set())
        self.NewTableDialog.show()


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
        # self.historyQPlainTextEdit.setStyleSheet("color: blue;")
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
        # self.pyvisaQLineEdit.setStyleSheet("color: red;")
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


class DataBase:
    def __init__(self, project_name):
        self.main_file = os.path.join(os.getcwd(), MAIN_PROJECTS_SAVED_FILE, project_name,
                                      SUB_MAIN_PROJECTS_SAVED_FILE[0], f"{project_name}.h5")

    def create_new_hdf5_file(self):
        with h5py.File(self.main_file, "a") as t:
            pass
        self.create_new_data_set(name='time stamp', data=np.arange(0, 100))

        self.create_new_data_set('voltage_data')
        self.create_new_data_set('current_data')
        self.create_new_data_set('x_data')
        self.create_new_data_set('data2')
        self.create_new_data_set('data3', data=np.arange(300, 400)/100)


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
    def create_new_data_set(self, name, data=np.array(np.random.random(100))):
        try:
            with h5py.File(self.main_file, "a") as f:
                f.create_dataset(name=name, data=data)
        except Exception as e:
            return ErrorMassage("Error", str(e))

    def get_list_data_set(self):
        with h5py.File(self.main_file, "a") as f:
            return list(f.keys().__iter__())

    def get_one_data_set(self, name):
        with h5py.File(self.main_file, "a") as f:
            return f.get(name)[:]


class MonitorAction(QAction):
    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.setText("Monitor")
        self.setStatusTip("open monitor")
        self.setIcon(icon("line-graph.png"))

        self.triggered.connect(self.clicked)

    def clicked(self):
        self.parent().add_sub_win(MonitorWidget())


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
            dark(app)
        else:
            light(app)


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


class RemoteControlPanel(QMainWindow):
    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.RemoteManger = self.parent().RemoteManger

        self.ip_QLabel = QLabel("Host IP Address")
        self.RemoteManger_ip_addr_QLineEdit = QLineEdit(self.RemoteManger.ip_addr)
        self.RemoteManger_ip_addr_QLineEdit.setReadOnly(True)

        self.port_QLabel = QLabel("Port")
        self.RemoteManger_port_QLineEdit = QLineEdit(str(self.RemoteManger.port))
        self.RemoteManger_port_QLineEdit.setReadOnly(True)

        self.state_QLabel = QLabel("State")
        self.RemoteManger_state_QLineEdit = QLabel(self.RemoteManger.current_state)
        # self.RemoteManger_state_QLineEdit.setReadOnly(True)

        self.server_listen_QPushButton = QPushButton('listing')
        self.server_listen_QPushButton.clicked.connect(self.listing)

        self.server_close_QPushButton = QPushButton('close')
        self.server_close_QPushButton.clicked.connect(self.close_connection)

        layout = QGridLayout()
        layout.addWidget(self.ip_QLabel, 0, 0)
        layout.addWidget(self.RemoteManger_ip_addr_QLineEdit, 0, 1)
        layout.addWidget(self.port_QLabel, 1, 0)
        layout.addWidget(self.RemoteManger_port_QLineEdit, 1, 1)
        layout.addWidget(self.RemoteManger_state_QLineEdit, 2, 1)
        layout.addWidget(self.state_QLabel, 2, 0)
        layout.addWidget(self.server_listen_QPushButton, 3, 0)
        layout.addWidget(self.server_close_QPushButton, 4, 0)

        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)

    def listing(self):
        self.RemoteManger.server_listen()
        self.RemoteManger_state_QLineEdit.setText(self.RemoteManger.current_state)

    def close_connection(self):
        self.RemoteManger.close_connection()
        self.RemoteManger_state_QLineEdit.setText(self.RemoteManger.current_state)


class PumpQWidget(QWidget):
    PumpSignalSend = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.remote_conn = False
        self.connection_mode_QLabel = QLabel("Pump Connection Mode")
        self.connection_mode_QComboBox = QComboBox()
        self.connection_mode_QComboBox.addItems(["USB-direct", "Remote"])
        self.connection_mode_QComboBox.setDisabled(True)
        self.connection_mode_QComboBox.currentTextChanged.connect(self.remote_conn_changed)

        # self.PumpModbusCommandSender = PumpModbusCommandSender()
        self.pump_mode_state = PumpMode.COUPLED
        group_box_pump_mode = QGroupBox("Mode")
        self.mode_QLabel = QLabel("Pump Mode")
        self.mode_QComboBox = QComboBox()
        self.mode_QComboBox.addItems(["coupled", "decoupled"])
        self.mode_QComboBox.currentTextChanged.connect(self.pump_mode_changed)
        layout_pump_mode = QGridLayout()

        layout_pump_mode.addWidget(self.connection_mode_QLabel, 0, 0)
        layout_pump_mode.addWidget(self.connection_mode_QComboBox, 0, 1)

        layout_pump_mode.addWidget(self.mode_QLabel, 1, 0)
        layout_pump_mode.addWidget(self.mode_QComboBox, 1, 1)
        group_box_pump_mode.setLayout(layout_pump_mode)

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

    def remote_conn_changed(self):
        usb_ports = PortManger().get_ports_list
        self.pump1.pump_port_selection_QComboBox.clear()
        self.pump2.pump_port_selection_QComboBox.clear()
        if self.connection_mode_QComboBox.currentText() == "Remote":
            s = self.parent().parent().RemoteManger
            if s is not None:
                try:
                    self.pump1.pump_port_selection_QComboBox.addItems(s.get_ports_list())
                    self.pump2.pump_port_selection_QComboBox.addItems(s.get_ports_list())

                except Exception as e:
                    ErrorMassage("Error", "These is no connection, or the connection is lost")

        elif self.connection_mode_QComboBox.currentText() == "USB-direct":
            self.pump1.pump_port_selection_QComboBox.addItems(usb_ports)
            self.pump2.pump_port_selection_QComboBox.addItems(usb_ports)


class HelpAction(QAction):
    def __init__(self, parent):
        super().__init__()
        self.setText("Help")
        self.setParent(parent)
        self.setStatusTip("Need Help")
        self.triggered.connect(self.clicked)
        self.setShortcut(QKeySequence("Ctrl+h"))

    def clicked(self):
        self.parent().add_sub_win(HelpDialog())


class HelpDialog(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setWindowTitle("Help")
        self.setWindowIcon(icon("help.png"))
        self.layout = QGridLayout()

        self.help_QTextEdit = QTextEdit('Select Topic')
        f = self.font()
        f.setFamily('courier new')
        f.setPointSize(12)
        self.help_QTextEdit.setFont(f)

        self.help_QTextEdit.setReadOnly(True)
        Highlighter(self.help_QTextEdit.document())

        self.help_QListWidget = QListWidget()
        self.help_QListWidget.setMaximumWidth(200)
        self.help_QListWidget.setAcceptDrops(False)
        self.help_QListWidget.doubleClicked.connect(self.topic)
        self.help_QListWidget.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)

        self.ok_QPushButton = QPushButton("Ok")
        self.ok_QPushButton.clicked.connect(self.hide)
        self.layout.addWidget(self.help_QTextEdit, 1, 1)
        self.layout.addWidget(self.help_QListWidget, 1, 0)
        self.layout.addWidget(self.ok_QPushButton, 3, 0)

        w = QWidget()
        w.setLayout(self.layout)
        self.setCentralWidget(w)

        self.add_list()

    def add_list(self, items=None):

        if items is None:
            items = ['ModbusBuilder', 'PumpModbusCommandSender', 'PortManger']
        for i, j in enumerate(items):
            l = QListWidgetItem(j)
            self.help_QListWidget.insertItem(i + 1, l)

    def topic(self, s):
        text_0 = """
This class is used as ModBus Message builder


class modbus. ModbusBuilder
    __init__()
    build_start ()
        build start ModBus message

    build_stop ()
        build stop ModBus message

    build_flow_direction (direction="cw")
        build start ModBus
        Parameter: direction(str) : flow direction, “cw”, “ccw’

    build_change_speed (new_speed=0)
        Parameter: direction(float) : pump speed in rpm, 
        build speed ModBus message

get_modbus
    Getter (property):	Get the modbus last built.
    Return type:	str"""
        text_1 = """This class is used as to send ModBus message though usb port


class control_api. PumpModbusCommandSender
    __init__()
    send_pump (data, send_to)
    send a specific message to a specified port
        Parameter: data(bytearrey):contian the message
                    send_to(str) : port, Ex[COM1, COM4] 

    Return type:	None"""
        text_2 = """This class is used to mange ports 

class control_api. PortManger
        __init__(remote=False, s="USB-SERIAL CH340")
        get_ports_list
            Getter (property):	Get all Port list.
            Return type:	list

        get_all_pump_ports_list
            Getter (property):	Get only pumps Port list.
            Return type:	list

        get_number_of_pump_connected
            Getter (property):	Get number of pumps connected.
            Return type:	int"""

        if s.row() == 0:
            self.help_QTextEdit.setText(text_0)
        elif s.row() == 1:
            self.help_QTextEdit.setText(text_1)
        elif s.row() == 2:
            self.help_QTextEdit.setText(text_2)

    def sizeHint(self):
        return QSize(400, 500)


class AboutAction(QAction):
    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.setText("About")
        self.triggered.connect(self.clicked)

    def clicked(self):
        browser = QWebEngineView()
        browser.setUrl('https://github.com/Mohamed-Nser-Said/RDF_project')
        self.parent().add_sub_win(browser)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.remote = False
        self.project_name = None
        self.RemoteManger = None

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
        self.help_action = HelpAction(self)
        self.about_action = AboutAction(self)
        self.monitor = MonitorAction(self)

        self.dark_mode_action = DarkModeAction()
        self.NewProjectAction = NewProjectAction(self)
        self.OpenProjectAction = OpenProjectAction(self)
        self.CreatNewTableAction = CreatNewTableAction(self)
        self.CreateNotePadAction = CreateNotePadAction(self)
        self.NewTextEditorAction = NewTextEditorAction(self)
        self.StepFunctionAction = StepFunctionAction(self)
        self.OpenGraphAction = OpenGraphAction(self)
        self.RemoteAction = RemoteAction(self)
        self.NewGraphAction = NewGraphAction(self)

        # signals and slots
        self.CreateNotePadAction.CreateNewNoteClicked.connect(self.add_sub_win)
        self.FileTreeViewer.FileOpenedSignal.connect(self.file_opened)
        self.NewProjectAction.NewProjectAddedSignal.connect(self.project_manger)
        self.OpenProjectAction.OpenProjectActionClickedSignal.connect(self.project_manger)
        self.PumpQWidget.PumpSignalSend.connect(lambda _: print(_))
        self.RemoteAction.triggered.connect(self.remote_activated)
        # self.RemoteAction.triggered.connect(self.remote_trigger)

        # self.CreatNewTableAction.NewTableCreatedSignal.connect(self.NewProjectTab.append_new_tabel)

        # Toolbar and menu bar
        self.menu = self.menuBar()
        self.file = self.menu.addMenu("File")
        self.file.addAction(self.NewProjectAction)
        self.file.addAction(self.OpenProjectAction)

        self.tools = self.menu.addMenu("Tools")
        self.tools.addAction(self.CreateNotePadAction)
        self.tools.addAction(self.StepFunctionAction)
        self.tools.addAction(self.NewTextEditorAction)
        self.tools.addAction(self.monitor)

        self.view = self.menu.addMenu("View")
        self.appearance = self.view.addMenu("Appearance")
        self.appearance.addAction(self.dark_mode_action)

        self.table = self.menu.addMenu("Tables")
        self.table.addAction(self.CreatNewTableAction)

        self.graph = self.menu.addMenu("Graph")
        self.graph.addAction(self.NewGraphAction)
        self.graph.addAction(self.OpenGraphAction)

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

    def project_manger(self, name):
        self.set_disable_enable_widgets(False)
        self.project_name = name
        self.setWindowTitle(f"RedoX App 2.1 [{name}]")
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

        elif file['file_type'] == '.png':
            obj = GraphViewer(file['file_path'])
            self.add_sub_win(obj)

    def remote_activated(self):
        if self.RemoteManger is None:
            try:
                self.RemoteManger = RemoteManger()

            except Exception as e:
                self.error_message(str(e))

        if self.RemoteManger is not None:
            self.add_sub_win(RemoteControlPanel(self))
            self.PumpQWidget.connection_mode_QComboBox.setDisabled(False)

    def error_message(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()


def dark(app):
    """ Apply Dark Theme to the Qt application instance.

        Args:
            app (QApplication): QApplication instance.
    """

    darkPalette = QPalette()

    # base
    darkPalette.setColor(QPalette.WindowText, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Button, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.Light, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Midlight, QColor(90, 90, 90))

    darkPalette.setColor(QPalette.Dark, QColor(35, 35, 35))
    darkPalette.setColor(QPalette.Text, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.BrightText, QColor(180, 180, 180))

    darkPalette.setColor(QPalette.ButtonText, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Base, QColor(42, 42, 42))
    darkPalette.setColor(QPalette.Window, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))

    darkPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.HighlightedText, QColor(180, 180, 180))
    darkPalette.setColor(QPalette.Link, QColor(56, 252, 196))
    darkPalette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))

    darkPalette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ToolTipText, QColor(180, 180, 180))

    darkPalette.setColor(QPalette.PlaceholderText, QColor(0, 0, 0))

    # disabled
    darkPalette.setColor(QPalette.Disabled, QPalette.WindowText,
                         QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.Text,
                         QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.ButtonText,
                         QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Disabled, QPalette.Highlight,
                         QColor(80, 80, 80))
    darkPalette.setColor(QPalette.Disabled, QPalette.HighlightedText,
                         QColor(127, 127, 127))

    app.setPalette(darkPalette)


def light(app):
    """ Apply Light Theme to the Qt application instance.

        Args:
            app (QApplication): QApplication instance.
    """

    lightPalette = QPalette()

    # base
    lightPalette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.Button, QColor(240, 240, 240))
    lightPalette.setColor(QPalette.Light, QColor(180, 180, 180))
    lightPalette.setColor(QPalette.Midlight, QColor(200, 200, 200))

    lightPalette.setColor(QPalette.Dark, QColor(225, 225, 225))
    lightPalette.setColor(QPalette.Text, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.BrightText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.ButtonText, QColor(0, 0, 0))

    lightPalette.setColor(QPalette.Base, QColor(237, 237, 237))
    lightPalette.setColor(QPalette.Window, QColor(240, 240, 240))
    lightPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))
    lightPalette.setColor(QPalette.Highlight, QColor(76, 163, 224))

    lightPalette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.Link, QColor(0, 162, 232))
    lightPalette.setColor(QPalette.AlternateBase, QColor(225, 225, 225))
    lightPalette.setColor(QPalette.ToolTipBase, QColor(240, 240, 240))

    lightPalette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    # lightPalette.setColor(QPalette., QColor(0, 0, 0))

    lightPalette.setColor(QPalette.PlaceholderText, QColor(240, 240, 240))

    lightPalette.setColor(QPalette.Disabled, QPalette.WindowText,
                          QColor(115, 115, 115))
    lightPalette.setColor(QPalette.Disabled, QPalette.Text,
                          QColor(115, 115, 115))
    lightPalette.setColor(QPalette.Disabled, QPalette.ButtonText,
                          QColor(115, 115, 115))
    lightPalette.setColor(QPalette.Disabled, QPalette.Highlight,
                          QColor(190, 190, 190))
    lightPalette.setColor(QPalette.Disabled, QPalette.HighlightedText,
                          QColor(115, 115, 115))

    app.setPalette(lightPalette)


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
