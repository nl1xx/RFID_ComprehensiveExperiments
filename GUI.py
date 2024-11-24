import datetime
import json
import os
import serial
import time
import tkinter as tk
from tkinter import messagebox, simpledialog


ser = serial.Serial('COM3', 9600, timeout=1)


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


def rfid_id(hex_data):
    return hex_data[-14:-2]  # 22 4F AC 01


def init_json():
    students_file = 'students.json'
    attendance_file = 'attendance.json'

    if not os.path.exists(students_file):
        with open(students_file, 'w') as f:
            json.dump([], f)

    if not os.path.exists(attendance_file):
        with open(attendance_file, 'w') as f:
            json.dump([], f)


# 开卡
def add_student(student_id, name, class_id, card_id, class_name):
    students_file = 'students.json'
    with open(students_file, 'r+') as f:
        students = json.load(f)
        students.append({
            'student_id': student_id,
            'name': name,
            'class_id': class_id,
            'card_id': card_id,
            'class_name': class_name
        })
        json.dump(students, f, indent=4)


# 记录签到信息
def record_attendance(student_id):
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


# 获取学生信息
def get_student_info(card_id):
    students_file = 'students.json'
    with open(students_file, 'r') as f:
        students = json.load(f)
        for student in students:
            if student['card_id'] == card_id:
                return student
    return None


# 查询签到信息
def query_attendance(student_id=None, class_id=None, date=None):
    attendance_file = 'attendance.json'
    with open(attendance_file, 'r') as f:
        attendance_records = json.load(f)
        filtered_records = []
        for record in attendance_records:
            if (student_id and record['student_id'] != student_id) or \
                    (class_id and record['student_id'] not in [s['student_id'] for s in json.load(open('students.json', 'r')) if s['class_id'] == class_id]) or \
                    (date and datetime.datetime.strptime(record['attendance_time'],  "%Y-%m-%d %H:%M:%S").date() != datetime.datetime.strptime(date, "%Y-%m-%d").date()):
                continue
            filtered_records.append(record)
        return filtered_records


# 查询学生
def query_student_info(student_id=None):
    students_file = 'students.json'
    with open(students_file, 'r') as f:
        students = json.load(f)
        if student_id:
            for student in students:
                if student['student_id'] == student_id:
                    return [student]
        return students


# GUI页面
class RFIDSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("RFID 签到系统")
        self.root.geometry("400x300")

        self.label = tk.Label(root, text="刷卡")
        self.label.pack(pady=20)

        self.read_button = tk.Button(root, text="签到", command=self.read_card)
        self.read_button.pack(pady=10)

        self.query_button = tk.Button(root, text="查询签到信息", command=self.query_attendance_records)
        self.query_button.pack(pady=10)

        self.student_button = tk.Button(root, text="查询学生信息", command=self.query_student_info)
        self.student_button.pack(pady=10)

        self.exit_button = tk.Button(root, text="退出系统", command=root.quit)
        self.exit_button.pack(pady=10)

    def read_card(self):
        card_id_hex = read_rfid()
        card_id = rfid_id(card_id_hex)
        if card_id:
            student_info = get_student_info(card_id)
            if student_info:
                record_attendance(student_info['student_id'])
                messagebox.showinfo("签到成功", f"学生姓名：{student_info['name']}\n班级：{student_info['class_name']}\n学号：{student_info['student_id']}")
            else:
                if messagebox.askyesno("未找到信息", "未找到学生信息，添加学生信息"):
                    self.add_new_student(card_id)
        else:
            messagebox.showerror("错误", "未检测到RFID卡")

    def add_new_student(self, card_id):
        new_student_id = simpledialog.askstring("输入信息", "学号：")
        new_name = simpledialog.askstring("输入信息", "姓名：")
        new_class_id = simpledialog.askstring("输入信息", "班级：")
        new_class_name = simpledialog.askstring("输入信息", "专业：")
        if new_student_id and new_name and new_class_id and new_class_name:
            add_student(new_student_id, new_name, new_class_id, card_id, new_class_name)
            messagebox.showinfo("成功", "学生信息已添加，可以进行签到")
        else:
            messagebox.showerror("错误", "输入信息不完整，无法添加学生")

    def query_attendance_records(self):
        student_id = simpledialog.askstring("查询", "学号：")
        class_id = simpledialog.askstring("查询", "班级：")
        date = simpledialog.askstring("查询", "日期（格式YYYY-MM-DD）：")
        records = query_attendance(student_id, class_id, date)
        if records:
            records_text = "\n".join([f"学号：{r['student_id']}, 签到时间：{r['attendance_time']}" for r in records])
            messagebox.showinfo("签到记录", records_text)
        else:
            messagebox.showinfo("查询结果", "没有找到相关记录")

    def query_student_info(self):
        student_id = simpledialog.askstring("查询", "请输入学号：")
        student_info = query_student_info(student_id)
        if student_info:
            info_text = "\n".join([f"学号：{s['student_id']}, 姓名：{s['name']}, 班级：{s['class_name']}, 卡号：{s['card_id']}" for s in student_info])
            messagebox.showinfo("学生信息", info_text)
        else:
            messagebox.showinfo("查询结果", "没有找到相关学生信息")


if __name__ == "__main__":
    init_json()
    root = tk.Tk()
    system = RFIDSystem(root)
    root.mainloop()

    if ser.is_open:
        ser.close()
