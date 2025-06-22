import sys
from src.ui.main_window_view import MainWindow
from PySide6.QtWidgets import QApplication

def main():
    print("Hello from pdf-trans!")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
