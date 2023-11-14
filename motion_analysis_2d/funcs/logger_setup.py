import logging
import sys

from defs import log_file


def setup_logger(logging_level=logging.DEBUG):
    logging.TRACE = 5
    logging.addLevelName(logging.TRACE, "TRACE")
    logging.Logger.trace = lambda inst, msg, *args, **kwargs: inst.log(
        logging.trace, msg, *args, **kwargs
    )
    logging.trace = lambda msg, *args, **kwargs: logging.log(
        logging.TRACE, msg, *args, **kwargs
    )

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

    log_handler_stdout = logging.StreamHandler(sys.stdout)
    log_handler_stdout.setFormatter(formatter)

    log_handler_file = logging.FileHandler(log_file())
    log_handler_file.setFormatter(formatter)

    log = logging.getLogger()
    log.setLevel(logging_level)
    log.addHandler(log_handler_stdout)
    log.addHandler(log_handler_file)
