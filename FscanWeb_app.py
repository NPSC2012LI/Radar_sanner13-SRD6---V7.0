import webbrowser
from flask import Flask, jsonify, render_template
import Seria_data
import logging
from motorSerialPort import SerialPortManager
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import serial

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

web_app = Flask(__name__)
web_app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# 创建sensor串口收集器实例
# serial_ports = ['COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10', 'COM11', 'COM12', 'COM13']
serial_ports = ['COM5']
serial_data_list = []
all_ports_opened = True
serial_sport = {}
motor_port = []
# print("初始化串口")

for port in serial_ports:
    try:
        serial_data = Seria_data.SerialDataCollector(port, 115200)
        serial_data.set_serial_data_list(serial_data_list)
        if serial_data.ser is not None and serial_data.ser.is_open:
            logger.info(f"串口实列创建成功：{serial_data}")
            serial_data_list.append(serial_data)
            serial_sport[port] = serial_data  # 将串口名称和对象存入字典
            # logger.info(f"向serial_data_list列表中写入串口初始化实例：{serial_data_list}")
        else:
            logger.error(f"无法打开串口{port}")
    except Exception as e:
        logger.error(f"初始化串口{port}发生错误:{e}")

# 创建 SerialPortManager 实例
motor_serial_port_manager = SerialPortManager(port='COM14', baudrate=115200)
motor_serial_port_manager.open_serial()

shared_sensor_data = []  # 共享的数据结构来存储传感器数据

# 定义常量
DATA_TO_SEND_1 = b'\x31'
DATA_TO_SEND_0 = b'\x30'
DATA_HEX_1 = DATA_TO_SEND_1.hex()
DATA_HEX_0 = DATA_TO_SEND_0.hex()

# 配置参数，指定要监控的串口
# selected_ports = ['COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10', 'COM11', 'COM12', 'COM13']
selected_ports = ['COM5']


def sent_start(target_port, data_to_send, data_hex):
    if target_port not in serial_sport:
        logger.error(f"目标串口 {target_port} 不存在")
        return

    serial_data = serial_sport[target_port]
    try:
        if serial_data.initialized and serial_data.ser.is_open:
            serial_data.write(data_to_send)  # 发送数据
            logger.info(f"Sent {data_hex} to serial port {target_port}.")
        else:
            logger.error(f"Failed to send {data_hex} to serial port {target_port}: Port is not initialized or not open.")
    except (serial.SerialException, OSError) as e:
        logger.error(f"Failed to send {data_hex} to serial port {target_port}: {str(e)}")


def initialize_and_send_data(target_ports):
    with ThreadPoolExecutor() as executor:
        futures = []
        for target_port in target_ports:
            # 发送 b'\x30'
            futures.append(executor.submit(sent_start, target_port, DATA_TO_SEND_0, DATA_HEX_0))
            # 等待1秒
            time.sleep(1)
            # 发送 b'\x31'
            futures.append(executor.submit(sent_start, target_port, DATA_TO_SEND_1, DATA_HEX_1))
            # 等待2秒
            # time.sleep(2)

        # 等待所有任务完成
        for future in futures:
            future.result()

        # time.sleep(1)
        # sent_start(target_port, DATA_TO_SEND_1, DATA_HEX_1)  # 发送 b'\x31'


# 显式调用 initialize_and_send_data 函数在应用启动后
initialize_and_send_data(serial_ports)

# 定义自动追踪全局变量auto_tracking、message_queue
auto_tracking = False


def poll_serial_ports():
    global auto_tracking, shared_sensor_data
    internal_lock = threading.Lock()

    while True:
        new_sensor_data = []
        start_time = time.time()  # 记录开始时间
        all_ports_have_data = False
        ports_with_data = set()  # 用于记录有数据的串口号

        # 尝试获取所有串口的数据
        while not all_ports_have_data and time.time() - start_time < 20:
            all_ports_have_data = True
            for port_name, serial_instance in serial_sport.items():
                try:
                    if serial_instance.initialized and serial_instance.ser.is_open:
                        data = serial_instance.get_data()  # get_data 方法用于读取数据
                        if data:
                            override_temperature = None  # 根据需要设置覆盖温度
                            processed_data = Seria_data.process_sensor_data(data, override_temperature, motor_serial_port_manager)
                            # logger.info(f"processed_data:{processed_data}")
                            # 确保每个传感器的数据是唯一的
                            for data_item in processed_data:
                                if data_item not in new_sensor_data:
                                    new_sensor_data.append(data_item)
                            ports_with_data.add(port_name)  # 记录有数据的串口号
                            # 打印具体串口获取的数据
                            if port_name in selected_ports:
                                for data_item in processed_data:
                                    logger.info(f"串口 {port_name} 获取的数据: 传感器编号 {data_item['sensor_id']}, 距离 {data_item['distance']}")
                        else:
                            all_ports_have_data = False
                    else:
                        logger.error(f"串口 {port_name} 未初始化或未打开")
                        all_ports_have_data = False
                except Exception as exc:
                    logger.error(f"读取串口 {port_name} 数据时发生错误: {exc}")
                    all_ports_have_data = False

            # 短暂休眠，减少CPU占用
            time.sleep(0.1)

        # 更新共享数据结构
        with internal_lock:
            shared_sensor_data = new_sensor_data

        # 输出有数据的串口号
        if ports_with_data:
            logger.info(f"有数据的串口: {', '.join(ports_with_data)}")
        else:
            logger.info("没有串口有数据")

        # 休眠2秒后再次轮询，以确保每次轮询时所有传感器的数据都被完整读取
        time.sleep(2)


