# Redox Flow Battery Control GUI


![](https://github.com/Mohamed-Nser-Said/RFB_control_sys/blob/master/main_simple_ui/icons/manimage.png)

  > ### This project provides simple control GUI used to control Redox Flow Battery cell with some analytic tools.

---

### Table of Contents
* Description
* Start
* required packages
* Hardware
* GUI


---
* ## Description 

   This is the source code for the [`redox flow battery`](https://en.wikipedia.org/wiki/Flow_battery) control `GUI`,
  the `GUI` is built using the python version of `Qt5`  [**`pyside2`**](https://doc.qt.io/qtforpython/index.html), 
  the system consists of the `cell itself`, `Shenchen Peristaltic Pump` and Keithley Instruments Model 2450 ,
  HDF5 files was used for data storage.
---
* ## Start
    Download the repository, run the `main` python file which contains the main GUI.
---
* ## Packages


Package                           | Version
----------------------------------| -------------------
conda                             | 4.9.2
h5py                              | 2.10.0
matplotlib                        | 3.3.2
numpy                             | 1.19.2
pandas                            | 1.1.3
PyQt5                             | 5.15.2
pyqtgraph                         | 0.11.0
pyserial                          | 3.5
PySide2                           | 5.15.2
qtmodern                          | 0.2.0
ViTables                          | 3.0.2

---
* ## Hardware
  * ### Shenchen Peristaltic Pump
  <img src="https://www.good-pump.com/uploadfile/load/images/2020/202004/20200407/15/20200407103434z1kzlgic.jpg" alt="gui" width="300"/>
  
  MODBUS-RTU standard communication is used to control the pump, message frame as below：
  
  |Slave address | Function code | Data area         | CRC Check (Cyclic Redundancy Check)   |
  |--------------|---------------|-------------------|---------------------------------------|
  |1 Byte        | 1 Byte        | or up to 252 bytes|     2 Bytes                           |
  |              |               |                   |  CRC low       CRC high               |
  
  **`CRC check`**: CRC code is 2 bytes, 16 check codes. Use CRC-16(which used in American binary
synchronous system).

    `Polynomial: G(X)=X16+X15+X2+1`.
---
  * ### Keithley Instruments Model 2450
    <img src="https://www.distrelec.de/Web/WebShopImages/landscape_large/95/80/keithley-2450.jpg" alt="gui" width="300"/>
    
    this instrument used for charging/discharging and a variety of measurements, data will be stored in an HDF5 file for
    other usage, the instrument uses `SCPI` standard as a syntax, some functionality has its own `GUI`, other commands can be
    accessed via `SCPI command line`.
    
    `$ pip install -U pyvisa`
    
    [for more information](https://pyvisa.readthedocs.io/en/latest/introduction/getting.html)
    

    
        
  
---
  * ### NI6001
     the National Instruments USB-6001/6002/6003 data acquisition '(DAQ) devices'. The NI-DAQmx Python where used,
    nidaqmx can be installed with pip:
    
    `$ python -m pip install nidaqmx`
     
    [for more information](https://nidaqmx-python.readthedocs.io/en/latest/)

---

  * ### GUI
    the GUI was built using PySide2 module which is `Qt` for Python,
    
    get `PySide2` via pip by running:
    `pip install PySide2`.
    
    [for more information](https://wiki.qt.io/Qt_for_Python)
    
    
# **Main Dashboard** 
 <img src="https://github.com/Mohamed-Nser-Said/RDF_project/blob/main/icons/new_des.jpg?raw=true" alt="gui" width="700"/>



  

    
    
    
    
 




---
   


