# Definitions - keep at project root level
from os import path

PROJECT_ROOT_DIR = path.dirname(path.abspath(__file__))
LOG_DIR = path.join(PROJECT_ROOT_DIR, 'logs')
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%dT%H-%M-%S"

STDLIB = ("abc", "aifc", "argparse", "ast", "asynchat", "asyncio",
          "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
          "binhex", "bisect", "builtins", "bz2", "cProfile", "calendar",
          "cgi", "cgitb", "cmath", "code", "codecs", "codeop",
          "collections", "colorsys", "compileall", "contextlib", "copy",
          "copyreg", "csv", "ctypes", "dbm", "decimal", "difflib", "dis",
          "doctest", "dummy_threading", "email", "encodings", "ensurepip",
          "enum", "faulthandler", "filecmp", "fileinput", "fnmatch",
          "formatter", "fractions", "ftplib", "functools", "gc",
          "genericpath", "getopt", "getpass", "gettext", "glob", "gzip",
          "hashlib", "heapq", "hmac", "html", "imaplib", "imghdr", "imp",
          "importlib", "inspect", "io", "ipaddress", "itertools", "json",
          "keyword", "linecache", "locale", "logging", "lzma", "macpath",
          "macurl2path", "mailcap", "marshal", "math", "mimetypes",
          "modulefinder", "msilib", "msvcrt", "multiprocessing", "nntplib",
          "ntpath", "nturl2path", "numbers", "opcode", "operator",
          "optparse", "os", "parser", "pathlib", "pdb", "pickle",
          "pickletools", "pipes", "pkgutil", "platform", "plistlib",
          "posixpath", "pprint", "profile", "pstats", "py_compile",
          "pyclbr", "pydoc", "pyexpat", "queue", "quopri", "random", "re",
          "readline", "reprlib", "rlcompleter", "runpy", "sched",
          "secrets", "select", "selectors", "shelve", "shlex", "shutil",
          "signal", "site", "smtpd", "smtplib", "sndhdr", "socket",
          "socketserver", "sqlite3", "sre_compile", "sre_parse", "ssl",
          "stat", "statistics", "string", "stringprep", "struct",
          "subprocess", "sunau", "symtable", "sys", "sysconfig",
          "tabnanny", "tarfile", "telnetlib", "tempfile", "textwrap",
          "threading", "time", "timeit", "tkinter", "token", "tokenize",
          "trace", "traceback", "tracemalloc", "turtle", "types", "typing",
          "unicodedata", "unittest", "uu", "uuid", "venv", "warnings",
          "wave", "weakref", "winreg", "winsound", "xdrlib", "xxsubtype",
          "zipapp", "zipfile", "zlib")
