# backend/utils/logger.py

import logging
import colorlog
import copy
import os
import sys
import asyncio
import json
from logging.handlers import RotatingFileHandler

# --- 1. Define the Handler ---
class WebSocketLogHandler(logging.Handler):
    """
    A custom logging handler that pushes logs to a WebSocket Manager.
    """
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        # We use a standard formatter for JSON serialization
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

    def emit(self, record):
        try:
            # Format the log message
            log_msg = self.formatter.format(record)
            
            # Construct a structured JSON packet for the dashboard
            packet = {
                "type": "log",
                "timestamp": record.asctime if hasattr(record, 'asctime') else "Now",
                "logger": record.name,
                "level": record.levelname,
                "message": record.getMessage() # Get the raw message (JSON payloads)
            }
            
            # Broadcast is async, so we create a task to run it without blocking
            if self.manager:
                asyncio.create_task(self.manager.broadcast(json.dumps(packet)))
                
        except Exception:
            self.handleError(record)

# --- 2. The Setup Function (Unchanged logic, just cleaner) ---
def setup_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
    try:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        sys.stderr.write(f"CRITICAL: Could not create log directory '{log_dir}'. Reason: {e}\n")
        raise

    # Console Formatter (Colors)
    color_formatter = colorlog.ColoredFormatter(
        '\033[2m[%(asctime)s]\033[0m - %(log_color)s%(name)s%(reset)s - %(log_color)s%(levelname)s%(reset)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',
        }
    )

    # Console Handler
    stream_handler = colorlog.StreamHandler()
    stream_handler.setFormatter(color_formatter)

    # File Handler
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.propagate = False 

    return logger




















# # File: backend/utils/logger.py

# import logging
# import colorlog
# import copy
# import os
# import sys
# from logging.handlers import RotatingFileHandler

# def setup_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
    
#     # --- 1. Robust Directory Creation ---
#     try:
#         log_dir = os.path.dirname(log_file)
#         if log_dir:
#             os.makedirs(log_dir, exist_ok=True)
#     except OSError as e:
#         sys.stderr.write(f"CRITICAL: Could not create log directory '{log_dir}'. Reason: {e}\n")
#         raise

#     # --- 2. Define Formatter ---
#     color_formatter = colorlog.ColoredFormatter(
#         '\033[2m[%(asctime)s]\033[0m - %(log_color)s%(name)s%(reset)s - %(log_color)s%(levelname)s%(reset)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S',
#         reset=True,
#         log_colors={
#             'DEBUG':    'cyan',
#             'INFO':     'green',
#             'WARNING':  'yellow',
#             'ERROR':    'red',
#             'CRITICAL': 'bold_red',
#         }
#     )

#     # --- 3. Custom Stream Handler ---
#     class CustomStreamHandler(colorlog.StreamHandler):
#         def emit(self, record):
#             try:
#                 cloned = copy.copy(record)
#                 # Check if running in a real terminal to apply colors
#                 is_tty = hasattr(self.stream, 'isatty') and self.stream.isatty()

#                 if is_tty:
#                     if record.levelno >= logging.WARNING:
#                         cloned.name = f'\033[1;5;32m{cloned.name}\033[0m'
#                         color_map = {logging.WARNING: '33', logging.ERROR: '31', logging.CRITICAL: '91'}
#                         color = color_map.get(record.levelno, '37')
#                         cloned.levelname = f'\033[1;5;{color}m{record.levelname}\033[0m'
#                         blinked_msg = f'\033[5m{cloned.getMessage()}\033[0m'
#                         if record.levelno >= logging.CRITICAL: 
#                             blinked_msg += '\a'
#                         cloned.msg = blinked_msg
#                         cloned.args = ()
#                     elif record.levelno == logging.DEBUG:
#                         cloned.msg = f'\033[2m{cloned.getMessage()}\033[0m'
#                         cloned.args = ()
#                 super().emit(cloned)
#             except Exception:
#                 self.handleError(record)

#     # --- 4. Setup Handlers ---
#     stream_handler = CustomStreamHandler()
#     stream_handler.setFormatter(color_formatter)

#     # Rotating File Handler (Max 5MB)
#     file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
#     file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

