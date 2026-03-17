import logging


def get_logger(name: str, **kwargs) -> logging.Logger:
    """
    This function returns a logger object with a custom formatter.
    """
    import colorlog

    logger = logging.getLogger(name)

    # Remove propagation of messages to the parent loggers
    logger.propagate = False

    message_format = kwargs.get(
        "message_format",
        "%(log_color)s%(asctime)s - %(levelname)s - %(name)s - Line %(lineno)d - %(message)s",
    )
    datefmt = kwargs.get("datefmt", "%Y-%m-%d %H:%M:%S")
    log_colors = kwargs.get(
        "log_colors",
        {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )

    # Create a color formatter
    formatter = colorlog.ColoredFormatter(
        message_format,
        datefmt=datefmt,
        log_colors=log_colors,
    )

    # Create a console handler and set the formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)

    # Set the logging level based on kwargs or default to INFO
    logger.setLevel(kwargs.get("level", logging.INFO))

    return logger
