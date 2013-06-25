import logging
import sys

import colorama
from colorama import Fore, Back, Style

LEVEL_COLOR_MAPPING = {
    logging.DEBUG: Style.BRIGHT + Fore.BLUE + Back.RESET,
    logging.INFO: Style.BRIGHT + Fore.GREEN + Back.RESET,
    logging.WARNING: Style.BRIGHT + Fore.YELLOW + Back.RESET,
    logging.ERROR: Style.BRIGHT + Fore.RED + Back.RESET,
    logging.CRITICAL: Style.BRIGHT + Fore.WHITE + Back.RED,
}
 

class SystemExitLoggingHandler(logging.Handler):
    """Buffer the logging records and send email digests."""
    exit_level = logging.ERROR

    def emit(self, record):
        """Quit the application if the record level is high."""
        if record.levelno >= self.exit_level:
            raise SystemExit(1)


class ColoredFormatter(logging.Formatter):
    def __init__(self, fmt=None):
        datefmt='%d-%m-%Y %I:%M:%S %p'
        logging.Formatter.__init__(self, fmt, datefmt=datefmt)
        self._fmt = self._fmt.replace('%(levelname)s', '%(coloredlevel)s')
 
    def format(self, record):
        record.coloredlevel = (LEVEL_COLOR_MAPPING.get(record.levelno, '') +
                               record.levelname + Style.RESET_ALL)
        return logging.Formatter.format(self, record)


def init_logger(level=logging.INFO):
    # Prepare the logging handler with a custom formatter
    fmt = '%(asctime)s %(levelname)s: %(message)s'
    formatter = ColoredFormatter(fmt)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Special handler for Exit
    exit_handler = SystemExitLoggingHandler()

    # Configure the root logger
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.addHandler(exit_handler)
    logger.setLevel(level)
 
 
# Initialize
colorama.init()
init_logger(level=logging.DEBUG)