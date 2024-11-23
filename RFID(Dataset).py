import datetime
import serial
import sqlite3
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


def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students
                 (student_id TEXT PRIMARY KEY, name TEXT, class_id TEXT, card_id TEXT, class_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (student_id TEXT, attendance_time TEXT, FOREIGN KEY(student_id) REFERENCES students(student_id))''')
    conn.commit()
    conn.close()


def add_student(student_id, name, class_id, card_id, class_name):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO students (student_id, name, class_id, card_id, class_name) VALUES (?, ?, ?, ?, ?)',
                  (student_id, name, class_id, card_id, class_name))
        conn.commit()
        print("学生信息添加成功。")
    except sqlite3.IntegrityError:
        print("学生信息已存在，无需重复添加。")
    finally:
        conn.close()


def record_attendance(student_id):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('INSERT INTO attendance (student_id, attendance_time) VALUES (?, ?)',
              (student_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_student_info(card_id):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('SELECT * FROM students WHERE card_id = ?', (card_id,))
    student_info = c.fetchone()
    conn.close()
    return student_info


def query_attendance(student_id=None, class_id=None, date=None):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    query = 'SELECT students.student_id, students.name, students.class_name, attendance.attendance_time FROM students JOIN attendance ON students.student_id = attendance.student_id WHERE 1=1'

    # 添加查询条件
    if student_id:
        query += ' AND students.student_id = ?'
    if class_id:
        query += ' AND students.class_id = ?'
    if date:
        query += ' AND DATE(attendance.attendance_time) = ?'

    # 执行查询
    if student_id or class_id or date:
        c.execute(query, (student_id, class_id, date))
    else:
        c.execute(query)

    # 获取查询结果
    attendance_records = c.fetchall()
    conn.close()
    return attendance_records


def query_student_info(student_id=None):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    if student_id:
        c.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
    else:
        c.execute('SELECT * FROM students')

    # 获取查询结果
    student_info = c.fetchall()
    conn.close()
    return student_info


def main():
    init_db()
    while True:
        print("\n请刷卡：")
        card_id_hex = read_rfid()
        card_id = rfid_id(card_id_hex)
        if card_id:
            student_info = get_student_info(card_id)
            if student_info:
                print(f"学生姓名：{student_info[1]}, 班级：{student_info[4]}, 学号：{student_info[0]}")
                record_attendance(student_info[0])
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
                print(f"学号：{record[0]}, 姓名：{record[1]}, 班级：{record[2]}, 签到时间：{record[3]}")
        elif choice == '3':
            student_id = input("请输入学号（查询单个学生信息，留空查询所有学生）：")
            student_info = query_student_info(student_id)
            for info in student_info:
                print(f"学号：{info[0]}, 姓名：{info[1]}, 班级号：{info[2]}, 班级名称：{info[4]}, 卡号：{info[3]}")
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