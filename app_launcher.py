import sys
import os
import threading
import webbrowser
import time

# PyInstaller 번들 실행 시 경로 설정
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    os.chdir(bundle_dir)

def open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8051")

if __name__ == '__main__':
    threading.Thread(target=open_browser, daemon=True).start()

    from protogen_univ_dash import app
    app.run(debug=False, port=8051)
