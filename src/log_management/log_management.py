import logging
import logging.config

from src.log_management.config import get_app_config_parameters


class CorrIdFilter(logging.Filter):
    """
    A simple log filter to ensure corr-id is populated
    """

    def filter(self, record):
        record.corrId = (
            record.args.get("corrId") if "corrId" in record.args else "no-corr"
        )
        return True


def configure_logger(arg_log_config_file: str) -> None:
    """
    Create logger from logging configuration file.
    """
    try:
        log_config = get_app_config_parameters(arg_log_config_file)
        logging.config.dictConfig(log_config)
        logger = logging.getLogger()
        logger.info("Log file creation done. Put a lot of log!")
    except Exception as ex:
        raise RuntimeError("Error creating logging configuration:", ex)
