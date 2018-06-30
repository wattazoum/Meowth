import sys
import logging
import logging.handlers


def init_loggers():
    # d.py stuff
    dpy_logger = logging.getLogger("discord")
    dpy_logger.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    dpy_logger.addHandler(console)

    # Meowth

    loglvl = logging.DEBUG

    logger = logging.getLogger("meowth")

    meowth_format = logging.Formatter(
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(meowth_format)
    logger.setLevel(loglvl)
    logger.addHandler(stdout_handler)

    logfile_path = 'logs/meowth.log'
    fhandler = logging.handlers.RotatingFileHandler(
        filename=str(logfile_path), encoding='utf-8', mode='a',
        maxBytes=400000, backupCount=20)
    fhandler.setFormatter(meowth_format)

    logger.addHandler(fhandler)

    return logger