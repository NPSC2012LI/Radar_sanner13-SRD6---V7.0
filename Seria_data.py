import logging
import serial
import threading
import queue
import time
import math
import motorSerialPort
# 添加日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SerialDataCollector:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.data_queue = queue.Queue()
        self.running = False
        self.logger = logging.getLogger(__name__)
        self._stop_event = threading.Event()
        self.ser = None
        self.initialized = False
        self.serial_data = []
        self.serial_data_list = []
        if self.ser is None or not self.ser.is_open:
            if self.initialize_serial(1):  # 尝试打开串口1次
                self.initialized = True
                self.logger.info(f"串口{port} 已打开")
                self.start()  # 如果串口打开成功，启动数据读取子线程
            else:
                self.logger.error(f"无法顺利打开串口{port}")
        else:
            self.logger.info(f"串口{self.port} 已经打开，跳过初始化")

    def initialize_serial(self, max_attempts):
        if self.ser is not None and self.ser.is_open:
            self.logger.info(f"串口{self.port} 已经打开，跳过初始化")
            return True  # 如果串口已经打开，直接返回True

        for attempt in range(max_attempts):
            try:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                return True
                
            except serial.SerialException as e:
                self.logger.error(f"尝试 {attempt + 1} 次无法打开串口 {self.port}: {e}")
                time.sleep(1)
        self.logger.error(f"无法打开串口 {self.port}, 将跳过此串口")
        return False

    def ensure_serial_open(self):
        if self.ser is None or not self.ser.is_open:
            self.logger.info(f"尝试重新打开串口 {self.port}")
            if self.initialize_serial(1):
                self.start()
            else:
                self.logger.error(f"无法重新打开串口 {self.port}")

    def read_data(self):
        if self.ser is None:
            self.logger.error("串口未初始化或已停止，无法读取数据")
            return
        self.logger.info("开始读取串口数据")
        buffer = []
        # sensor_id_list = ['1', '10', '19', '28', '37', '46', '55', '64', '73']
        sensor_id_list = ['1']
        valid_start = False
        while not self._stop_event.is_set():
            try:
                # 使用超时读取，避免阻塞
                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8').strip()
                    if not valid_start:
                        # 判断读取的数据是否在列表中
                        if data in sensor_id_list:
                            valid_start = True
                            self.logger.info(f'找到有效起始数据：{data}')
                            buffer.append(data)  # 存入有效起始数据
                            continue  # 跳过当前循环，避免重复存入
                        else:
                            self.logger.info(f"无效数据，跳过：{data}")
                            continue
                    # 如果找到了有效起始数据，则正常读取
                    buffer.append(data)
                    if len(buffer) >= 180:
                        # self.logger.info(f"buffer长度达到20，调用ensure_unique_and_insert方法，{self.port} buffer内容：{buffer}")
                        self.ensure_unique_and_insert(buffer)
                        buffer = []
                        valid_start = False  # 重置标志便于下一次查找
                        # logger.info(f"read方法将数据插入队列后，buffer值：{buffer}")
                else:
                    # 添加短暂的睡眠时间，避免CPU占用过高
                    time.sleep(0.01)
            except UnicodeDecodeError:
                self.logger.error("解码错误，跳过无效数据")
            except serial.SerialException as e:
                self.logger.error(f"串口错误：{e}")
                self.handle_error()
            except Exception as e:
                self.logger.error(f"读取串口数据时发生异常：{e}")
                self.handle_error()

    def handle_error(self):
        """处理串口错误，尝试重新打开串口"""
        if self.ser is not None:
            self.ser.close()
            self.ser = None
        self.logger.error("handle尝试重新打开串口")
        time.sleep(1)  # 等待一段时间再重试
        if self.initialize_serial(1):  # 尝试重新初始化串口
            self.start()
        else:
            self.logger.error("handle无法重新打开串口，将停止读取数据")
            self.running = False  # 如果初始化失败，停止读取数据

    def start(self):
        """启动数据读取子线程"""
        if not self.initialized or self.running:
            self.logger.info("串口未初始化或数据读取子线程已在运行，跳过启动")
            return
        self.running = True
        self.thread = threading.Thread(target=self.read_data)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("启动数据读取子线程")

    def write(self, data):
        """
        Write data to the serial port
        """
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("Can only send str, bytes or bytearray types")
        if self.ser is not None and self.ser.is_open:
            bytes_written = self.ser.write(data)
            if bytes_written > 0:
                self.logger.info(f"Wrote {bytes_written} bytes to {self.port}.")
                return bytes_written
            else:
                self.logger.error(f"Failed to write to {self.port}.")
                return None
        else:
            self.logger.error(f"Serial port {self.port} is not open.")
            return None

    def set_serial_data_list(self, serial_data_list):
        self.serial_data_list = serial_data_list

    def stop(self):
        """停止数据读取线程"""
        self._stop_event.set()
        if self.thread is not None:
            self.thread.join()
        self.ser.close()
        self.initialized = False  # 关闭串口时，重置initialized标志

    def ensure_unique_and_insert(self, buffer):
        """确保数据唯一性并插入队列"""
        # self.logger.info("开始执行ensure_unique_and_insert方法")
        try:
            # 直接将数据放入队列，不进行存在性检查
            self.data_queue.put(buffer)  # 使用 put 方法添加数据
            # self.logger.info(f"插入从串口获取新原始数据到队列：{buffer}")
        except Exception as e:
            self.logger.error(f"ensure_unique_and_insert方法执行发生异常：{e}", exc_info=True)
        # finally:
        #     self.logger.info("ensure_unique_and_insert方法执行完毕")

    def get_data(self):
        self.ensure_serial_open()
        """从队列中获取所有数据并处理①取出队列中所有数据"""
        all_sensor_data = []
        while not self.data_queue.empty():
            try:
                data = self.data_queue.get(timeout=1)
                # logger.info(f"从队列中获取原始数据: {data}")
                all_sensor_data.extend(data)
                if len(all_sensor_data) == 180:
                    # logger.info(f"打印组装后的all_sensor_data数据: {all_sensor_data}")
                    self.serial_data = all_sensor_data
                    break
            except queue.Empty:
                break
        if not all_sensor_data:
            return []
            # all_sensor_data = self.serial_data  # 缓存上一次正确数据
        return all_sensor_data

    def __del__(self):
        if self.ser is not None:
            self.ser.close()


