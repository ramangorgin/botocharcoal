# app/core/logging.py - Add or update this file
import logging
import sys

def setup_logging():
    """Configure logging for the application"""

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # Set specific loggers
    logging.getLogger('app.services.ai_service').setLevel(logging.DEBUG)
    logging.getLogger('app.tasks.generate_post').setLevel(logging.DEBUG)

    # Reduce noise from other libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return root_logger

# Call setup when module is imported
logger = setup_logging()
