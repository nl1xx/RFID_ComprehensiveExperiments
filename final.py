import datetime
import json
import os
import serial
import time
from tkinter import simpledialog, messagebox
import tkinter as tk


ser = serial.Serial('COM3', 9600, timeout=1)


# 读卡(相当于一键读卡)
def read_rfid():
    while True:
        if ser.in_waiting > 0:
            data = ser.readline()
            if data:
                hex_data = data.hex().upper()
                formatted_hex_data = ' '.join(hex_data[i:i+2] for i in range(0, len(hex_data), 2))
                return formatted_hex_data  # 7F 09 10 00 04 00 22 4F AC 01 DD
        ser.flushInput()
        time.sleep(0.5)


# 获取卡号(ID)
def rfid_id(hex_data):
    return hex_data[-14:-2]  # 22 4F AC 01


class RFID:
    def __init__(self, serial, receive_buffer=bytearray(64), send_buffer=bytearray(64), keyA=bytearray(6), keyB=bytearray(6)):
        self.serial = serial
        self.receive_buffer = receive_buffer
        self.keyA = keyA
        self.keyB = keyB
        self.send_buffer = send_buffer
        self.block = [0] * 16
        self.head_flag = False

    # 校验和
    def check_sum(self, sendData, num):
        checksum = 0
        for i in range(num):
            checksum ^= sendData[i]
        return checksum

    # 发送数据
    def send(self, serial, data):
        SendData = []
        serial.write(bytes([0x7F]))
        SendData.append('0x7f')

        # 发送数据
        for byte in data:
            serial.write(bytes([byte]))
            formatted_byte = f'0x{byte:02x}'
            SendData.append(formatted_byte)
            # 数据中有0x7F多发送一个
            if byte == 0x7F:
                serial.write(bytes([0x7F]))
                SendData.append('0x7f')
        print("Send data: {}".format(SendData))

    # 读块数据
    def read_block_data_(self, block):
        length = 3
        self.send_buffer[0] = length
        self.send_buffer[1] = 0x06
        self.send_buffer[2] = block

        self.send_buffer[3] = self.check_sum(self.send_buffer, length)

        self.send(ser, self.send_buffer)

    # 写块数据
    def write_block_data_(self, block, data):
        length = 19
        blockDataBytes = []
        self.send_buffer[0] = length
        self.send_buffer[1] = 0x07
        self.send_buffer[2] = block

        for i in range(15, -1, -1):  # 从高位到低位提取
            byte = (data >> (i * 8)) & 0xFF  # 提取当前字节
            blockDataBytes.append(byte)
        for i in range(16):
            self.send_buffer[3 + i] = blockDataBytes[i]

        self.send_buffer[19] = self.check_sum(self.send_buffer, length)

        self.send(ser, self.send_buffer)

    # 一件读卡
    def read_card(self):
        length = 2
        self.send_buffer[0] = 2
        self.send_buffer[1] = 0x10
        self.send_buffer[2] = self.check_sum(self.send_buffer, length)
        self.send(ser, self.send_buffer)

    # 一件办卡
    def open_card(self, block, value, keyA, keyB, initial_keyB):
        length = 25
        self.send_buffer = [0] * (length + 1)

        self.send_buffer[0] = length  # 数据长度
        self.send_buffer[1] = 0x11  # 固定命令字节
        self.send_buffer[2] = block  # 填充块地址

        # 填充4字节的value
        self.send_buffer[3] = (value >> 24) & 0xFF
        self.send_buffer[4] = (value >> 16) & 0xFF
        self.send_buffer[5] = (value >> 8) & 0xFF
        self.send_buffer[6] = value & 0xFF

        # keyA
        for i in range(6):
            self.send_buffer[7 + i] = keyA[i]

        # keyB
        for i in range(6):
            self.send_buffer[13 + i] = keyB[i]

        # initial_keyB
        for i in range(6):
            self.send_buffer[19 + i] = initial_keyB[i]

        self.send_buffer[25] = self.check_sum(self.send_buffer, length)

        self.send(ser, self.send_buffer)

    # 一键充值
    def recharge(self, block, keyB, money):
        length = 13
        self.send_buffer[0] = length
        self.send_buffer[1] = 0x12
        self.send_buffer[2] = block
        for i in range(6):
            self.send_buffer[3 + i] = keyB[i]

        self.send_buffer[9] = (money >> 24) & 0xFF
        self.send_buffer[10] = (money >> 16) & 0xFF
        self.send_buffer[11] = (money >> 8) & 0xFF
        self.send_buffer[12] = money & 0xFF

        self.send_buffer[13] = self.check_sum(self.send_buffer, length)

        self.send(ser, self.send_buffer)

    # 一键扣款
    def spend(self, block, keyA, money):
        length = 13
        self.send_buffer[0] = length
        self.send_buffer[1] = 0x13
        self.send_buffer[2] = block
        for i in range(6):
            self.send_buffer[3 + i] = keyA[i]

        self.send_buffer[9] = (money >> 24) & 0xFF
        self.send_buffer[10] = (money >> 16) & 0xFF
        self.send_buffer[11] = (money >> 8) & 0xFF
        self.send_buffer[12] = money & 0xFF

        self.send_buffer[13] = self.check_sum(self.send_buffer, length)

        self.send(ser, self.send_buffer)

    # 一键读块
    def read_block_data(self, block, keyA):
        length = 9
        # 设置前9个字节
        self.send_buffer[0] = length
        self.send_buffer[1] = 0x14
        self.send_buffer[2] = block
        for i in range(6):
            self.send_buffer[3 + i] = keyA[i]

        self.send_buffer[9] = self.check_sum(self.send_buffer, length)

        self.send(ser, self.send_buffer)

    # 一件写块
    def write_block_data(self, block, keyB, blockData):
        length = 25
        blockDataBytes = []

        for i in range(15, -1, -1):  # 从高位到低位提取
            byte = (blockData >> (i * 8)) & 0xFF  # 提取当前字节
            blockDataBytes.append(byte)

        self.send_buffer[0] = length
        self.send_buffer[1] = 0x15
        self.send_buffer[2] = block

        # 填充keyB (6字节)
        for i in range(6):
            self.send_buffer[3 + i] = keyB[i]

        # 填充blockData (16字节)
        for i in range(16):
            self.send_buffer[9 + i] = blockDataBytes[i]

        self.send_buffer[25] = self.check_sum(self.send_buffer, length)

        self.send(ser, self.send_buffer)

    # 接收数据
    def receive(self):
        # 检查串口是否有数据等待读取
        if self.serial.in_waiting > 0:
            # 读取数据
            data = self.serial.read(self.serial.in_waiting)
            hex_data = data.hex().upper()
            formatted_hex_data = ' '.join(hex_data[i:i + 2] for i in range(0, len(hex_data), 2))
            # 去掉命令头
            data_no_head = formatted_hex_data.split()[1:-1]
            # 去掉多余的0x7F
            new_data = []
            for i in range(len(data_no_head)):
                if i < len(data_no_head) - 1 and data_no_head[i] == "7F" and data_no_head[i + 1] == "7F":
                    # 如果当前位置和下一个位置都是0x7F，跳过下一个位置
                    continue
                new_data.append(data_no_head[i])
            processed_hex_data = ' '.join(new_data)
            print(f"Received data: {processed_hex_data}")
            return processed_hex_data
        else:
            return None

    def send_command(self, block, value, keyA, keyB, initial_keyB, blockData):
        commands = {
            0x01: "停止卡",
            0x02: "寻卡",
            0x03: "防冲撞",
            0x04: "选择卡",
            0x05: "验证密钥",
            0x06: "读数据块",
            0x07: "写数据块",
            0x08: "加值",
            0x09: "减值",
            0x0A: "扣款钱包",
            0x0B: "存储",
            0x0C: "读钱包",
            0x10: "一键读卡",
            0x11: "办卡",
            0x12: "充值",
            0x13: "扣款",
            0x14: "一键读块",
            0x15: "一键写块",
            0x16: "一键改密",
            0x17: "一键改值",
            0xA0: "读机器码",
            0xAA: "写机器码",
            0xAB: "设置自动读卡"
        }

        if commands == "0x06":
            self.read_block_data_(block)
        elif commands == "0x07":
            self.write_block_data_(block, value)
        elif commands == "0x10":
            self.read_card()
        elif commands == "0x11":
            self.open_card(block, value, keyA, keyB, initial_keyB)
        elif commands == "0x12":
            self.recharge(block, keyB, value)
        elif commands == "0x13":
            self.spend(block,keyA, value)
        elif commands == "0x14":
            self.read_block_data(block, keyA)
        elif commands == "0x15":
            self.write_block_data(block, keyB, blockData)

    # 实现签到系统(一键写块)
    def write_student_info(self, block, keyB, student_info):
        length = 25
        self.send_buffer[0] = length
        self.send_buffer[1] = 0x15
        self.send_buffer[2] = block

        # 将学生信息编码为字节，并确保不超过16个字节
        student_info_bytes = student_info.encode('utf-8')[:16]

        # 如果学生信息不足16个字节，则用\x00填充
        student_info_bytes += b'\x00' * (16 - len(student_info_bytes))

        # 填充send_buffer的块数据部分
        for i in range(16):
            self.send_buffer[3 + i] = student_info_bytes[i]

        # 填充keyB (6字节)
        for i in range(6):
            self.send_buffer[19 + i] = keyB[i]

        self.send_buffer[25] = self.check_sum(self.send_buffer, length)

        self.send(ser, self.send_buffer)
        # self.receive()

