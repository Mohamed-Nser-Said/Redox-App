import socket
import threading
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QMainWindow, QMessageBox
from serial.tools import list_ports as ports
from enum import Enum
from modbus import ModbusBuilder
import serial
import time
from abc import ABC, abstractmethod


class RemoteManger:
    def __init__(self):
        self.ip_addr = socket.gethostbyname(socket.gethostname())
        self.port = 5051
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.server.bind((self.ip_addr, self.port))
        self.server.settimeout(2)

        self.connection = False
        self.current_state = 'Ready'

        self.conn, self.addr = None, None

    def server_listen(self):
        self.server.listen()
        try:
            self.conn, self.addr = self.server.accept()
            self.connection = True
            self.current_state = f'Connected with IP:{self.addr}'
        except socket.timeout:
            self.current_state = f'[No connection] Time out 2 second'
            self.connection = None

    def data_send(self, msg):
        self.conn.send(msg.encode('utf-8'))
        thread = threading.Thread(target=self.data_receiver)
        if self.connection:
            return thread.start()

    def data_receiver(self):
        msg = self.conn.recv(2048)
        return msg

    def close_connection(self):
        if self.conn is not None:
            self.connection = False
            self.current_state = f'Connection is Closed'
            self.data_send("end")
            self.conn.close()
            self.conn = None

            print('closed')

    def get_ports_list(self):
        self.conn.send('get_ports_list'.encode('utf-8'))
        # self.close_connection
        a = self.conn.recv(2048).decode('utf-8')
        return eval(a)

    def error_message(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()


class ErrorMassage(QMainWindow):
    """error handler for general use """

    def __init__(self, title, message):
        super().__init__()
        self.title = title
        self.message = message
        self.setWindowIcon(QIcon('icons/warning.png'))
        QMessageBox.warning(self, self.title, self.message)


class PumpMode(Enum):
    COUPLED = 0
    DECOUPLED = 1


class Pump(Enum):
    MASTER = 1
    SECOND = 2
    BOTH = 0


class PortManger:
    """
    this is port manger to check how many pumps are connected and return the specific port for each pump
    """

    def __init__(self, remote=False, s="USB-SERIAL CH340"):
        if not remote:
            self.__port = [str(i) for i in ports.comports(include_links=False)]
            self.__s = s
        elif remote:
            pass

    @property
    def get_ports_list(self):
        return self.__port

    @property
    def get_all_pump_ports_list(self):
        return [self.get_master_pump_port, self.get_second_pump_port]

    @property
    def get_master_pump_port(self):
        for _ in self.__port:
            if self.__s in _:
                return _[_.find("(") + 1:-1]
        return None

    @property
    def get_master_pump_port_name_raw(self):
        for _ in self.__port:
            if self.__s in _:
                return _
        return None

    def get_second_pump_port_name_raw(self):
        p = []
        for _ in self.__port:
            if self.__s in _:
                p.append(_)
            if len(p) > 1:
                return p[2]
        return None

    @property
    def get_number_of_pump_connected(self):
        num = []
        for _ in self.__port:
            if self.__s in _:
                num.append(_)
        return len(num)

    @property
    def get_second_pump_port(self):
        num = []
        for _ in self.__port:
            if self.__s in _:
                num.append(_)
        if len(num) > 1:
            return num[1][num[1].find("(") + 1:-1]
        return None


class PumpAbstract(ABC):

    @abstractmethod
    def send_pump(self):
        pass


class PumpModbusCommandSender(PumpAbstract):
    """
    this class manage the connection of the Pumps though the usb Ports, send the message
    with update connection method
    """

    def send_pump(self, data, send_to):
        if self._update_connection():
            try:
                self._write_s(send_to, data)

            except Exception as e:
                self.error_message(e)

    def _write_s(self, port, data):
        self.serial = serial.Serial(baudrate=9600, timeout=0.005, bytesize=8, stopbits=2,
                                    parity=serial.PARITY_NONE)
        self.serial.port = port
        self.serial.open()
        # with self.serial as s:
        #     s.write(data)
        self.serial.write(data)
        time.sleep(0.012)
        self.serial.close()

    def _update_connection(self):
        if PortManger().get_number_of_pump_connected > 1:
            return True
        else:
            self.error_message("No pump was found, please check you connections")
            return False

    @staticmethod
    def error_message(s):
        ErrorMassage('Error', s)


def find_my_pump(send_to):
    m = ModbusBuilder()
    p = PumpModbusCommandSender()
    start_ = m.build_start().get_modbus
    stop_ = m.build_stop().get_modbus
    speed_ = m.build_change_speed(30).get_modbus
    p.send_pump(data=speed_, send_to=send_to)
    time.sleep(0.1)
    p.send_pump(data=start_, send_to=send_to)
    time.sleep(0.2)
    p.send_pump(data=stop_, send_to=send_to)
    time.sleep(0.1)
    p.send_pump(data=start_, send_to=send_to)
    time.sleep(0.2)
    p.send_pump(data=stop_, send_to=send_to)


def step_increase(start, stop, steps, duration, send_to):
    m = ModbusBuilder()
    p = PumpModbusCommandSender()
    start_ = m.build_start().get_modbus
    stop_ = m.build_stop().get_modbus
    stop_ = m.build_stop().get_modbus
    p.send_pump(data=start_, send_to=send_to)
    speed_ = m.build_change_speed(start).get_modbus
    time.sleep(0.012)
    if abs(steps) != steps or abs(stop) != stop \
            or abs(start) != start or abs(duration) != duration:
        steps = abs(steps)
        stop = abs(stop)
        start = abs(start)
        duration = abs(duration)

    if start > stop:
        stop = stop - 1
        steps = - steps
    elif start < stop:
        stop = stop + 1
    for i in range(start, stop, steps):
        speed_ = m.build_change_speed(i).get_modbus
        p.send_pump(data=speed_, send_to=send_to)
        time.sleep(duration)


if __name__ == "__main__":
    m = ModbusBuilder()
    #
    # start_ = m.build_start().get_modbus
    # stop_ = m.build_stop().get_modbus
    # speed_ = m.build_change_speed(30).get_modbus
    #
    # # time.sleep(0.2)
    # p = PumpModbusCommandSender()
    # p.send_pump(data=stop_, send_to=Pump.MASTER)

    # p.send_pump(data=s,send_to=Pump.MASTER)
    # time.sleep(0.2)
    # p.send_pump(data=stop_, send_to=Pump.MASTER)
    # step_increase(5, 24, 5, 1, Pump.BOTH)
    # s = RemoteManger()
    # s.server_listen()
    # s.get_ports_list()
