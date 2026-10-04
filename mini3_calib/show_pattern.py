#!/usr/bin/env python3
"""Show the circle grid fullscreen and record its millimetre geometry."""

import argparse
import json
import os
from pathlib import Path

# Qt を XWayland 経由にし、xrandr の座標へ窓を移せるようにする。
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

import cv2

from pattern import COLS, ROWS, geometry, render

# USER_SETTINGS
DIAGONAL_IN = 27.0                      # モニタの対角（インチ）。27型フルHD
PANEL_WIDTH = 1920                      # パネルの幅（画素）。1920×1080
PANEL_HEIGHT = 1080                     # パネルの高さ（画素）。1920×1080
DISPLAY_NAME = "HDMI-1"                 # パターンを出す出力。ノート=eDP-1、モニタ=HDMI-1
GEOMETRY_JSON = "out/pattern.json"      # 間隔と画面サイズの書き出し先
WINDOW_TITLE = "mini3 circle grid"      # 全画面ウィンドウの名前
QUIT_KEY = "q"                          # 閉じるキー。Esc でも閉じる


def show_on_display(image, display_name):
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QImage, QPixmap
    from PyQt5.QtWidgets import QApplication, QLabel

    class PatternWindow(QLabel):
        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Escape or event.text() == QUIT_KEY:
                QApplication.quit()

    app = QApplication([])
    screen = next((item for item in app.screens() if item.name() == display_name), None)
    if screen is None:
        listed = ", ".join(item.name() for item in app.screens())
        raise SystemExit(f"出力 {display_name} が無い。接続中: {listed}")

    gray = image
    if not gray.flags["C_CONTIGUOUS"]:
        gray = gray.copy()
    qimage = QImage(gray.data, gray.shape[1], gray.shape[0], gray.shape[1], QImage.Format_Grayscale8)
    window = PatternWindow()
    window.setPixmap(QPixmap.fromImage(qimage.copy()))
    window.setAlignment(Qt.AlignCenter)
    window.setScaledContents(False)
    window.setStyleSheet("background-color: black;")
    window.setWindowTitle(WINDOW_TITLE)
    window.setWindowFlag(Qt.FramelessWindowHint, True)
    window.create()
    window.windowHandle().setScreen(screen)
    window.setGeometry(screen.geometry())
    window.showFullScreen()
    place = screen.geometry()
    print(f"display {screen.name()} at {place.x()},{place.y()}")
    print(f"fullscreen. {QUIT_KEY} or Esc closes it.")
    return app.exec_()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagonal-in", type=float, default=DIAGONAL_IN)
    parser.add_argument("--display", default=DISPLAY_NAME, help="xrandr output name")
    parser.add_argument("--width", type=int, default=PANEL_WIDTH, help="panel width in pixels")
    parser.add_argument("--height", type=int, default=PANEL_HEIGHT, help="panel height in pixels")
    parser.add_argument("--cols", type=int, default=COLS)
    parser.add_argument("--rows", type=int, default=ROWS)
    parser.add_argument(
        "--dump",
        type=Path,
        help="write the pattern image and exit without opening a window",
    )
    parser.add_argument(
        "--geometry",
        type=Path,
        default=Path(__file__).resolve().parent / GEOMETRY_JSON,
    )
    args = parser.parse_args()

    spec = geometry(args.width, args.height, args.diagonal_in, args.cols, args.rows)
    image, _ = render(spec)
    args.geometry.parent.mkdir(parents=True, exist_ok=True)
    args.geometry.write_text(json.dumps(spec, indent=2) + "\n")
    print(
        f"panel {spec['width_px']}x{spec['height_px']}  "
        f"{spec['width_mm']:.1f}x{spec['height_mm']:.1f} mm  "
        f"spacing {spec['spacing_mm']:.2f} mm  "
        f"diameter {2 * spec['radius_mm']:.2f} mm"
    )
    print(f"wrote {args.geometry}")

    if args.dump:
        args.dump.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.dump), image)
        print(f"wrote {args.dump}")
        return 0

    return show_on_display(image, args.display)


if __name__ == "__main__":
    raise SystemExit(main())