# 计算距离
def calculate_distance(sensor_value, average_temperature):
    # 在自由空间传播测距R=1/2*c*t
    # 距离=T*c/2 (c声速、T脉宽时间)、声速温度公式:c=(331.45+0.61t/℃)m*s-1(其中 330.45 是在 0℃、20℃声速:342.62M/S、40℃声速:354.85M/S)
    R = ((1/2) * ((331.45+0.61*average_temperature)-1) * (sensor_value * (1E-6)))*100  # *100单位由m调整为cm
    return R


# 计算角度
def calculate_angle(sensor_id, rotation_angle):
    # 圆心距为50mm，9行9列分布，所以每个传感器之间的水平和垂直距离是50mm
    cell_size = 50

    # 传感器编号对应的行列号
    # 传感器编号从1开始，我们需要将其转换为从0开始的索引
    row = (sensor_id - 1) // 9
    col = (sensor_id - 1) % 9
    # col = 8 - ((sensor_id - 1) % 9)  # 调整列索引以适应从右往左的编号
    # 以编号41的圆心为坐标原点(0, 0)
    # 计算相对于原点的坐标
    x = cell_size * (col - 4)
    y = cell_size * (row - 4)  # Y轴向上为正方向，所以这里不取负值
    # 旋转传感器平面
    # 将旋转角度从度转换为弧度
    rotation_radians = math.radians(rotation_angle)

    # 旋转后的坐标
    x_rotated = x * math.cos(rotation_radians) - y * math.sin(rotation_radians)
    y_rotated = x * math.sin(rotation_radians) + y * math.cos(rotation_radians)

    # 计算夹角，结果为弧度，转换为度
    if x_rotated == 0 and y_rotated == 0:
        angle_degrees = 0  # 传感器41位于原点，角度为0°
    else:
        angle_radians = math.atan2(-y_rotated, x_rotated)  # 使用负值定义角度计算以逆时针为方向，发之为顺时针
        angle_degrees = math.degrees(angle_radians)

        # 确保角度在0°到360°之间
        if angle_degrees < 0:
            angle_degrees += 360

    return angle_degrees


