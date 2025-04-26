import shutil
import os
from pathlib import Path
import logging

# Custom filter to add user field to log records
class UserFilter(logging.Filter):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def filter(self, record):
        record.user = self.user_id
        return True

# Configure logging
USER_ID = "kill_switch_user"
logger = logging.getLogger('kill_switch')
logger.setLevel(logging.INFO)

# Create file handler
os.makedirs('logs', exist_ok=True)
file_handler = logging.FileHandler("logs/log.txt")
file_handler.setLevel(logging.INFO)

# Create formatter with the custom format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the custom filter to inject the user field
file_handler.addFilter(UserFilter(USER_ID))

# Add a stream handler for console output
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
stream_handler.addFilter(UserFilter(USER_ID))

# Add handlers to the logger
logger.handlers = []
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def activate_kill_switch():
    logger.info("Activating Kill Switch")
    directories = [
        Path("content/content_ready"),
        Path("logs"),
    ]
    
    # Delete contents of directories
    for directory in directories:
        if directory.exists() and directory.is_dir():
            for item in directory.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                        logger.info(f"Deleted file: {item}")
                    elif item.is_dir():
                        shutil.rmtree(item, ignore_errors=False, onerror=onerror_handler)
                        logger.info(f"Deleted subdirectory: {item}")
                except Exception as e:
                    logger.error(f"Failed to delete {item}: {e}")
        else:
            logger.warning(f"Directory does not exist or is not a directory: {directory}")

    # Delete specific files
    files_to_delete = [
        Path("content/scores.json"),
        Path("scheduler_db/scheduled_posts.db"),
    ]
    
    for file_path in files_to_delete:
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {e}")
        else:
            logger.warning(f"File does not exist: {file_path}")

def onerror_handler(func, path, exc_info):
    """
    Custom error handler for shutil.rmtree to handle permission issues.
    """
    import stat
    if isinstance(exc_info[1], PermissionError):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}. File may be in use by another process.")
    else:
        logger.error(f"Error deleting {path}: {exc_info[1]}")