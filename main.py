import sys
import logging
import traceback
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from src.gui.main_window import MainWindow

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.log')


def exception_hook(exc_type, exc_value, exc_tb):
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    
    with open(log_file, 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"CRASH at {__import__('datetime').datetime.now()}\n")
        f.write(error_msg)
        f.write(f"{'='*60}\n")
    
    sys.stderr.write(f"\nCRASH:\n{error_msg}\n")
    sys.stderr.flush()
    
    try:
        QMessageBox.critical(
            None,
            "Application Error",
            f"The application crashed:\n\n{str(exc_value)}\n\nSee error.log for details."
        )
    except:
        pass
    
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def main():
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    sys.excepthook = exception_hook
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