# 示例：获取传感器编号1和传感器编号81的角度
# sensor_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 41, 45, 81, 61, 62, 63, 64, 65, 66, 67, 68, 69]
# angles = {sensor_id: calculate_angle(sensor_id, rotation_angle=0) for sensor_id in sensor_ids}
# for sensor_id, (angle) in angles.items():
#     print(f"Sensor {sensor_id}: Angle = {angle:.2f}°")


def test_calculate_angle_no_rotation():
    sensor_id = 42  # 中心传感器
    rotation_angle = 0
    expected_angle = 0  # 由于没有旋转，角度应为0°
    calculated_angle = calculate_angle(sensor_id, rotation_angle)
    assert calculated_angle == expected_angle, f"Expected {expected_angle}, but got {calculated_angle}"


test_calculate_angle_no_rotation()
print("Test passed!")


# 处理传感器数据
def process_sensor_data(all_sensor_data, override_temperature=None, motor_serial_port_manager=None):
    total_temperature = 0
    temperature_count = 0
    average_temperature = 0
    results = []

    # 获取温度值，假设它们分布在下标为 18, 38, 58, ..., 168 的位置
    for temp_index in range(18, 180, 20):
        if len(all_sensor_data) > temp_index and all_sensor_data[temp_index].isdigit():
            temperature_value = int(all_sensor_data[temp_index])
            total_temperature += temperature_value
            temperature_count += 1  # 更新温度计数
            logger.info(f"提取温度值: {temperature_value} 位置: {temp_index}")

    if temperature_count > 0:
        average_temperature = total_temperature / temperature_count
        logger.info(f"auto_average_temperature: {average_temperature}")
    else:
        logger.error('温度数据格式不正确')
        return results

    # 如果有覆盖温度值，则使用覆盖温度值
    if override_temperature is not None:
        average_temperature = override_temperature
        logger.info(f'change_temperature:{average_temperature}')

    # 检查数据列表长度是否为180
    if len(all_sensor_data) != 180:
        logger.error(f"数据不完整，必须是180个数据点,all_sensor_data:{all_sensor_data}")
        return results

    # 只处理前180个数据，跳过温度值的位置
    for i in range(0, 180, 2):
        if (i + 1) % 20 == 0:
            continue
        if i in range(18, 180, 20):
            logger.info(f"跳过温度值位置: {i}")
            continue

        sensor_id = int(all_sensor_data[i])
        sensor_value = int(all_sensor_data[i + 1])

        # 当 sensor_value 为 6666 或 8888 时跳过这个数据
        # if sensor_value in [0, 6666, 8888, 26666, 28888]:
        #     continue

        # 计算距离
        distance = calculate_distance(sensor_value, average_temperature if temperature_count else 20)

        # 计算角度
        try:
            if motor_serial_port_manager is not None and motor_serial_port_manager.ser.is_open:
                rotation_angle = motor_serial_port_manager.read_motor_data()
            else:
                rotation_angle = 0  # 如果没有提供 motor_serial_port_manager 或 串口未打开，则默认为0
        except AttributeError:
            rotation_angle = 0

        angle = calculate_angle(sensor_id, rotation_angle)

        # 逻辑判断：如果distance>500cm,元素不加入results
        if distance > 500:
            logger.info(f"跳过距离大于500cm的数据: sensor_id={sensor_id}, distance={distance}")
            continue

        # 逻辑判断：(0,0)元素不加入results
        if distance == 0 and angle == 0:
            logger.info(f"跳过距离和角度为0的数据: sensor_id={sensor_id}, distance={distance}, angle={angle}")
            continue

        results.append({'sensor_id': sensor_id, 'distance': distance, 'angle': angle})
        logger.info(f"添加数据: {sensor_id}, {distance}, {angle}")

    return results




#
# print(f'6666转化实际距离为:{calculate_distance(6666, 20)}')
# print(f'8888转化实际距离为:{calculate_distance(8888, 20)}')
# print(f'1500转化实际距离为:{calculate_distance(1550, 20)}')