# 测试
def test():
    rfid = RFID(ser)
    keyA = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
    keyB = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
    blockdata = 0x11111111100000000000000000111111
    print("一键读卡")
    rfid.read_card()
    rfid.receive()  # 09 10 00 04 00 29 52 C4 1F
    time.sleep(1)
    print("-----" * 20)
    print("一键写块")
    block = 0x01
    rfid.write_block_data(block, keyB, blockdata)
    rfid.receive()
    time.sleep(1)
    print("-----" * 20)
    print("一键读块")
    rfid.read_block_data(block, keyA)
    rfid.receive()
    time.sleep(1)
    print("-----" * 20)
    rfid.receive()
test()


class CheckinSystem:
    def init_json(self):
        students_file = 'students.json'
        attendance_file = 'attendance.json'

        if not os.path.exists(students_file):
            with open(students_file, 'w') as f:
                json.dump([], f)

        if not os.path.exists(attendance_file):
            with open(attendance_file, 'w') as f:
                json.dump([], f)

    def __init__(self, root):
        self.init_json()
        self.root = root
        self.root.title("RFID 签到系统")
        self.root.geometry("400x300")

        self.label = tk.Label(root, text="签到系统")
        self.label.pack(pady=20)

        self.read_button = tk.Button(root, text="开卡", command=self.open_card)
        self.read_button.pack(pady=10)

        self.read_button = tk.Button(root, text="签到", command=self.check_in)
        self.read_button.pack(pady=10)

        self.query_button = tk.Button(root, text="查询签到信息", command=self.find_attendance)
        self.query_button.pack(pady=10)

        self.student_button = tk.Button(root, text="查询学生信息", command=self.find_student)
        self.student_button.pack(pady=10)

        self.exit_button = tk.Button(root, text="退出系统", command=root.quit)
        self.exit_button.pack(pady=10)

    # 添加学生
    def add_student(self, student_id, name, class_id, card_id, class_name):
        students_file = 'students.json'
        with open(students_file, 'r+') as f:
            try:
                students = json.load(f)
            except json.JSONDecodeError:
                students = []
            students.append({
                'student_id': student_id,
                'name': name,
                'class_id': class_id,
                'card_id': card_id,
                'class_name': class_name
            })

            f.seek(0)
            json.dump(students, f, indent=4)
            f.truncate()

    # 获取学生信息
    def get_students_info(self, card_id):
        students_file = 'students.json'
        with open(students_file, 'r') as f:
            students = json.load(f)
            for student in students:
                if student['card_id'] == card_id:
                    return student
        return None

    # 记录签到信息
    def record_attendance(self, student_id):
        attendance_file = 'attendance.json'
        with open(attendance_file, 'r+') as f:
            try:
                attendance = json.load(f)
            except json.JSONDecodeError:
                attendance = []

            attendance.append({
                'student_id': student_id,
                'attendance_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            f.seek(0)
            json.dump(attendance, f, indent=4)
            f.truncate()

    def get_attendance(self, student_id, class_id, date):
        attendance_file = 'attendance.json'
        with open(attendance_file, 'r') as f:
            attendance_records = json.load(f)
            filtered_records = []
            for record in attendance_records:
                if (student_id and record['student_id'] != student_id) or \
                        (class_id and record['student_id'] not in [s['student_id'] for s in
                                                                   json.load(open('students.json', 'r')) if
                                                                   s['class_id'] == class_id]) or \
                        (date and datetime.datetime.strptime(record['attendance_time'],
                                                             "%Y-%m-%d %H:%M:%S").date() != datetime.datetime.strptime(
                            date, "%Y-%m-%d").date()):
                    continue
                filtered_records.append(record)
            return filtered_records

    def open_card(self):
        card = read_rfid()
        card_id = rfid_id(card)

        # 检查是否已经存在该卡号
        existing_student = self.get_students_info(card_id)
        if existing_student:
            messagebox.showinfo("提示", f"卡号已绑定！\n学生姓名：{existing_student['name']}\n"
                                        f"学号：{existing_student['student_id']}\n班级：{existing_student['class_name']}")
            return

        # 输入学生信息
        student_id = simpledialog.askstring("开卡", "请输入学生学号")
        name = simpledialog.askstring("开卡", "请输入学生姓名")
        major = simpledialog.askstring("开卡", "请输入专业")
        class_num = simpledialog.askstring("开卡", "请输入班级")

        # 开卡
        if student_id and name and major and class_num and card_id:
            block = 0x01
            keyB = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
            student_info = f"{student_id}_{name}"

            rfid = RFID(ser)
            rfid.write_student_info(block, keyB, student_info)

            self.add_student(student_id, name, class_num, card_id, major)
            messagebox.showinfo("成功", "开卡成功")
        else:
            messagebox.showerror("错误", "请完整填写学生信息")

    def check_in(self):
        rfid = RFID(ser)
        # 一键读卡
        rfid.read_card()
        message = rfid.receive()
        print(message)
        card_id = message[-11:] + " "

        if card_id:
            student = self.get_students_info(card_id)
            if student:
                self.record_attendance(student['student_id'])
                messagebox.showinfo("签到成功", f"姓名：{student['name']}\n班级：{student['class_name']}\n学号：{student['student_id']}")
            else:
                messagebox.showinfo("请开卡", "暂无该学生信息")
                self.open_card()
        else:
            messagebox.showerror("错误", "未检测到RFID卡")

    def find_attendance(self):
        student_id = simpledialog.askstring("查询", "学号(可选)：")
        class_id = simpledialog.askstring("查询", "班级(可选)：")
        date = simpledialog.askstring("查询", "日期(可选 格式YYYY-MM-DD)：")
        records = self.get_attendance(student_id, class_id, date)
        if records:
            records_text = "\n".join([f"学号：{r['student_id']}, 签到时间：{r['attendance_time']}" for r in records])
            messagebox.showinfo("签到记录", records_text)
        else:
            messagebox.showinfo("查询结果", "没有找到相关记录")

    def find_student(self):
        student_id = simpledialog.askstring("查询", "请输入学生学号(可选)：")
        name = simpledialog.askstring("查询", "请输入学生姓名(可选)：")

        students_file = 'students.json'
        with open(students_file, 'r') as f:
            students = json.load(f)

        filtered_students = []
        for student in students:
            if (not student_id or student['student_id'] == student_id) and \
                    (not name or student['name'] == name):
                filtered_students.append(student)

        # 显示学生信息
        if filtered_students:
            students_text = "\n".join(
                [f"学号：{s['student_id']}, 姓名：{s['name']}, 专业：{s['class_name']}, 卡号：{s['card_id']}" for s in
                 filtered_students])
            messagebox.showinfo("学生信息", students_text)
        else:
            messagebox.showinfo("查询结果", "没有找到相关学生信息")


if __name__ == '__main__':
    root = tk.Tk()
    system = CheckinSystem(root)
    root.geometry("600x400")
    root.mainloop()
