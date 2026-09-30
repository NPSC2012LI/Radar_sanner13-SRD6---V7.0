import serial
import logging
import threading
import time


class SerialPortManager:
    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.initialized = False
        self.data_queue = []  # 缓存用于存储有效数据
        # self.last_rotation_angle = None  # 储存上一次有效的rotation_angle
        self.last_rotation_angle = 0  # 储存上一次有效的rotation_angle

    def open_serial(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate)
            self.initialized = True
            logging.info(f'motorPort:{self.port}')
            print(f"motorSerial port {self.port} opened successfully.")
        except Exception as e:
            print(f"motorFailed to open serial port {self.port}: {e}")
            self.initialized = False

    def read_motor_data(self):
        # 检查串口是否已初始化并且打开
        if not (self.initialized and self.ser.is_open):
            logging.error(f"串口 {self.port} motor serial未初始化或未打开")
            return 0  # 如果串口未初始化或未打开，立即返回0
        # time.sleep(1)
        if self.ser.in_waiting > 0:  # 确保在读取数据前清除可能存在的旧数据
            self.ser.reset_input_buffer()
        try:
            if self.ser.in_waiting > 0:  # 判断是否有数据
                data = self.ser.readline().decode('utf-8').strip()
                print(f'motor串口返回数据格式：{data}')
                # 判断起始数据
                if data == '100':
                    # 读取下一行数据
                    next_line = self.ser.readline().decode('utf-8').strip()
                    print(f'下一行数据：{next_line}')

                    self.data_queue.append(next_line)
                    # 取出缓存中的数据赋值给 rotation_angle
                    if self.data_queue:
                        rotation_angle = float(self.data_queue[0])
                        # 清空缓存，准备下一次读取
                        self.data_queue.clear()
                        print(f'测试发送电机数据是否成功')
                        return rotation_angle
        except Exception as e:
            logging.error(f"读取串口数据时发生错误: {e}")
        # 如果没有成功读取到数据或者发生了错误，则返回0
        return 0

    def motor_write(self, data):
        if self.ser.is_open:
            if isinstance(data, int):
                data = data.to_bytes(1, byteorder='big')
                print(f'motor方法按钮数据：{data}')
            elif isinstance(data, str):
                data = data.encode('utf-8')
                print(f'motor方法按钮数据str：{data}')

            # 发送数据
            bytes_sent = self.ser.write(data)
            if bytes_sent != len(data):
                logging.warning(f"Failed to send all data. Sent {bytes_sent} out of {len(data)} bytes.")
            else:
                logging.info(f"motor_button_Data sent successfully: {data.hex()}")
        else:
            raise IOError("Serial port is not open")

    def close_serial(self):
        if self.initialized and self.ser.is_open:
            self.ser.close()
            self.initialized = False
            print(f"Serial port {self.port} closed.")


# motor_serial = SerialPortManager(port='COM14', baudrate=115200)
# motor_serial.open_serial()
# motor_serial.motor_write('7')
# print(motor_serial.read_motor_data())