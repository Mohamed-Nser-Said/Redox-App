from PySide2.QtCore import QSize, Qt, QAbstractTableModel, Signal, QTimer
from PySide2.QtGui import QIcon, QKeySequence
from PySide2.QtWidgets import QAction, QApplication, QMainWindow, QStatusBar, QToolBar, QFileDialog, QTabWidget
from PySide2.QtWidgets import QLabel, QLineEdit, QGridLayout, QHBoxLayout, QGroupBox, QComboBox, QWidget
from PySide2.QtWidgets import QMdiArea, QMdiSubWindow, QDockWidget, QTableView, QSizePolicy
from control_api import PumpMode, Pump, PumpModbusCommandSender
from widgets_builder import NewProjectSetNameDialog, SetNewTableDialog, ErrorMassage, Label, FileTreeViewer
from widgets_builder import PumpAbstract, icon, special_characters_detector
import numpy as np
import qtmodern.windows
# import tables as tb
import os
import sys
from random import randint
import pyqtgraph as pg
from pyqtgraph import PlotWidget, plot



MAIN_PROJECTS_SAVED_FILE = "saved_projects"
SUB_MAIN_PROJECTS_SAVED_FILE = ["hsf5-data", 'graphs', 'reports', 'notes']

if not os.path.exists(MAIN_PROJECTS_SAVED_FILE):
    os.mkdir(MAIN_PROJECTS_SAVED_FILE)


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
            data=np.arange(0, 100).reshape(20, 5)

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


class AddFileTreeViewerAction(QAction):
    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.setText("Files")
        self.setStatusTip("Add File Tree")
        self.triggered.connect(self.clicked)
        self.setCheckable(True)
        self.setChecked(True)

    def clicked(self, s):
        if s:
            self.parent().FileTreeViewer.show()

        else:
            self.parent().FileTreeViewer.hide()


class PumpQWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.PumpModbusCommandSender = PumpModbusCommandSender()
        self.pump_mode_state = PumpMode.COUPLED
        group_box_pump_mode = QGroupBox("Mode")
        # group_box_pump_mode.setMaximumSize(150, 80)
        self.mode_QLabel = QLabel("Pump Mode")
        self.mode_QComboBox = QComboBox()
        self.mode_QComboBox.addItems(["coupled", "decoupled"])
        self.mode_QComboBox.currentTextChanged.connect(self.pump_mode_changed)
        h_layout_pump_mode = QHBoxLayout()
        h_layout_pump_mode.addWidget(self.mode_QLabel)
        h_layout_pump_mode.addWidget(self.mode_QComboBox)
        group_box_pump_mode.setLayout(h_layout_pump_mode)

        self.pump1 = PumpAbstract("Pump 1")
        self.pump1.pump_send_state_QPushButton.clicked.connect(lambda _: self.start_stop_pump(Pump.MASTER, _))
        self.pump2 = PumpAbstract("Pump 2")
        self.pump2.pump_send_state_QPushButton.clicked.connect(lambda _: self.start_stop_pump(Pump.SECOND, _))
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

    def start_stop_pump(self, pump, s):
        if self.pump_mode_state == PumpMode.COUPLED:
            pump = Pump.BOTH
        if s:
            self.PumpModbusCommandSender.send_pump(data=self.PumpModbusCommandSender.start, send_to=pump)
            if pump == Pump.MASTER:
                self.pump1.pump_send_state_QPushButton.setText("Stop")
            elif pump == Pump.SECOND:
                self.pump2.pump_send_state_QPushButton.setText("Stop")
        if not s:
            self.PumpModbusCommandSender.send_pump(data=self.PumpModbusCommandSender.stop, send_to=pump)
            if pump == Pump.MASTER:
                self.pump1.pump_send_state_QPushButton.setText("Start")
            elif pump == Pump.SECOND:
                self.pump2.pump_send_state_QPushButton.setText("Start")


