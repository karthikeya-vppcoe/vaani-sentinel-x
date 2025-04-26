import click
import os
import logging
from pathlib import Path
from agents import miner_sanitizer as sanitizer, ai_writer_voicegen as generator, security_guard as secure, publisher_sim as publisher, scheduler
from kill_switch import activate_kill_switch

# Custom filter to add user field to log records
class UserFilter(logging.Filter):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def filter(self, record):
        record.user = self.user_id
        return True

# Configure logging
logger = logging.getLogger('cli')
logger.setLevel(logging.INFO)

# Create file handler
os.makedirs('logs', exist_ok=True)
file_handler = logging.FileHandler("logs/cli.log")
file_handler.setLevel(logging.INFO)

# Create formatter with the custom format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)

# Add a stream handler for console output
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)

# Add handlers to the logger
logger.handlers = []
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

@click.group()
def cli():
    """Vaani Sentinel CLI for content processing pipeline."""
    pass

@cli.command()
def sanitize():
    """Sanitize raw content."""
    user = "agent_a_user"
    for handler in logger.handlers:
        handler.filters = [UserFilter(user)]
    logger.info("Starting sanitization")
    sanitizer.main()
    logger.info("Sanitization completed")

@cli.command()
def generate():
    """Generate content from sanitized data."""
    user = "agent_b_user"
    for handler in logger.handlers:
        handler.filters = [UserFilter(user)]
    logger.info("Starting content generation")
    generator.main()
    logger.info("Content generation completed")

@cli.command()
def secure():
    """Secure the generated content."""
    user = "agent_e_user"
    for handler in logger.handlers:
        handler.filters = [UserFilter(user)]
    logger.info("Starting content securing")
    secure.main()
    logger.info("Content securing completed")

@cli.command()
def schedule():
    """Schedule the content for publishing."""
    user = "agent_d_scheduler"
    for handler in logger.handlers:
        handler.filters = [UserFilter(user)]
    content_dir = Path("content/content_ready")
    logger.info(f"Running Scheduler with content directory: {content_dir}")
    scheduler.init_db()
    scheduler.schedule_content()
    logger.info("Scheduling completed")

@cli.command()
def publish():
    """Publish the scheduled content."""
    user = "agent_d_publisher"
    for handler in logger.handlers:
        handler.filters = [UserFilter(user)]
    logger.info("Running Publisher")
    publisher.run_publisher()
    logger.info("Publishing completed")

@cli.command()
def kill():
    """Wipe all generated data."""
    user = "kill_switch_user"
    for handler in logger.handlers:
        handler.filters = [UserFilter(user)]
    confirmation = input("Are you sure you want to wipe all data? This cannot be undone. [y/N]: ")
    if confirmation.lower() == "y":
        logger.info("Activating kill switch")
        activate_kill_switch()
        logger.info("Kill switch completed")
    else:
        logger.info("Kill switch aborted")

@cli.command()
def view_logs():
    """View system logs."""
    user = "cli_user"
    for handler in logger.handlers:
        handler.filters = [UserFilter(user)]
    log_file = Path("logs/cli.log")
    if log_file.exists():
        with open(log_file, 'r') as f:
            click.echo(f.read())
    else:
        click.echo("No logs found.")

@cli.command()
def view_alerts():
    """View security alerts."""
    user = "cli_user"
    for handler in logger.handlers:
        handler.filters = [UserFilter(user)]
    log_file = Path("logs/security.log")
    if log_file.exists():
        with open(log_file, 'r') as f:
            alerts = [line for line in f if "WARNING" in line and "Controversial content detected" in line]
            if alerts:
                for alert in alerts:
                    click.echo(alert)
            else:
                click.echo("No alerts found.")
    else:
        click.echo("No security logs found.")

@cli.command()
def status():
    """Check agent status."""
    user = "cli_user"
    for handler in logger.handlers:
        handler.filters = [UserFilter(user)]
    agents = [
        ("Agent A (Sanitizer)", Path("content/structured/content_blocks.json")),
        ("Agent B (Generator)", Path("content/content_ready")),
        ("Agent D (Scheduler)", Path("scheduler_db/scheduled_posts.db")),
        ("Agent D (Publisher)", Path("content/scores.json")),
        ("Agent E (Security)", Path("content/content_ready/encrypted.json")),
    ]
    for agent_name, output_path in agents:
        status = "Completed" if output_path.exists() else "Not run"
        click.echo(f"{agent_name}: {status}")

if __name__ == "__main__":
    cli()