#     logger = logging.getLogger(name)
#     logger.setLevel(level)

#     if logger.hasHandlers():
#         logger.handlers.clear()

#     logger.addHandler(stream_handler)
#     logger.addHandler(file_handler)
#     logger.propagate = False 

#     return logger



# # --- EXAMPLE USAGE ---
# if __name__ == "__main__":
#     # This logger will automatically create the 'mind/logs' directories if they don't exist
#     engine_logger = setup_logger(
#         "ReactiveEngine",
#         log_file="mind/logs/reactive_analytic_engine.log",
#         level=logging.DEBUG
#     )

#     engine_logger.debug("This is a faint debug message.")
#     engine_logger.info("Engine has started successfully.")
#     engine_logger.warning("Cache is running low on memory.")
#     engine_logger.error("Failed to connect to the database.")
#     engine_logger.critical("Core process has crashed. System is unstable.")

#     # Example of a logger writing to the local directory
#     local_logger = setup_logger("LocalTest", log_file="local_test.log")
#     local_logger.info("This log goes to a local file.")









































# import logging
# import colorlog
# import copy

# def setup_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
#     """Set up a logger with faint timestamp, blinking bold light green name (console only), and clean file output."""

#     color_formatter = colorlog.ColoredFormatter(
#         '\033[2m[%(asctime)s]\033[22m - %(log_color)s%(name)s%(reset)s - %(log_color)s%(levelname)s%(reset)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S',
#         reset=True,
#         log_colors={
#             'DEBUG':    'cyan',
#             'INFO':     'green',
#             'WARNING':  'yellow',
#             'ERROR':    'red',
#             'CRITICAL': 'bold_red',
#         }
#     )

#     class CustomStreamHandler(colorlog.StreamHandler):
#         def emit(self, record):
#             cloned = copy.copy(record)

#             if record.levelno >= logging.WARNING:
#                 # Blink + bold + light green name
#                 cloned.name = f'\033[1;5;32m{cloned.name}\033[25m\033[22m\033[39m'

#                 # Blink level name with color
#                 color = {
#                     logging.WARNING:  '33',  # Yellow
#                     logging.ERROR:    '31',  # Red
#                     logging.CRITICAL: '91'   # Bright Red
#                 }.get(record.levelno, '37')

#                 cloned.levelname = f'\033[1;5;{color}m{record.levelname}\033[25m\033[22m\033[39m'

#                 # Blink the message
#                 blinked_msg = f'\033[5m{cloned.getMessage()}\033[25m'

#                 # Add a beep if ERROR or CRITICAL
#                 if record.levelno >= logging.ERROR:
#                     blinked_msg += '\a'  # Terminal beep

#                 cloned.msg = blinked_msg
#                 cloned.args = ()

#             elif record.levelno == logging.DEBUG:
#                 # Make the DEBUG message faint (dim)
#                 faint_msg = f'\033[2m{cloned.getMessage()}\033[22m'
#                 cloned.msg = faint_msg
#                 cloned.args = ()

#             else:
#                 cloned.name = f'{cloned.name}'

#             super().emit(cloned)

#     stream_handler = CustomStreamHandler()
#     stream_handler.setFormatter(color_formatter)

#     file_handler = logging.FileHandler(log_file)
#     file_handler.setFormatter(logging.Formatter(
#         '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S'
#     ))

#     logger = colorlog.getLogger(name)
#     logger.setLevel(level)
#     logger.handlers.clear()
#     logger.addHandler(stream_handler)
#     logger.addHandler(file_handler)

#     return logger
































# Need to make the Debug level faded
# import logging
# import colorlog
# import copy

# def setup_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
#     """Set up a logger with faint timestamp, blinking bold light green name (console only), and clean file output."""

#     color_formatter = colorlog.ColoredFormatter(
#         '\033[2m[%(asctime)s]\033[22m - %(log_color)s%(name)s%(reset)s - %(log_color)s%(levelname)s%(reset)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S',
#         reset=True,
#         log_colors={
#             'DEBUG':    'cyan',
#             'INFO':     'green',
#             'WARNING':  'yellow',
#             'ERROR':    'red',
#             'CRITICAL': 'bold_red',
#         }
#     )

