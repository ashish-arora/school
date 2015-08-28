import os
import logging
import logging.handlers

BASIC_LOG_FORMAT = "%(asctime)s:[%(levelname)s]:[%(name)s]: %(message)s"
TIME_FORMAT = "%d/%b/%Y:%H:%M:%S"

'''
Class: Logger,  meant to return logger for each file
'''

LOGGING_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

class Logger:

    @staticmethod
    def get_logger(name=None):
        if name:
            name = os.path.splitext(os.path.basename(name))[0]
        logger = logging.getLogger(name)
        logger.setLevel(LOGGING_LEVELS.get(os.environ.get("LOG_LEVEL"), logging.DEBUG))
        formatter = logging.Formatter(BASIC_LOG_FORMAT, TIME_FORMAT)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

if __name__=="__main__":
    Logger.get_logger()

