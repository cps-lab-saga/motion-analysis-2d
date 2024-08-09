import logging
import sys

from motion_analysis_2d.defs import log_file

# add trace level
logging.TRACE = 5
logging.addLevelName(logging.TRACE, "TRACE")
logging.Logger.trace = lambda inst, msg, *args, **kwargs: inst.log(
    logging.trace, msg, *args, **kwargs
)
logging.trace = lambda msg, *args, **kwargs: logging.log(
    logging.TRACE, msg, *args, **kwargs
)


def setup_logger(name, logging_level=logging.INFO):
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s")

    logger = logging.getLogger(name)
    logger.setLevel(logging_level)

    log_handler_stdout = logging.StreamHandler(sys.stdout)
    log_handler_stdout.setFormatter(formatter)
    logger.addHandler(log_handler_stdout)

    log_handler_file = logging.FileHandler(log_file())
    log_handler_file.setFormatter(formatter)
    logger.addHandler(log_handler_file)

    return logger