#     class CustomStreamHandler(colorlog.StreamHandler):
#         def emit(self, record):
#             cloned = copy.copy(record)

#             if record.levelno >= logging.WARNING:
#                 # Blink + bold + light green name
#                 cloned.name = f'\033[1;5;32m{cloned.name}\033[25m\033[22m\033[39m'

#                 # Blink level name with color
#                 color = {
#                     logging.WARNING:  '33',  # Yellow
#                     logging.ERROR:    '31',  # Red
#                     logging.CRITICAL: '91'   # Bright Red
#                 }.get(record.levelno, '37')

#                 cloned.levelname = f'\033[1;5;{color}m{record.levelname}\033[25m\033[22m\033[39m'

#                 # Blink the message
#                 blinked_msg = f'\033[5m{cloned.getMessage()}\033[25m'

#                 # Add a beep if ERROR or CRITICAL
#                 if record.levelno >= logging.ERROR:
#                     blinked_msg += '\a'  # Terminal beep

#                 cloned.msg = blinked_msg
#                 cloned.args = ()
#             else:
#                 cloned.name = f'{cloned.name}'

#             super().emit(cloned)


#     stream_handler = CustomStreamHandler()
#     stream_handler.setFormatter(color_formatter)

#     file_handler = logging.FileHandler(log_file)
#     file_handler.setFormatter(logging.Formatter(
#         '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S'
#     ))

#     logger = colorlog.getLogger(name)
#     logger.setLevel(level)
#     logger.handlers.clear()
#     logger.addHandler(stream_handler)
#     logger.addHandler(file_handler)

#     return logger


    # class CustomStreamHandler(colorlog.StreamHandler):
    #     def emit(self, record):
    #         cloned = copy.copy(record)
    #         cloned.name = f'\033[1;5;32m{cloned.name}\033[25m\033[22m\033[39m'  # Bold + blink + light green
    #         super().emit(cloned)
    
    # class CustomStreamHandler(colorlog.StreamHandler):
    #     def emit(self, record):
    #         cloned = copy.copy(record)

    #         if record.levelno >= logging.WARNING:
    #             # Blink + bold + light green for the logger name
    #             cloned.name = f'\033[1;5;32m{cloned.name}\033[25m\033[22m\033[39m'

    #             # Blink level name based on severity color
    #             color = {
    #                 logging.WARNING: '33',   # Yellow
    #                 logging.ERROR:   '31',   # Red
    #                 logging.CRITICAL: '91'   # Bright Red
    #             }.get(record.levelno, '37')

    #             cloned.levelname = f'\033[1;5;{color}m{record.levelname}\033[25m\033[22m\033[39m'

    #             # Blink the message
    #             cloned.msg = f'\033[5m{cloned.getMessage()}\033[25m'
    #             cloned.args = ()
    #         else:
    #             cloned.name = f'{cloned.name}'

    #         super().emit(cloned)
























# import logging
# import colorlog

# def setup_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
#     """Set up a logger with colored level names, a colored logger name, and a faint timestamp."""

#     # Color formatter with faint timestamp and colored logger name + level
#     color_formatter = colorlog.ColoredFormatter(
#         '\033[2m[%(asctime)s]\033[22m - %(log_color)s%(name)s%(reset)s - %(log_color)s%(levelname)s%(reset)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S',
#         reset=True,
#         log_colors={
#             'DEBUG':    'cyan',
#             'INFO':     'green',
#             'WARNING':  'yellow',
#             'ERROR':    'red',
#             'CRITICAL': 'bold_red',
#         }
#     )


#     # Custom stream handler with blinking bold light green name
#     class CustomStreamHandler(colorlog.StreamHandler):
#         def emit(self, record):
#             record.name = f'\033[1;5;32m{record.name}\033[25m\033[22m\033[39m'  # Bold + blink + light green
#             super().emit(record)
            
            
#     # Console handler
#     stream_handler = CustomStreamHandler()
#     stream_handler.setFormatter(color_formatter)

#     # File handler (plain, no colors)
#     file_handler = logging.FileHandler(log_file)
#     file_handler.setFormatter(logging.Formatter(
#         '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S'
#     ))

