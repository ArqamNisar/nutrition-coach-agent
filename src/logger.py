import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger with the specified name configured with StreamHandler and RotatingFileHandler.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if the logger is retrieved multiple times
    if not logger.handlers:
        # Determine the root directory and create the logs folder
        root_dir = Path(__file__).resolve().parent.parent
        log_dir = root_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / "app.log"
        
        # Format for logs
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Rotating File Handler
        try:
            file_handler = RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Failed to setup file logging to {log_file}: {e}", file=sys.stderr)
            
    return logger
