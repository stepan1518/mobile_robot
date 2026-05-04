import socket
import threading
import json
import tkinter as tk
from tkinter import ttk
import time

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Robot Control")
        self.root.geometry("520x820")
        self.root.configure(bg='#1e1e1e')
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background='#1e1e1e', foreground='white', fieldbackground='#2d2d2d')
        self.style.configure('TLabel', background='#1e1e1e', foreground='white')
        self.style.configure('TFrame', background='#1e1e1e')
        self.style.configure('TScale', background='#1e1e1e')
        self.style.configure('TButton', background='#3d3d3d', foreground='white')

        self.distance = tk.StringVar(value='--')
        self.angle_error = tk.StringVar(value='--')
        self.max_speed = tk.DoubleVar(value=5.0)
        self.obstacle_avoidance = tk.DoubleVar(value=1.5)
        self.connected = False

        self.lidar_states = [None for _ in range(16)]
        self.camera1_state = None
        self.camera2_state = None

        self.conn = None
        self.running = True
        self.reconnect_requested = False
        self.reconnect_start_time = 0

        self.build_ui()
        self.start_client()

    def build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X, pady=(0,10))

        self.status_label = ttk.Label(status_frame, text="Статус: отключено", foreground='#cc3333')
        self.status_label.pack(side=tk.LEFT)

        self.reconnect_btn = ttk.Button(status_frame, text="⟳ Переподключить", command=self.do_reconnect)
        self.reconnect_btn.pack(side=tk.RIGHT)

        ttk.Label(main, text="Максимальная скорость").pack(anchor='w')
        ttk.Scale(main, from_=0.1, to=10.0, variable=self.max_speed, orient=tk.HORIZONTAL,
                  command=lambda e: self.send_params()).pack(fill=tk.X)

        ttk.Label(main, text="Чувствительность к препятствиям").pack(anchor='w', pady=(10,0))
        ttk.Scale(main, from_=0.0, to=5.0, variable=self.obstacle_avoidance, orient=tk.HORIZONTAL,
                  command=lambda e: self.send_params()).pack(fill=tk.X)

        info_frame = ttk.Frame(main)
        info_frame.pack(fill=tk.X, pady=10)
        ttk.Label(info_frame, text="Дистанция:").grid(row=0, column=0, sticky='w')
        ttk.Label(info_frame, textvariable=self.distance, font=('Arial', 12, 'bold')).grid(row=0, column=1, padx=5)
        ttk.Label(info_frame, text="Угол ошибки:").grid(row=1, column=0, sticky='w')
        ttk.Label(info_frame, textvariable=self.angle_error, font=('Arial', 12, 'bold')).grid(row=1, column=1, padx=5)

        lidar_frame = ttk.LabelFrame(main, text="LiDAR датчики", padding=5)
        lidar_frame.pack(fill=tk.X, pady=10)

        self.lidar_widgets = []
        for i in range(16):
            f = tk.Frame(lidar_frame, bg='#1e1e1e')
            f.grid(row=i//4, column=i%4, padx=4, pady=4)
            tk.Label(f, text=f"L{i+1}", bg='#1e1e1e', fg='white', font=('Arial', 9, 'bold')).pack()
            status = tk.Label(f, text='OFF', bg='#555555', fg='white', font=('Arial', 8, 'bold'),
                              width=6, relief=tk.RIDGE, borderwidth=1)
            status.pack()
            self.lidar_widgets.append(status)

        cam_frame = ttk.LabelFrame(main, text="Камеры", padding=5)
        cam_frame.pack(fill=tk.X, pady=10)
        self.cam_widgets = []
        for name in ['Cam 1', 'Cam 2']:
            f = tk.Frame(cam_frame, bg='#1e1e1e')
            f.pack(side=tk.LEFT, padx=12)
            tk.Label(f, text=name, bg='#1e1e1e', fg='white', font=('Arial', 9, 'bold')).pack()
            status = tk.Label(f, text='OFF', bg='#555555', fg='white', font=('Arial', 8, 'bold'),
                              width=8, relief=tk.RIDGE, borderwidth=1)
            status.pack()
            self.cam_widgets.append(status)

        self.update_indicators()

    def update_indicators(self):
        for i, w in enumerate(self.lidar_widgets):
            state = self.lidar_states[i]
            if state is None: w.config(text='OFF', bg='#555555')
            elif state: w.config(text='DET', bg='#cc3333')
            else: w.config(text='CLR', bg='#33aa33')

        for idx, attr in enumerate([self.camera1_state, self.camera2_state]):
            if attr is None: self.cam_widgets[idx].config(text='OFF', bg='#555555')
            elif attr: self.cam_widgets[idx].config(text='OK', bg='#33aa33')
            else: self.cam_widgets[idx].config(text='ERR', bg='#cc3333')
        self.root.after(100, self.update_indicators)

    def do_reconnect(self):
        if self.conn:
            try: self.conn.close()
            except: pass
        self.conn = None
        self.connected = False
        self.reconnect_requested = True
        self.reconnect_start_time = time.time()
        self.status_label.config(text="Статус: переподключение...", foreground='#ccaa33')

    def send_params(self):
        if self.conn and self.connected:
            cmd = {"max_speed": self.max_speed.get(), "obstacleAvoidance": self.obstacle_avoidance.get()}
            try: self.conn.send((json.dumps(cmd) + '\n').encode())
            except: pass

    def client_thread(self):
        while self.running:
            if self.conn is None:
                # Проверяем таймаут переподключения (3 секунды)
                if self.reconnect_requested and time.time() - self.reconnect_start_time > 3:
                    self.reconnect_requested = False
                    self.status_label.config(text="Статус: отключено", foreground='#cc3333')
                    time.sleep(1)
                    continue

                try:
                    self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.conn.connect(('127.0.0.1', 9999))
                    self.conn.setblocking(False)
                    self.connected = True
                    self.reconnect_requested = False
                    self.status_label.config(text="Статус: подключено", foreground='#33aa33')
                    self.send_params()
                except:
                    self.conn = None
                    self.connected = False
                    if self.reconnect_requested:
                        self.status_label.config(text="Статус: переподключение...", foreground='#ccaa33')
                    else:
                        self.status_label.config(text="Статус: отключено", foreground='#cc3333')
                    time.sleep(1)
                    continue

            try:
                data = self.conn.recv(4096)
                if data:
                    for line in data.decode().split('\n'):
                        if line.strip():
                            try:
                                tele = json.loads(line)
                                self.distance.set(f"{tele['distance']:.2f}")
                                self.angle_error.set(f"{tele['angleError']:.1f}°")
                                for i, v in enumerate(tele.get('lidars', [])):
                                    self.lidar_states[i] = v
                                self.camera1_state = tele.get('cameras', {}).get('working', None)
                                self.camera2_state = tele.get('cameras', {}).get('working2', None)
                            except: pass
                elif data == b'':
                    raise ConnectionError("disconnected")
            except BlockingIOError:
                pass
            except:
                if self.conn:
                    try: self.conn.close()
                    except: pass
                self.conn = None
                self.connected = False
                self.status_label.config(text="Статус: отключено", foreground='#cc3333')
                self.lidar_states = [None for _ in range(16)]
                self.camera1_state = None
                self.camera2_state = None
                self.distance.set('--')
                self.angle_error.set('--')
            time.sleep(0.05)

    def start_client(self):
        threading.Thread(target=self.client_thread, daemon=True).start()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        self.running = False
        if self.conn: self.conn.close()
        self.root.destroy()

if __name__ == "__main__":
    App().run()