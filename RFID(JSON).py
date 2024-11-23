import datetime
import json
import os

import serial
import time


# 初始化串口
ser = serial.Serial('COM3', 9600, timeout=1)


def read_rfid():
    while True:
        if ser.in_waiting > 0:
            data = ser.readline()
            if data:
                # 将二进制数据转换为十六进制字符串，并在每两个字符后添加空格
                hex_data = data.hex().upper()
                formatted_hex_data = ' '.join(hex_data[i:i+2] for i in range(0, len(hex_data), 2))
                print("Label Detail:", formatted_hex_data)
                break
            else:
                print("Error")
        # 清空输入缓冲区
        ser.flushInput()
        time.sleep(0.5)  # 延时0.5秒
    return formatted_hex_data


def rfid_id(hex_data):
    return hex_data[-14:-2]


def init_json():
    students_file = 'students.json'
    attendance_file = 'attendance.json'

    if not os.path.exists(students_file):
        with open(students_file, 'w') as f:
            json.dump([], f)

    if not os.path.exists(attendance_file):
        with open(attendance_file, 'w') as f:
            json.dump([], f)


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
        f.seek(0)
        json.dump(students, f)
        f.truncate()


def record_attendance(student_id):
    attendance_file = 'attendance.json'
    with open(attendance_file, 'a') as f:  # 使用 'a' 模式以支持追加
        attendance = {
            'student_id': student_id,
            'attendance_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        json.dump(attendance, f)
        f.write('\n')


def get_student_info(card_id):
    students_file = 'students.json'
    with open(students_file, 'r') as f:
        students = json.load(f)
        for student in students:
            if student['card_id'] == card_id:
                return student
    return None


def query_attendance(student_id=None, class_id=None, date=None):
    attendance_file = 'attendance.json'
    with open(attendance_file, 'r') as f:
        attendance_records = json.load(f)
        filtered_records = []
        for record in attendance_records:
            if (student_id and record['student_id'] != student_id) or \
               (class_id and record['student_id'] not in [s['student_id'] for s in json.load(open('students.json', 'r')) if s['class_id'] == class_id]) or \
               (date and datetime.datetime.strptime(record['attendance_time'], "%Y-%m-%d %H:%M:%S").date() != datetime.datetime.strptime(date, "%Y-%m-%d").date()):
                continue
            filtered_records.append(record)
        return filtered_records


def query_student_info(student_id=None):
    students_file = 'students.json'
    with open(students_file, 'r') as f:
        students = json.load(f)
        if student_id:
            for student in students:
                if student['student_id'] == student_id:
                    return [student]
        return students


def main():
    init_json()
    while True:
        print("\n请刷卡：")
        card_id_hex = read_rfid()
        card_id = rfid_id(card_id_hex)
        if card_id:
            student_info = get_student_info(card_id)
            if student_info:
                print(f"学生姓名：{student_info['name']}, 班级：{student_info['class_name']}, 学号：{student_info['student_id']}")
                record_attendance(student_info['student_id'])
            else:
                print("未找到学生信息，请输入新学生信息进行开卡：")
                new_student_id = input("请输入学生学号：")
                new_name = input("请输入学生姓名：")
                new_class_id = input("请输入班级号：")
                new_class_name = input("请输入班级名称：")
                add_student(new_student_id, new_name, new_class_id, card_id, new_class_name)
                print("新学生信息已添加，可以进行签到。")

        else:
            print("未检测到RFID卡，请重试。")

        print("\n1. 继续刷卡签到")
        print("2. 查询签到信息")
        print("3. 查询学生信息")
        print("4. 退出")
        choice = input("请选择一个操作：")

        if choice == '1':
            continue
        elif choice == '2':
            student_id = input("请输入学号（可选）：")
            class_id = input("请输入班级号（可选）：")
            date = input("请输入日期（格式YYYY-MM-DD，可选）：")
            records = query_attendance(student_id, class_id, date)
            for record in records:
                print(f"学号：{record['student_id']}, 姓名：{get_student_info(record['student_id'])['name']}, 班级：{get_student_info(record['student_id'])['class_name']}, 签到时间：{record['attendance_time']}")
        elif choice == '3':
            student_id = input("请输入学号（查询单个学生信息，留空查询所有学生）：")
            student_info = query_student_info(student_id)
            for info in student_info:
                print(f"学号：{info['student_id']}, 姓名：{info['name']}, 班级号：{info['class_id']}, 班级名称：{info['class_name']}, 卡号：{info['card_id']}")
        elif choice == '4':
            break
        else:
            print("无效的选择，请重新输入。")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
    finally:
        if ser.is_open:
            ser.close()
