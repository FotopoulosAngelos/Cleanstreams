# main.py - CleanStreams (FULL + STYLESHEET FIX + ALL FEATURES)
import sys
import sqlite3
import os
import math
import cv2
import numpy as np
from datetime import datetime
import warnings
import time
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --------------------------------------------------------------
# IMPORTS
# --------------------------------------------------------------
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QMessageBox, QDialog, QGroupBox, QPushButton,
    QLineEdit, QTextEdit
)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt, QObject, pyqtSlot, QMimeData
from PyQt5.QtGui import QPixmap, QFont, QImage, QIcon, QDrag
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel

import folium
from io import BytesIO
import socket

# ----------------------------------------------------------------------
# Styles – fallback if styles.qss is missing
# ----------------------------------------------------------------------
try:
    with open("styles.qss", "r", encoding="utf-8") as f:
        STYLESHEET = f.read()
except Exception:
    STYLESHEET = """
        QWidget { background:#f8f8f8; font-family:Arial; }
        QLabel { color:#333; }
        QLineEdit, QTextEdit { padding:8px; border:1px solid #ccc; border-radius:6px; }
        QPushButton { background:#00A896; color:white; border-radius:8px; padding:10px; }
        QPushButton:hover { background:#008F7A; }
    """

# ----------------------------------------------------------------------
# RoundedButton
# ----------------------------------------------------------------------
class RoundedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #00A896;
                color: white;
                border-radius: 12px;
                padding: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #008F7A; }
            QPushButton:pressed { background-color: #006D5B; }
        """)

# ----------------------------------------------------------------------
# Draggable Marker (sidebar)
# ----------------------------------------------------------------------
class DraggableMarker(QLabel):
    def __init__(self, icon_path, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        pix = QPixmap(icon_path).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(pix)
        self.setToolTip(f"Drag {kind.title()} marker to map")
        self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.kind)
        drag.setMimeData(mime)
        drag.setPixmap(self.pixmap())
        drag.exec_(Qt.CopyAction)

# ----------------------------------------------------------------------
# Icon loader
# ----------------------------------------------------------------------
def load_icon(path, size=(30, 30)):
    lbl = QLabel()
    if os.path.exists(path):
        pix = QPixmap(path).scaled(*size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    else:
        pix = QPixmap(*size); pix.fill(Qt.lightGray)
    lbl.setPixmap(pix)
    return lbl

# ----------------------------------------------------------------------
# Drone Thread
# ----------------------------------------------------------------------
class DroneThread(QThread):
    response_received = pyqtSignal(str)

    def __init__(self, sock, running_flag):
        super().__init__()
        self.sock = sock
        self.running_flag = running_flag

    def run(self):
        while self.running_flag():
            try:
                data, _ = self.sock.recvfrom(1024)
                msg = data.decode().strip()
                self.response_received.emit(msg)
            except:
                break

# ----------------------------------------------------------------------
# Video Thread
# ----------------------------------------------------------------------
class VideoThread(QThread):
    change_pixmap = pyqtSignal(QImage)
    record_frame = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        cap = cv2.VideoCapture("udp://0.0.0.0:11111")
        while self.running and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
                self.change_pixmap.emit(img)
                self.record_frame.emit(frame.copy())
            time.sleep(0.03)
        cap.release()

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

# ----------------------------------------------------------------------
# Splash Page
# ----------------------------------------------------------------------
class SplashPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = parent.parent()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(20)

        title = QLabel("Clean Streams")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        sub = QLabel("Clean streams, safer cities")
        sub.setFont(QFont("Arial", 16))
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #666;")
        lay.addWidget(sub)

        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.prog.setTextVisible(False)
        self.prog.setStyleSheet(
            "QProgressBar { border-radius: 5px; background: #eee; }"
            "QProgressBar::chunk { background: #00A896; border-radius: 5px; }"
        )
        lay.addWidget(self.prog)

        self.btn_container = QWidget()
        self.btn_container.setVisible(False)
        btn_lay = QVBoxLayout(self.btn_container)
        btn_lay.setSpacing(20)

        self.drone_btn = QPushButton()
        pix = QPixmap("assets/Drone operator.png").scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.drone_btn.setIcon(QIcon(pix)); self.drone_btn.setIconSize(pix.size())
        self.drone_btn.setFlat(True); self.drone_btn.setStyleSheet("background: transparent;")
        btn_lay.addWidget(self.drone_btn)

        self.service_btn = QPushButton()
        pix2 = QPixmap("assets/Service employee.png").scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.service_btn.setIcon(QIcon(pix2)); self.service_btn.setIconSize(pix2.size())
        self.service_btn.setFlat(True); self.service_btn.setStyleSheet("background: transparent;")
        btn_lay.addWidget(self.service_btn)

        lay.addWidget(self.btn_container)

        self.val = 0
        self.ptmr = QTimer(self)
        self.ptmr.timeout.connect(self.inc_prog)
        self.ptmr.start(30)

    def inc_prog(self):
        self.val += 1
        self.prog.setValue(self.val)
        if self.val >= 100:
            self.ptmr.stop()
            self.btn_container.setVisible(True)
            self.drone_btn.clicked.connect(lambda: self.app.show_login())
            self.service_btn.clicked.connect(lambda: self.app.show_login())

# ----------------------------------------------------------------------
# Login Page
# ----------------------------------------------------------------------
class LoginPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = parent.parent()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(20)

        title = QLabel("Clean Streams")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        lay.addWidget(title, alignment=Qt.AlignCenter)

        sub = QLabel("Fill in your credentials")
        sub.setFont(QFont("Arial", 16))
        sub.setStyleSheet("color: #666;")
        lay.addWidget(sub, alignment=Qt.AlignCenter)

        self.user = QLineEdit(); self.user.setPlaceholderText("Username")
        self.user.setStyleSheet("padding:12px;border:1px solid #ddd;border-radius:8px;")
        lay.addWidget(self.user)

        self.pwd = QLineEdit(); self.pwd.setPlaceholderText("Password")
        self.pwd.setEchoMode(QLineEdit.Password)
        self.pwd.setStyleSheet("padding:12px;border:1px solid #ddd;border-radius:8px;")
        lay.addWidget(self.pwd)

        self.forgot = QLabel("<a href='#'>Forgot password?</a>")
        self.forgot.setStyleSheet("color:#00A896;")
        self.forgot.setOpenExternalLinks(True)
        lay.addWidget(self.forgot, alignment=Qt.AlignRight)

        login_btn = RoundedButton("Login")
        login_btn.setStyleSheet("background:#00A896;color:white;padding:12px;")
        login_btn.clicked.connect(self.do_login)
        lay.addWidget(login_btn)

    def do_login(self):
        u, p = self.user.text().strip(), self.pwd.text().strip()
        if not u or not p:
            QMessageBox.warning(self, "Error", "Fill both fields")
            return
        try:
            con = sqlite3.connect("users.db")
            cur = con.cursor()
            cur.execute("SELECT password FROM users WHERE username=?", (u,))
            row = cur.fetchone()
            con.close()
            if row and row[0] == p:
                self.app.show_connect_page(u)
            else:
                QMessageBox.warning(self, "Error", "Invalid credentials")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

# ----------------------------------------------------------------------
# Connect Page
# ----------------------------------------------------------------------
class ConnectPage(QWidget):
    def __init__(self, parent=None, username=""):
        super().__init__(parent)
        self.app = parent.parent()
        self.username = username
        self.running = False
        self.sock = None
        self.connected = False
        self.stream_sent = False
        self.stream_ready = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(30)

        title = QLabel("Clean Streams")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        sub = QLabel("Connect to Drone")
        sub.setFont(QFont("Arial", 18))
        sub.setStyleSheet("color:#666;")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        info = QLabel("Ensure you are connected to Tello Wi-Fi")
        info.setFont(QFont("Arial", 14))
        info.setStyleSheet("color:#888;")
        info.setAlignment(Qt.AlignCenter)
        lay.addWidget(info)

        self.connect_btn = RoundedButton("Connect to Drone")
        self.connect_btn.setStyleSheet("background:#00A896;color:white;padding:12px;font-size:16px;")
        self.connect_btn.clicked.connect(self.start_connect)
        lay.addWidget(self.connect_btn, alignment=Qt.AlignCenter)

        self.status = QLabel("Not connected")
        self.status.setStyleSheet("color:red;font-weight:bold;")
        self.status.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.status)

        lay.addStretch()

    def start_connect(self):
        if self.connected: return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', 9000))
            self.sock.settimeout(5)
            self.app.drone_socket = self.sock
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Socket error: {e}")
            return

        self.running = True
        self.connected = False
        self.stream_sent = False
        self.stream_ready = False

        self.thread = DroneThread(self.sock, lambda: self.running)
        self.thread.response_received.connect(self.on_response)
        self.thread.start()

        self.status.setText("Connecting...")
        self.status.setStyleSheet("color:orange;font-weight:bold;")
        self.send_command("command")

        self.fallback_timer = QTimer(self)
        self.fallback_timer.timeout.connect(self.connection_failed)
        self.fallback_timer.start(12000)

    def send_command(self, cmd):
        if not self.sock: return
        try:
            self.sock.sendto(cmd.encode(), ('192.168.10.1', 8889))
        except Exception as e:
            print("Send error:", e)

    def on_response(self, msg):
        print("Drone:", msg)

        if msg.isdigit():
            battery = int(msg)
            self.app.battery_level = battery
            self.status.setText(f"Connected! Battery: {battery}%")
            self.status.setStyleSheet("color:green;font-weight:bold;")
            self.connected = True
            self.fallback_timer.stop()

            if not self.stream_sent:
                self.stream_sent = True
                QTimer.singleShot(800, lambda: self.send_command("streamon"))

        elif msg.lower() == "ok" and self.stream_sent and not self.stream_ready:
            self.stream_ready = True
            self.app.stream_ready = True
            QTimer.singleShot(500, lambda: self.app.show_homepage(self.username))

        elif msg.lower() == "ok" and not self.connected:
            self.connected = True
            self.send_command("battery?")

    def connection_failed(self):
        if not self.connected:
            self.status.setText("Connection failed")
            self.status.setStyleSheet("color:red;font-weight:bold;")
            QMessageBox.critical(self, "Error", "Could not connect to Tello.\nCheck Wi-Fi and try again.")
            self.cleanup()

    def cleanup(self):
        self.running = False
        if hasattr(self, "thread"):
            self.thread.quit()
            self.thread.wait()
        if self.sock:
            try: self.sock.close()
            except: pass
        self.sock = None
        self.app.drone_socket = None

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

# ----------------------------------------------------------------------
# Home Page – GPS MAP
# ----------------------------------------------------------------------
class Homepage(QWidget):
    def __init__(self, parent=None, username=""):
        super().__init__(parent)
        self.app = parent.parent()
        self.username = username

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 10, 20, 10)

        hdr = QWidget()
        hdr.setStyleSheet("background:#000;color:white;padding:10px;")
        hlay = QHBoxLayout(hdr)
        hlay.addWidget(QLabel("Clean Streams"))
        hlay.addStretch()
        hlay.addWidget(load_icon("assets/user-avatar.png", (40, 40)))
        lay.addWidget(hdr)

        home_lbl = QLabel("Home")
        home_lbl.setFont(QFont("Arial", 14, QFont.Bold))
        home_lbl.setStyleSheet("color:#00A896;")
        lay.addWidget(home_lbl)

        welcome = QLabel(f"Welcome, {username}")
        welcome.setFont(QFont("Arial", 14))
        welcome.setStyleSheet("color:#666;")
        lay.addWidget(welcome)

        img = QLabel()
        if os.path.exists("assets/drone-img.png"):
            img.setPixmap(QPixmap("assets/drone-img.png").scaledToHeight(180, Qt.SmoothTransformation))
        else:
            img.setText("Drone Image\n(Missing)")
        img.setAlignment(Qt.AlignCenter)
        lay.addWidget(img)

        status = QHBoxLayout()
        bat = QGroupBox(); bat.setStyleSheet("border:1px solid #ddd;border-radius:8px;")
        bl = QHBoxLayout(bat)
        bl.addWidget(load_icon("assets/hugeicons_battery.png"))
        self.bat_lbl = QLabel("...\nBattery")
        bl.addWidget(self.bat_lbl)
        status.addWidget(bat)

        time_box = QGroupBox(); time_box.setStyleSheet("border:1px solid #ddd;border-radius:8px;")
        tl = QHBoxLayout(time_box)
        tl.addWidget(load_icon("assets/hugeicons_clock.png"))
        self.time_lbl = QLabel("0 min\nRemaining")
        tl.addWidget(self.time_lbl)
        status.addWidget(time_box)
        lay.addLayout(status)

        self.map_view = QWebEngineView()
        self.load_map_with_gps()
        lay.addWidget(self.map_view)

        new_flight = RoundedButton("New flight")
        new_flight.setStyleSheet("background:#00A896;color:white;padding:12px;")
        new_flight.clicked.connect(self.open_flight_dialog)
        lay.addWidget(new_flight)

        self.home_timer = QTimer(self)
        self.home_timer.timeout.connect(self.update_home_status)
        self.home_timer.start(2000)
        QTimer.singleShot(1000, self.update_home_status)

    def load_map_with_gps(self):
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>GPS Map</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style> html, body, #map { height: 100%; margin: 0; } </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([38.290427, 21.794836], 12);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

                function onLocationFound(e) {
                    map.setView(e.latlng, 15);
                    L.marker(e.latlng).addTo(map).bindPopup("You are here").openPopup();
                }

                function onLocationError(e) {
                    map.setView([38.290427, 21.794836], 12);
                }

                map.locate({setView: true, maxZoom: 16});
                map.on('locationfound', onLocationFound);
                map.on('locationerror', onLocationError);
            </script>
        </body>
        </html>
        '''
        self.map_view.setHtml(html)

    def update_home_status(self):
        battery = getattr(self.app, 'battery_level', 0)
        if isinstance(battery, int):
            self.bat_lbl.setText(f"{battery}%\nBattery")
            remaining_min = int((battery / 100.0) * 12)
            self.time_lbl.setText(f"{remaining_min} min\nRemaining")
        else:
            self.bat_lbl.setText("...\nBattery")
            self.time_lbl.setText("0 min\nRemaining")

    def open_flight_dialog(self):
        dlg = FlightDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            name, notes = dlg.get_data()
            self.app.show_route_page(name, notes)

# ----------------------------------------------------------------------
# Flight Dialog
# ----------------------------------------------------------------------
class FlightDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Flight details")
        self.setModal(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)

        lay.addWidget(QLabel("Provide a name for the flight"))
        self.name = QLineEdit(); self.name.setPlaceholderText("Flight name*")
        lay.addWidget(self.name)
        self.notes = QTextEdit(); self.notes.setPlaceholderText("Notes")
        self.notes.setMaximumHeight(80)
        lay.addWidget(self.notes)

        save = RoundedButton("Save flight")
        save.setStyleSheet("background:#00A896;color:white;")
        save.clicked.connect(self.accept)
        lay.addWidget(save)

    def get_data(self):
        return self.name.text().strip(), self.notes.toPlainText().strip()

# ----------------------------------------------------------------------
# Map Bridge
# ----------------------------------------------------------------------
class MapBridge(QObject):
    clicked = pyqtSignal(float, float)
    marker_moved = pyqtSignal(str, float, float)
    drop_received = pyqtSignal(str, float, float)

    @pyqtSlot(float, float)
    def onMapClick(self, lat, lng):
        self.clicked.emit(lat, lng)

    @pyqtSlot(str, float, float)
    def onMarkerDrag(self, kind, lat, lng):
        self.marker_moved.emit(kind, lat, lng)

    @pyqtSlot(str, float, float)
    def onDrop(self, kind, lat, lng):
        self.drop_received.emit(kind, lat, lng)

# ----------------------------------------------------------------------
# Route Page – FULL MAP CONTROL
# ----------------------------------------------------------------------
class RoutePage(QWidget):
    def __init__(self, parent=None, flight_name="", flight_notes=""):
        super().__init__(parent)
        self.app = parent.parent()
        self.flight_name = flight_name
        self.flight_notes = flight_notes
        self.start_point = None
        self.end_point = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)

        # LEFT: Map
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)

        hdr = QWidget()
        hdr.setStyleSheet("background:#000;color:white;padding:10px;")
        hl = QHBoxLayout(hdr)
        hl.addWidget(QLabel("Clean Streams"))
        hl.addStretch()
        hl.addWidget(load_icon("assets/user-avatar.png", (40, 40)))
        left_lay.addWidget(hdr)

        self.web = QWebEngineView()
        self.web.setAcceptDrops(True)
        self.web.installEventFilter(self)
        left_lay.addWidget(self.web, 1)

        # RIGHT: Controls
        right = QWidget()
        right.setFixedWidth(280)
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(15, 15, 15, 15)
        right_lay.setSpacing(15)

        right_lay.addWidget(QLabel("Set route points"))
        right_lay.addWidget(QLabel("Tap map or drag icons"))

        marker_box = QGroupBox("Drag to Map")
        marker_lay = QVBoxLayout(marker_box)
        marker_lay.setSpacing(10)

        self.start_marker = DraggableMarker("assets/start_marker.png", "start", self)
        marker_lay.addWidget(self.start_marker, alignment=Qt.AlignCenter)

        self.end_marker = DraggableMarker("assets/end_marker.png", "end", self)
        marker_lay.addWidget(self.end_marker, alignment=Qt.AlignCenter)

        right_lay.addWidget(marker_box)

        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("Start: lat, lng")
        self.start_input.textChanged.connect(lambda: self.parse_input("start"))
        right_lay.addWidget(self.start_input)

        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("End: lat, lng")
        self.end_input.textChanged.connect(lambda: self.parse_input("end"))
        right_lay.addWidget(self.end_input)

        self.dist_label = QLabel("Distance: — m")
        right_lay.addWidget(self.dist_label)

        confirm = RoundedButton("Confirm Route")
        confirm.clicked.connect(self.confirm_route)
        right_lay.addWidget(confirm)

        info_layout = QHBoxLayout()
        bat_box = QGroupBox(); bat_box.setStyleSheet("border:1px solid #ddd;border-radius:8px;")
        bat_lay = QHBoxLayout(bat_box); bat_lay.addWidget(load_icon("assets/hugeicons_battery.png"))
        self.bat_label = QLabel("...\nBattery"); bat_lay.addWidget(self.bat_label)
        info_layout.addWidget(bat_box)

        time_box = QGroupBox(); time_box.setStyleSheet("border:1px solid #ddd;border-radius:8px;")
        time_lay = QHBoxLayout(time_box); time_lay.addWidget(load_icon("assets/hugeicons_clock.png"))
        self.time_label = QLabel("0 min\nRemaining"); time_lay.addWidget(self.time_label)
        info_layout.addWidget(time_box)
        right_lay.addLayout(info_layout)

        right_lay.addStretch()

        lay.addWidget(left, 1)
        lay.addWidget(right)

        self.bridge = MapBridge()
        self.bridge.clicked.connect(self.on_map_click)
        self.bridge.marker_moved.connect(self.on_marker_drag)
        self.bridge.drop_received.connect(self.on_drop)
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(self.channel)

        self.refresh_map()
        QTimer.singleShot(100, self.update_status)

    def eventFilter(self, source, event):
        if source == self.web and event.type() == event.Drop:
            pos = event.pos()
            self.web.page().runJavaScript(f"""
                (function() {{
                    const rect = document.getElementById('map').getBoundingClientRect();
                    const x = {pos.x()} - rect.left;
                    const y = {pos.y()} - rect.top;
                    const point = map.containerPointToLatLng(L.point(x, y));
                    return {{lat: point.lat, lng: point.lng}};
                }})();
            """, self.handle_drop_result)
            return True
        return super().eventFilter(source, event)

    def handle_drop_result(self, result):
        if isinstance(result, dict):
            lat, lng = result.get('lat'), result.get('lng')
            if lat and lng:
                mime = QApplication.clipboard().mimeData()
                if mime and mime.hasText():
                    kind = mime.text()
                    self.bridge.drop_received.emit(kind, lat, lng)

    def on_drop(self, kind, lat, lng):
        self.set_point(kind, [lat, lng])

    def on_map_click(self, lat, lng):
        if not self.start_point:
            self.set_point("start", [lat, lng])
        elif not self.end_point:
            self.set_point("end", [lat, lng])

    def on_marker_drag(self, kind, lat, lng):
        self.set_point(kind, [lat, lng])

    def set_point(self, kind, point):
        if kind == "start":
            self.start_point = point
            self.start_input.setText(f"{point[0]:.6f}, {point[1]:.6f}")
        else:
            self.end_point = point
            self.end_input.setText(f"{point[0]:.6f}, {point[1]:.6f}")
        self.update_distance()
        self.refresh_map()

    def parse_input(self, kind):
        text = self.start_input.text().strip() if kind == "start" else self.end_input.text().strip()
        if not text: return
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 2: return
        try:
            lat, lng = float(parts[0]), float(parts[1])
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                self.set_point(kind, [lat, lng])
        except: pass

    def update_distance(self):
        if self.start_point and self.end_point:
            dist = self.haversine(*self.start_point, *self.end_point)
            self.dist_label.setText(f"Distance: {dist:.1f} m")

    def update_status(self):
        battery = getattr(self.app, 'battery_level', 0)
        if isinstance(battery, int):
            self.bat_label.setText(f"{battery}%\nBattery")
            mins = int((battery / 100.0) * 12)
            self.time_label.setText(f"{mins} min\nRemaining")
        QTimer.singleShot(5000, self.update_status)

    def refresh_map(self):
        center = [38.290427, 21.794836]
        if self.start_point: center = self.start_point
        elif self.end_point: center = self.end_point

        start_js = f"addStart({self.start_point[0]}, {self.start_point[1]});" if self.start_point else ""
        end_js = f"addEnd({self.end_point[0]}, {self.end_point[1]});" if self.end_point else ""

        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Route Map</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style> html, body, #map {{ height: 100%; margin: 0; }} </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{center[0]}, {center[1]}], 15);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

                var startMarker = null, endMarker = null;
                var bridge = null;

                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    bridge = channel.objects.bridge;
                }});

                map.on('click', function(e) {{
                    if (bridge) bridge.onMapClick(e.latlng.lat, e.latlng.lng);
                }});

                window.addStart = function(lat, lng) {{
                    if (startMarker) startMarker.setLatLng([lat, lng]);
                    else {{
                        startMarker = L.marker([lat, lng], {{
                            draggable: true,
                            icon: L.icon({{iconUrl: 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-icon.png', iconAnchor: [12,41]}})
                        }}).addTo(map);
                        startMarker.on('dragend', function(e) {{
                            var pos = e.target.getLatLng();
                            if (bridge) bridge.onMarkerDrag('start', pos.lat, pos.lng);
                        }});
                    }}
                }};

                window.addEnd = function(lat, lng) {{
                    if (endMarker) endMarker.setLatLng([lat, lng]);
                    else {{
                        endMarker = L.marker([lat, lng], {{
                            draggable: true,
                            icon: L.icon({{iconUrl: 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-icon.png', iconAnchor: [12,41]}})
                        }}).addTo(map);
                        endMarker.on('dragend', function(e) {{
                            var pos = e.target.getLatLng();
                            if (bridge) bridge.onMarkerDrag('end', pos.lat, pos.lng);
                        }});
                    }}
                }};

                {start_js}
                {end_js}
            </script>
        </body>
        </html>
        '''
        self.web.setHtml(html)

    def confirm_route(self):
        if not self.start_point or not self.end_point:
            QMessageBox.warning(self, "Error", "Set **both** points")
            return
        dist = self.haversine(*self.start_point, *self.end_point)
        self.app.show_flight_page(self.flight_name, self.flight_notes, dist,
                                  self.start_point, self.end_point)

    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2-lat1)
        dlambda = math.radians(lon2-lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ----------------------------------------------------------------------
# Flight Page – SLEEP BETWEEN COMMANDS
# ----------------------------------------------------------------------
class FlightPage(QWidget):
    def __init__(self, parent=None, flight_name="", flight_notes="", distance=0, start=None, end=None):
        super().__init__(parent)
        self.app = parent.parent()
        self.flight_name = flight_name
        self.distance = distance
        self.start = start
        self.end = end
        self.recorder = None
        self.video_thread = None
        self.is_flying = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 10, 20, 10)

        hdr = QWidget()
        hdr.setStyleSheet("background:#000;color:white;padding:10px;")
        hl = QHBoxLayout(hdr)
        hl.addWidget(QLabel("Clean Streams"))
        hl.addStretch()
        hl.addWidget(load_icon("assets/user-avatar.png", (40, 40)))
        lay.addWidget(hdr)

        lay.addWidget(QLabel(f"Flight: {flight_name}"))
        lay.addWidget(QLabel(f"Distance: {distance:.1f} m"))

        self.video_label = QLabel()
        self.video_label.setStyleSheet("background:#222;border:2px solid #333;")
        self.video_label.setMinimumHeight(300)
        self.video_label.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.video_label, 1)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color:#00A896;font-weight:bold;")
        lay.addWidget(self.status_label)

        start_flight = RoundedButton("Start Auto Flight")
        start_flight.clicked.connect(self.start_auto_flight)
        lay.addWidget(start_flight)

        self.start_video_when_ready()

    def start_video_when_ready(self):
        def check():
            if getattr(self.app, "stream_ready", False):
                self.video_thread = VideoThread()
                self.video_thread.change_pixmap.connect(self.update_video)
                self.video_thread.record_frame.connect(self.write_frame)
                self.video_thread.start()
            else:
                QTimer.singleShot(300, check)
        QTimer.singleShot(300, check)

    def update_video(self, img: QImage):
        scaled = img.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(QPixmap.fromImage(scaled))

    def write_frame(self, frame: np.ndarray):
        if self.recorder and self.recorder.isOpened():
            self.recorder.write(frame)

    def start_recording(self):
        if self.recorder: return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("flights", exist_ok=True)
        filename = f"flights/{self.flight_name}_{timestamp}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.recorder = cv2.VideoWriter(filename, fourcc, 30.0, (960, 720))
        if not self.recorder.isOpened():
            QMessageBox.critical(self, "Error", "Failed to open video writer")
            return
        self.status_label.setText(f"Recording: {os.path.basename(filename)}")

    def stop_recording(self):
        if self.recorder:
            self.recorder.release()
            self.recorder = None
            self.status_label.setText("Flight complete – video saved!")

    def send_command(self, cmd):
        if self.app.drone_socket:
            try:
                self.app.drone_socket.sendto(cmd.encode(), ('192.168.10.1', 8889))
                print(f"> {cmd}")
            except Exception as e:
                QMessageBox.critical(self, "Drone", str(e))

    def start_auto_flight(self):
        if not self.app.drone_socket:
            QMessageBox.warning(self, "Error", "Drone not connected")
            return

        self.is_flying = True
        self.status_label.setText("Taking off…")
        self.start_recording()
        self.send_command("takeoff")
        time.sleep(4)
        self.execute_flight()

    def execute_flight(self):
        d_cm = int(self.distance * 100)
        self.send_command(f"forward {d_cm}")
        time.sleep(2 + d_cm / 100)

        self.send_command("left 180")
        time.sleep(3)

        self.send_command(f"forward {d_cm}")
        time.sleep(2 + d_cm / 100)

        self.send_command("land")
        time.sleep(3)

        self.is_flying = False
        self.stop_recording()

    def closeEvent(self, event):
        self.is_flying = False
        self.stop_recording()
        if self.video_thread:
            self.video_thread.stop()
        super().closeEvent(event)

# ----------------------------------------------------------------------
# Main App
# ----------------------------------------------------------------------
class CleanStreamsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clean Streams")
        self.setGeometry(100, 100, 1000, 700)
        self.username = ""
        self.battery_level = 0
        self.drone_socket = None
        self.stream_ready = False

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.stack.addWidget(SplashPage(self.stack))
        self.stack.addWidget(LoginPage(self.stack))

    def show_login(self):
        self.stack.setCurrentIndex(1)

    def show_connect_page(self, username):
        page = ConnectPage(self.stack, username)
        page.app = self
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)

    def show_homepage(self, username):
        page = Homepage(self.stack, username)
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)

    def show_route_page(self, flight_name, flight_notes):
        page = RoutePage(self.stack, flight_name, flight_notes)
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)

    def show_flight_page(self, flight_name, flight_notes, distance, start, end):
        self.stream_ready = True
        page = FlightPage(self.stack, flight_name, flight_notes, distance, start, end)
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)

# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)   # NOW DEFINED!
    win = CleanStreamsApp()
    win.show()
    sys.exit(app.exec_())