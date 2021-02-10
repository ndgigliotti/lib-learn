# Definitions - keep at project root level
from os import path

PROJECT_ROOT_DIR = path.dirname(path.abspath(__file__))
LOG_DIR = path.join(PROJECT_ROOT_DIR, 'logs')
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%dT%H-%M-%S"
