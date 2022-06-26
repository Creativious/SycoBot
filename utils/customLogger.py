import time
import colorlog
import logging


class Logger:
    def __init__(self, name: str, subname: str, debug: bool = False):
        self.name = name
        self.subname = subname
        self.format = f'%(levelname)s [%(asctime)s] ({subname}) %(message)s'
        # logging.basicConfig(filename=f"logs/logs.log", encoding="utf-8", datefmt='%m/%d/%Y %H:%m:%S', format=self.format)
        self.handler = colorlog.StreamHandler()
        self.fileHandler = logging.FileHandler(filename=f"logs/{name}.log", encoding="utf-8")
        self.fileHandler.setFormatter(logging.Formatter(self.format, datefmt='%m/%d/%Y %H:%m:%S'))
        self.allFileHandler = logging.FileHandler(filename=f"logs/all_logs.log", encoding="utf-8")
        self.allFileHandler.setFormatter(logging.Formatter(f'%(levelname)s [%(asctime)s] ({name}:{subname}) %(message)s', datefmt='%m/%d/%Y %H:%m:%S'))
        self.handler.setFormatter(colorlog.ColoredFormatter(f"%(log_color)s %(levelname)s [%(asctime)s] ({name}:{subname}) %(message)s", datefmt='%m/%d/%Y %H:%m:%S'))
        self.debug = debug
        self.__logger = logging.getLogger(name)
        self.__logger.addHandler(self.handler)
        self.__logger.addHandler(self.fileHandler)
        self.__logger.addHandler(self.allFileHandler)
        if debug:
            self.__logger.setLevel(colorlog.DEBUG)
        else:
            self.__logger.setLevel(colorlog.INFO)

    def getLogger(self):
        return self.__logger
        
