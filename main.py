import sys
import asyncio
import qasync
from src.ui.view.main_window_view import MainWindow
from PySide6.QtWidgets import QApplication

def main():
    print("Hello from pdf-trans!")
    app = QApplication(sys.argv)

    # qasync를 사용하여 Qt 이벤트 루프와 asyncio 이벤트 루프를 통합합니다.
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    # 통합된 asyncio 이벤트 루프를 실행합니다.
    with loop:
        sys.exit(loop.run_forever())

if __name__ == "__main__":
    main()