# 创建锁以确保线程安全
lock = threading.Lock()
# 启动后台线程来轮询串口数据
polling_thread = threading.Thread(target=poll_serial_ports, daemon=True)
polling_thread.start()


@web_app.route('/get_serial_ports')
def get_serial_ports():
    return jsonify(serial_ports)


@web_app.route('/send_motor/<com_port>/<data>', methods=['GET'])
def send_motor_data(com_port, data):
    def handle_motor_data(com_port, data):
        with web_app.app_context():
            try:
                if not motor_serial_port_manager.initialized:
                    result = {"status": "error", "message": f"Failed to open serial port {com_port}."}
                    logger.error(result)
                    return jsonify({"status": "error", "message": f"Failed to open serial port {com_port}."}), 400
                else:
                    motor_serial_port_manager.motor_write(data)  # 发送数据
                    rotation_angle = motor_serial_port_manager.read_motor_data()
                    result = {"status": "success", "message": f"Sent: {data}, Received rotation angle: {rotation_angle}"}

                    return jsonify(result), 200
            except Exception as e:
                logger.error(f'An error occurred: {str(e)}')
                result = {"status": "error", "message": str(e)}
                return jsonify(result), 500

    # 使用线程处理串口操作，避免阻塞
    thread = threading.Thread(target=handle_motor_data, args=(com_port, data))
    thread.start()
    return jsonify({"status": "processing", "message": "Request is being processed in the background."}), 202


@web_app.route('/send/<com_port>/<data>')
def send_data(com_port, data):
    if com_port not in serial_sport:
        return jsonify({"status": "error", "message": "Invalid COM port"}), 400
    ser = serial_sport[com_port]
    if not ser.initialized or not ser.ser.is_open:
        return jsonify({"status": "error", "message": "Serial port is not initialized or not open."}), 500

    try:
        # 尝试将数据转换为字节
        data_bytes = bytes.fromhex(data)
        bytes_written = ser.write(data_bytes)
        if bytes_written is not None and bytes_written > 0:
            return jsonify({"status": "success", "data": f"{data} sent to {com_port}"})
        else:
            return jsonify({"status": "error", "message": "Failed to write to serial port."}), 500
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid hex data."}), 400
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return jsonify({"status": "error", "message": "An error occurred while sending data."}), 500


@web_app.route('/data')
def get_sensor_data():
    global shared_sensor_data
    if not shared_sensor_data:
        logger.error('shared_sensor_data为空')
        return jsonify([])

    # 去重处理，确保 sensor_id 唯一
    unique_sensor_data = {item['sensor_id']: item for item in shared_sensor_data}.values()

    # 返回共享的数据
    sorted_sensor_data = sorted(unique_sensor_data, key=lambda x: x['distance'])

    # filtered_sensor_data = [data for data in sorted_sensor_data if 20 <= data['distance'] <= 40]
    # filtered_sensor_data = [data for data in sorted_sensor_data if 2 <= data['distance'] <= 20]
    filtered_sensor_data = [data for data in sorted_sensor_data if 2 <= data['distance'] <= 200]
    final_sensor_data = filtered_sensor_data[:81]
    logger.info(f"即将转换的json数据：length:{len(final_sensor_data)}|{final_sensor_data}")
    return jsonify(final_sensor_data)


@web_app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    # main()
    webbrowser.open("http://127.0.0.1:5000")
    try:
        web_app.run(debug=False, threaded=True)
        logger.info("Flask服务已经启动")
    except Exception as e:
        logger.error("启动Flask应用失败：{0}".format(e))