#     # Create and configure logger
#     logger = colorlog.getLogger(name)
#     logger.setLevel(level)
#     logger.handlers.clear()  # Avoid duplicate logs
#     logger.addHandler(stream_handler)
#     logger.addHandler(file_handler)

#     return logger








































# import logging
# import colorlog

# def setup_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
#     """Set up a logger with colored level names and a custom-colored logger name, and log to both console and file."""

#     # Color formatter with custom colored logger name
#     color_formatter = colorlog.ColoredFormatter(
#         '[%(asctime)s] - %(log_color)s%(name)s%(reset)s - %(log_color)s%(levelname)s%(reset)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S',
#         reset=True,
#         log_colors={
#             'DEBUG':    'cyan',
#             'INFO':     'green',
#             'WARNING':  'yellow',
#             'ERROR':    'red',
#             'CRITICAL': 'bold_red',
#         }
#     )

#     # Custom stream handler to color the logger name
#     class CustomStreamHandler(colorlog.StreamHandler):
#         def emit(self, record):
#             record.name = f'\033[2m{record.name}\033[39m'  # Blue color for logger name
#             super().emit(record)

#     # Console handler
#     stream_handler = CustomStreamHandler()
#     stream_handler.setFormatter(color_formatter)

#     # File handler (plain, no colors)
#     file_handler = logging.FileHandler(log_file)
#     file_handler.setFormatter(logging.Formatter(
#         '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S'
#     ))

#     # Create and configure logger
#     logger = colorlog.getLogger(name)
#     logger.setLevel(level)
#     logger.handlers.clear()  # Avoid duplicate logs
#     logger.addHandler(stream_handler)
#     logger.addHandler(file_handler)

#     return logger








































# import logging
# import colorlog

# def setup_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
#     """Set up a logger with colored level names only, and log to both console and file."""
    
#     # Color only the LEVELNAME
#     color_formatter = colorlog.ColoredFormatter(
#         '[%(asctime)s] - %(name)s - %(log_color)s%(levelname)s%(reset)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S',
#         reset=True,
#         log_colors={
#             'DEBUG':    'cyan',
#             'INFO':     'green',
#             'WARNING':  'yellow',
#             'ERROR':    'red',
#             'CRITICAL': 'bold_red',
#         }
#     )

#     # Console handler
#     stream_handler = colorlog.StreamHandler()
#     stream_handler.setFormatter(color_formatter)

#     # File handler (plain)
#     file_handler = logging.FileHandler(log_file)
#     file_handler.setFormatter(logging.Formatter(
#         '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S'
#     ))

#     # Create and configure logger
#     logger = colorlog.getLogger(name)
#     logger.setLevel(level)
#     logger.handlers.clear()  # Avoid duplicate logs
#     logger.addHandler(stream_handler)
#     logger.addHandler(file_handler)

#     return logger









































# import logging
# import colorlog

# def setup_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
#     """Set up a logger with colored console output and file logging.

#     Args:
#         name (str): Name of the logger.
#         log_file (str): File to log to. Defaults to 'app.log'.
#         level (int): Logging level. Defaults to logging.INFO.

#     Returns:
#         logging.Logger: Configured logger instance.
#     """
#     # Colored formatter for console output
#     color_formatter = colorlog.ColoredFormatter(
#         '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S',
#         reset=True,
#         log_colors={
#             'DEBUG':    'cyan',
#             'INFO':     'green',
#             'WARNING':  'yellow',
#             'ERROR':    'red',
#             'CRITICAL': 'bold_red',
#         }
#     )

#     # Create handlers
#     stream_handler = colorlog.StreamHandler()
#     stream_handler.setFormatter(color_formatter)

#     file_handler = logging.FileHandler(log_file)
#     file_handler.setFormatter(logging.Formatter(
#         '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S'
#     ))

#     # Set up logger
#     logger = colorlog.getLogger(name)
#     logger.setLevel(level)
#     logger.handlers = []  # Clear existing handlers
#     logger.addHandler(stream_handler)
#     logger.addHandler(file_handler)

#     return logger