class AddPumpQWidgetAction(QAction):
    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.setText("Pump Control")
        self.setStatusTip("Add Pump Control")
        self.triggered.connect(self.clicked)
        self.setCheckable(True)
        self.setChecked(True)

    def clicked(self, s):
        if s:
            self.parent().PumpQWidget.show()

        else:
            self.parent().PumpQWidget.hide()


class SCPICommandLine(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        f = self.font()
        f.setPointSize(14)
        f.setWeight(5)
        self.setFont(f)
        self.setText(">>  ")
        # self.setEnabled(False)
        # self.returnPressed.connect(self.pressed)

    def keyReleaseEvent(self, e):
        if e.key() == 16777220:
            self.pressed()

    def sizeHint(self):
        return QSize(1080, 100)

    def pressed(self):
        self.setText(">>  ")
        # print("enter")


class SCPICommandLineAction(QAction):
    def __init__(self, parent):
        super().__init__()
        self.setParent(parent)
        self.setText("SCPI Command Line")
        self.triggered.connect(self.clicked)
        self.setStatusTip("add SCPI Command Line")
        self.setCheckable(True)
        self.SCPICommandLine = SCPICommandLine()

    def clicked(self, s):
        self.parent().layout.addWidget(self.SCPICommandLine, 2, 0, 1, 3)
        if s:
            self.SCPICommandLine.show()

        elif not s:
            self.SCPICommandLine.hide()


class NewProjectTab(QTabWidget):
    NewProjectTabClosedSignal = Signal(int)

    def __init__(self):
        super().__init__()
        self.setDocumentMode(True)
        self.setTabsClosable(True)
        self.label = Label(text="you could add graph, table, or open already exist ones")

        self.currentChanged.connect(self.current_tab_changed)
        self.tabCloseRequested.connect(self.close_tab)

        # self.setCentralWidget(self.mdi)

    def close_tab(self, i):
        self.removeTab(i)
        # self.NewProjectTabClosedSignal.emit(self.count())
        # if self.count():
        # print(self.count())

    def add_new_tab(self, project_name="None"):
        mdi = QMdiArea()
        mdi.ViewMode(QMdiArea.TabbedView)

        i = self.addTab(mdi, project_name)
        self.setCurrentIndex(i)

    def append_new_tabel(self, table_info=None, data=None):
        mdi = self.currentWidget()
        sub1 = QMdiSubWindow()
        sub1.setWindowIcon(icon('new_table.png'))
        sub1.setWidget(TableViewer())
        mdi.addSubWindow(sub1)
        sub1.show()

        self.append_new_graph()

    def append_new_graph(self):
        mdi = self.currentWidget()
        sub1 = QMdiSubWindow()
        sub1.setWindowIcon(icon('new_table.png'))

        hour = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        temperature = [30, 32, 34, 32, 33, 31, 29, 32, 35, 45]

        graphWidget = pg.PlotWidget()
        graphWidget.plot(hour, temperature)

        sub1.setWidget(graphWidget)

        mdi.addSubWindow(sub1)
        sub1.show()

    def current_tab_changed(self, i):
        print(i)

    def update_title(self):
        self.tabs.currentWidget().page().title()


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


# class CreateNewGraphAction(QAction):
#     def __init__(self, parent):
#         super().__init__()
#         self.setParent(parent)
#         self.setText("New Graph")
#         self.setStatusTip("Creat a New Graph")
#         self.setIcon(icon("line-graph.png"))
#         # self.SetNewTableDialog = SetNewTableDialog()
#         # self.SetNewTableDialog.cancel_QPushButton.clicked.connect(self.SetNewTableDialog.close)
#         # self.SetNewTableDialog.save_QPushButton.clicked.connect(self.create_new_table)
#         # self.triggered.connect(self.show_table_dialog)
#         self.triggered.connect(self.create_new_graph)
#
#     def create_new_graph(self):
#           pass


class OpenTableAction(QAction):
    def __init__(self, parent):
        super().__init__()
        self.setText("Open Table")
        self.setIcon(icon("graph"))
        self.triggered.connect(self.clicked)
        self.setParent(parent)

    def clicked(self):
        pass


class DataBase:
    def __init__(self, project_name):
        self.main_file = os.path.join(os.getcwd(), MAIN_PROJECTS_SAVED_FILE, project_name,
                                      SUB_MAIN_PROJECTS_SAVED_FILE[0], f"{project_name}.h5")

    def create_new_hdf5_file(self):
        with tb.open_file(self.main_file, "a") as t:
            pass

    def create_new_table(self, table_name):

        class Description(tb.IsDescription):
            time_stamp = tb.Int32Col()
            pump_1_speed = tb.Float64Col()
            pump_2_speed = tb.Float64Col()
            voltage = tb.Float64Col()
            note = tb.StringCol(itemsize=5)

        try:
            with tb.open_file(self.main_file, "a") as t:
                a = t.create_table(t.root, table_name, Description)
                # a.append(image)

        except tb.exceptions.NodeError:
            return ErrorMassage("Name already exist", "this name is already exist\nplease try different name")

    def create_new_array(self, name, size=None, data=np.array([])):
        if name in self.get_all_table_name_list:
            return ErrorMassage("Name already exist", "this name is already exist\nplease try different name")

        else:
            try:
                with tb.open_file(self.main_file, "a") as f:
                    a = f.create_array(f.root, name, obj=data)
                    return a.read()
            except:
                return ErrorMassage("Error", "something went wrong try again")

    @property
    def get_all_table_name_list(self):
        with tb.open_file(self.main_file, "a")as t:
            table_name_list = list(t.root.__members__)
        return table_name_list


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


class ExitAction(QAction):
    def __init__(self):
        super(ExitAction, self).__init__()
        self.setText("Exit")
        self.setStatusTip("Exit from the App")
        self.triggered.connect(self.clicked)
        self.setShortcut(QKeySequence("Ctrl+e"))

    def clicked(self):
        quit()


class OpenAction(QAction):
    def __init__(self):
        super().__init__()
        self.setText("Open")

        self.setIcon(icon("open.png"))
        self.setStatusTip("open old project")
        self.triggered.connect(self.clicked)

    def clicked(self):
        # self.file = QFileDialog.getOpenFileName(self.parent(), "Open Project", os.path.join(os.getcwd(), "hdf_data"))
        # with tb.open_file(self.file[0], "a") as t:
        #     print(list(t.root.__members__))
        pass


class SaveAction(QAction):
    def __init__(self):
        super().__init__()
        self.setText("Save Project")
        self.setIcon(icon("save.png"))
        self.setStatusTip("save a new project")
        self.triggered.connect(self.clicked)
        self.setShortcut(QKeySequence("Ctrl+s"))

    def clicked(self):
        self.file = QFileDialog.getSaveFileName(self.parent(), "Save Project", "C:/Users/abuaisha93/Desktop/")
        file = open(self.file[0], "w")
        file.close()


class SettingAction(QAction):
    def __init__(self):
        super().__init__()
        self.setText("Settings")
        self.setIcon(icon("setting.png"))
        self.setStatusTip("setting")
        self.triggered.connect(self.clicked)
        self.setShortcut(QKeySequence("Ctrl+Alt+s"))
        # self.w = SettingWindow()

    def clicked(self):
        # self.w.show()
        print("setting")


class AnalyseAction(QAction):
    def __init__(self):
        super().__init__()
        self.setText("Analyse")
        self.triggered.connect(self.clicked)

    def clicked(self):
        print("Analysing")


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
            qtmodern.styles.dark(app)
        else:
            qtmodern.styles.light(app)


class NewRecordAction(QAction):
    def __init__(self):
        super().__init__()
        self.setText("Start Record")
        self.triggered.connect(self.clicked)
        self.setStatusTip("New Table")
        icon = QIcon(os.path.join("", "images", "add.png"))
        self.setIcon(QIcon(icon))

    def clicked(self, s):
        print("add")


class GetPDFReportAction(QAction):
    def __init__(self):
        super().__init__()
        self.setText("Generate PDF Report")
        self.setStatusTip("Get PDF report summary")
        self.triggered.connect(self.clicked)

    def clicked(self):
        print("report is loading")


class LaunchViTables(QAction):
    def __init__(self):
        super().__init__()
        self.setText("launch ViTables")
        self.setIcon(icon("setting.png"))
        self.setStatusTip("launch ViTables")
        self.triggered.connect(self.clicked)
        self.setShortcut(QKeySequence("Ctrl+Shift+l"))

    @staticmethod
    def clicked():
        from vitables.start import gui
        gui()


class CreateDockWindows(QDockWidget):
    def __init__(self, title="No title", parent=None, widget=None, area=None):
        super().__init__()
        self.setWindowTitle(title)
        self.setParent(parent)
        self.setAllowedAreas(area)
        self.setWidget(widget)


#
# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#
#         mdi = QMdiArea()
# 
#         self.graphWidget = pg.PlotWidget()
#         sub1 = QMdiSubWindow()
#         sub1.setWidget(self.graphWidget)
#         mdi.addSubWindow(sub1)
#         sub1.show()
#
#         self.x = list(range(100))  # 100 time points
#         self.y = [randint(0, 100) for _ in range(100)]  # 100 data points
#
#         self.graphWidget.setBackground("w")
#
#         pen = pg.mkPen(color=(255, 0, 0))
#         self.data_line = self.graphWidget.plot(self.x, self.y, pen=pen)  # <1>
#
#         self.timer = QTimer()
#         self.timer.setInterval(50)
#         self.timer.timeout.connect(self.update_plot_data)
#         self.timer.start()
#
#         self.setCentralWidget(mdi)

    def update_plot_data(self):

        self.x = self.x[1:]  # Remove the first y element.
        self.x.append(self.x[-1] + 1)  # Add a new value 1 higher than the last.

        self.y = self.y[1:]  # Remove the first
        self.y.append(randint(0, 100))  # Add a new random value.

        self.data_line.setData(self.x, self.y)  # Update the data.



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.add = False
        self.setDocumentMode(True)
        self.setWindowTitle("RedoX App 2.1")
        self.setWindowIcon(icon("app.png"))
        # self.setCentralWidget(Label(text="Creat New Project Ctrl+N"))

        self.layout = QGridLayout()
        self.label = Label(text="Create New Project Ctrl+N")
        # self.setCentralWidget(self.label)

        mdi = QMdiArea()
        self.setCentralWidget(mdi)
        sub1 = QMdiSubWindow()

        hour = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        temperature = [30, 32, 34, 32, 33, 31, 29, 32, 35, 45]
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.plot(hour, temperature)

        sub1.setWidget(self.graphWidget)
        # self.setCentralWidget(self.graphWidget)

        mdi.addSubWindow(sub1)
        sub1.show()
        #########################################

        # QDocks
        self.PumpQWidget = PumpQWidget()
        self.PumpQWidget_dock = CreateDockWindows(title="Pump control", parent=self, widget=self.PumpQWidget,
                                                  area=Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.FileTreeViewer = FileTreeViewer()
        self.FileTreeViewer_dock = CreateDockWindows(title="File Tree", parent=self, widget=self.FileTreeViewer,
                                                     area=Qt.LeftDockWidgetArea)

        self.SCPICommandLine = SCPICommandLine()
        self.SCPICommandLine_dock = CreateDockWindows(title="SCPI Command Line", parent=self,
                                                      widget=self.SCPICommandLine,
                                                      area=Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)

        self.addDockWidget(Qt.RightDockWidgetArea, self.PumpQWidget_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.FileTreeViewer_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.SCPICommandLine_dock)
        #
        # self.layout.addWidget(self.PumpQWidget, 0, 3, 1, 1)
        # self.layout.addWidget(self.FileTreeViewer, 0, 0, 2, 1)
        ########################################################????????
        # self.w = QWidget()
        # self.w.setLayout(self.layout)
        # self.setCentralWidget(self.w)

        ########################################################/>??????????

        # all actions
        self.NewProjectTab = NewProjectTab()
        self.exit_action = ExitAction()
        self.open_action = OpenAction()
        self.save_action = SaveAction()
        self.help_action = HelpAction()
        self.about_action = AboutAction()
        self.monitor = MonitorAction()
        self.analyse = AnalyseAction()
        self.get_pdf_report = GetPDFReportAction()
        self.setting = SettingAction()
        self.dark_mode_action = DarkModeAction()

        self.SCPICommandLineAction = SCPICommandLineAction(self)
        self.add_new_measurement = NewRecordAction()

        self.NewProjectAction = NewProjectAction(self)
        self.AddPumpQWidgetAction = AddPumpQWidgetAction(self)
        self.LaunchViTables = LaunchViTables()
        self.OpenTableAction = OpenTableAction(self)
        self.AddFileTreeViewerAction = AddFileTreeViewerAction(self)
        self.CreatNewTableAction = CreatNewTableAction(self)
        #####################

        self.NewProjectAction.NewProjectAddedSignal.connect(self.new_project_created)
        self.CreatNewTableAction.NewTableCreatedSignal.connect(self.NewProjectTab.append_new_tabel)
        #########################
        self.menu = self.menuBar()
        self.file = self.menu.addMenu("File")

        self.file.addAction(self.NewProjectAction)
        self.file.addAction(self.open_action)
        self.file.addAction(self.save_action)

        self.file.addSeparator()
        self.file.addAction(self.LaunchViTables)
        self.file.addSeparator()
        self.file.addAction(self.get_pdf_report)
        self.file.addSeparator()
        self.file.addAction(self.setting)
        self.file.addSeparator()
        self.file.addAction(self.exit_action)

        self.tools = self.menu.addMenu("Tools")
        self.tools.addAction(self.SCPICommandLineAction)
        self.tools.addAction(self.AddPumpQWidgetAction)
        self.tools.addAction(self.AddFileTreeViewerAction)
        self.tools.addAction(self.monitor)
        self.tools.addSeparator()
        self.tools.addAction(self.analyse)

        self.view = self.menu.addMenu("View")

        self.appearance = self.view.addMenu("Appearance")

        self.appearance.addAction(self.dark_mode_action)

        self.table = self.menu.addMenu("Tables")
        self.table.addAction(self.CreatNewTableAction)
        self.table.addAction(self.OpenTableAction)

        self.table = self.menu.addMenu("Graph")

        self.remote = self.menu.addMenu("Remote")

        self.help = self.menu.addMenu("Help")

        self.help.addAction(self.help_action)
        self.help.addAction(self.about_action)

        self.toolbar = QToolBar("main toolbar")
        self.toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(self.toolbar)

        self.toolbar.addAction(self.NewProjectAction)
        self.toolbar.addAction(self.open_action)
        self.toolbar.addAction(self.save_action)

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.dark_mode_action)
        self.toolbar.addSeparator()

        self.project_toolbar = QToolBar("project")
        # self.addToolBar(Qt.RightToolBarArea, self.project_toolbar)
        self.addToolBar(self.project_toolbar)
        self.project_toolbar.setIconSize(QSize(16, 16))
        self.project_toolbar.setMovable(False)

        self.project_toolbar.addAction(self.CreatNewTableAction)
        self.project_toolbar.addAction(self.OpenTableAction)

        self.setStatusBar(QStatusBar(self))

    def sizeHint(self):
        return QSize(1080, 650)

    def new_project_created(self, s):
        self.NewProjectTab.add_new_tab(s)

        if not self.add:
            # self.layout.addWidget(self.NewProjectTab, 0, 1, 2, 2)
            self.label.hide()
            self.setCentralWidget(self.NewProjectTab)
            self.add = True

    def test(self, a):
        print(a)


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
