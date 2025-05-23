import os
import sys
import logging
import subprocess
from datetime import datetime
import signal
from typing import Dict, Optional, List, Tuple

# Logging setup for Command Center
USER_ID = 'command_center_user'
logger = logging.getLogger('command_center')
logger.setLevel(logging.INFO)
os.makedirs('../logs', exist_ok=True)
file_handler = logging.FileHandler('../logs/command_center.txt', encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler]

# Process tracking
active_processes: Dict[str, subprocess.Popen] = {}

# Agent configuration
AGENTS = {
    'miner_sanitizer': {
        'name': 'Knowledge Miner & Sanitizer',
        'path': '../agents/miner_sanitizer.py'
    },
    'multilingual_pipeline': {
        'name': 'Multilingual Pipeline',
        'path': '../agents/multilingual_pipeline.py'
    },
    'sentiment_tuner': {
        'name': 'Sentiment Tuner',
        'path': '../agents/sentiment_tuner.py'
    },
    'ai_writer_voicegen': {
        'name': 'AI Writer & Voice Generator',
        'path': '../agents/ai_writer_voicegen.py'
    },
    'adaptive_targeter': {
        'name': 'Adaptive Targeter',
        'path': '../agents/adaptive_targeter.py'
    },
    'scheduler': {
        'name': 'Scheduler',
        'path': '../agents/scheduler.py'
    },
    'publisher_sim': {
        'name': 'Publisher Simulator',
        'path': '../agents/publisher_sim.py'
    },
    'security_guard': {
        'name': 'Security Guard',
        'path': '../agents/security_guard.py'
    }
}

# Pipeline definition
PIPELINE: List[Tuple[str, str]] = [
    ("miner_sanitizer", "Agent A: Miner & Sanitizer"),
    ("multilingual_pipeline", "Agent F: Multilingual Router"),
    ("sentiment_tuner", "Agent H: Sentiment Tuner"),
    ("ai_writer_voicegen", "Agent G: AI Writer & Voice Generator"),
    ("security_guard", "Agent E: Security & Compliance"),
    ("adaptive_targeter", "Agent I: Context-Aware Platform Targeter"),
    ("scheduler", "Agent D: Scheduler"),
    ("publisher_sim", "Agent D: Publisher Simulator")
]

# Track active pipelines (language-specific)
active_pipelines: Dict[str, List[str]] = {}

# Allowed sentiments for sentiment_tuner
ALLOWED_SENTIMENTS = ['uplifting', 'neutral', 'devotional']
ALLOWED_LANGUAGES = ['en', 'hi', 'sa', 'all']

# Paths to validate
CONTENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'content', 'content_ready'))
SCHEDULER_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scheduler_db'))

def validate_environment() -> bool:
    """Validate that required directories exist."""
    if not os.path.exists(CONTENT_DIR):
        logger.error(f"Content directory not found: {CONTENT_DIR}")
        print(f"Error: Content directory not found: {CONTENT_DIR}")
        return False
    if not os.path.exists(SCHEDULER_DB_DIR):
        logger.warning(f"Scheduler DB directory not found, creating: {SCHEDULER_DB_DIR}")
        os.makedirs(SCHEDULER_DB_DIR, exist_ok=True)
    return True

def run_agent(agent: str, language: Optional[str] = None, sentiment: Optional[str] = None) -> subprocess.Popen:
    """Run a single agent and return the process."""
    if agent not in AGENTS:
        logger.error(f"Unknown agent: {agent}")
        raise ValueError(f"Unknown agent: {agent}")

    try:
        cmd = [sys.executable, AGENTS[agent]['path']]
        # Add arguments for specific agents
        if agent in ['multilingual_pipeline', 'scheduler', 'ai_writer_voicegen', 'sentiment_tuner', 'security_guard', 'adaptive_targeter', 'publisher_sim'] and language:
            cmd.append(language)  # Pass language as a positional argument
        if agent in ['sentiment_tuner', 'ai_writer_voicegen'] and sentiment:
            cmd.extend(['--sentiment', sentiment])  # Pass sentiment as a flag

        logger.info(f"Executing command: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"Started {AGENTS[agent]['name']} (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"Error running {AGENTS[agent]['name']}: {str(e)}")
        raise

def run_pipeline(language: str, sentiment: str = 'uplifting') -> None:
    """Run the pipeline for a specific language with the given sentiment."""
    if not validate_environment():
        return

    pipeline_key = f"pipeline_{language}"
    if pipeline_key in active_pipelines:
        logger.warning(f"Pipeline for language '{language}' is already running")
        print(f"Pipeline for language '{language}' is already running. Use 'kill-pipeline' to stop it.")
        return

    active_pipelines[pipeline_key] = []
    logger.info(f"Starting pipeline for language: {language} with sentiment: {sentiment}")
    print(f"Starting pipeline for language: {language} with sentiment: {sentiment}")

    try:
        for agent_id, agent_name in PIPELINE:
            print(f"Running {agent_name} for language {language}...")
            logger.info(f"Running {agent_name} for language {language}...")
            # Run the agent with appropriate arguments
            process = run_agent(
                agent_id,
                language=language if agent_id in ['multilingual_pipeline', 'scheduler', 'ai_writer_voicegen', 'sentiment_tuner', 'security_guard', 'adaptive_targeter', 'publisher_sim'] else None,
                sentiment=sentiment if agent_id in ['sentiment_tuner', 'ai_writer_voicegen'] else None
            )
            active_processes[agent_id] = process
            active_pipelines[pipeline_key].append(agent_id)

            # Monitor process output and wait for completion
            stdout, stderr = process.communicate()
            if stdout:
                logger.info(stdout.strip())
                print(stdout.strip())
            if stderr:
                logger.error(stderr.strip())
                print(f"Error: {stderr.strip()}")

            if process.returncode != 0:
                logger.error(f"{agent_name} failed with code {process.returncode}")
                print(f"Error: {agent_name} failed with code {process.returncode}")
                raise RuntimeError(f"Pipeline failed at {agent_name}")
            else:
                logger.info(f"{agent_name} completed successfully")
                print(f"{agent_name} completed successfully")

            # Clean up process tracking for this agent
            if agent_id in active_processes:
                del active_processes[agent_id]

        logger.info(f"Pipeline for language {language} completed successfully")
        print(f"Pipeline for language {language} completed successfully")

    except Exception as e:
        logger.error(f"Pipeline for language {language} failed: {str(e)}")
        print(f"Pipeline for language {language} failed: {str(e)}")
        raise
    finally:
        if pipeline_key in active_pipelines:
            del active_pipelines[pipeline_key]

def view_logs(agent: Optional[str] = None) -> None:
    """View logs for specific agent or all agents."""
    log_dir = '../logs'
    if not os.path.exists(log_dir):
        logger.error("No logs directory found")
        print("No logs directory found")
        return

    if agent:
        if agent not in AGENTS:
            logger.error(f"Unknown agent: {agent}")
            print(f"Unknown agent: {agent}")
            return
        log_file = os.path.join(log_dir, f"{agent}.txt")
        if not os.path.exists(log_file):
            logger.warning(f"No log file found for {AGENTS[agent]['name']}")
            print(f"No log file found for {AGENTS[agent]['name']}")
            return
        with open(log_file, 'r', encoding='utf-8') as f:
            print(f"\n=== Logs for {AGENTS[agent]['name']} ===")
            print(f.read())
    else:
        for log_file in os.listdir(log_dir):
            if log_file.endswith('.txt') or log_file.endswith('.log'):
                print(f"\n=== {log_file} ===")
                with open(os.path.join(log_dir, log_file), 'r', encoding='utf-8') as f:
                    print(f.read())

def kill_process(agent: str) -> None:
    """Kill a running agent process."""
    if agent not in active_processes:
        logger.warning(f"No active process found for {AGENTS.get(agent, {}).get('name', agent)}")
        print(f"No active process found for {AGENTS.get(agent, {}).get('name', agent)}")
        return

    process = active_processes[agent]
    try:
        process.terminate()
        process.wait(timeout=5)
        logger.info(f"Terminated {AGENTS[agent]['name']}")
        print(f"Terminated {AGENTS[agent]['name']}")
    except subprocess.TimeoutExpired:
        process.kill()
        logger.info(f"Forcefully killed {AGENTS[agent]['name']}")
        print(f"Forcefully killed {AGENTS[agent]['name']}")
    except Exception as e:
        logger.error(f"Error killing process: {str(e)}")
        print(f"Error killing process: {str(e)}")
    finally:
        if agent in active_processes:
            del active_processes[agent]

def kill_pipeline(language: str) -> None:
    """Kill all running agents in a pipeline for a specific language."""
    pipeline_key = f"pipeline_{language}"
    if pipeline_key not in active_pipelines:
        logger.warning(f"No active pipeline found for language {language}")
        print(f"No active pipeline found for language {language}")
        return

    for agent_id in active_pipelines[pipeline_key]:
        if agent_id in active_processes:
            kill_process(agent_id)

    logger.info(f"Pipeline for language {language} has been terminated")
    print(f"Pipeline for language {language} has been terminated")
    del active_pipelines[pipeline_key]

def restart_agent(agent: str, sentiment: str = 'uplifting') -> None:
    """Restart a running agent by killing and then running it again."""
    if agent not in AGENTS:
        logger.error(f"Unknown agent: {agent}")
        print(f"Unknown agent: {agent}")
        return

    # Kill the agent if it's running
    if agent in active_processes:
        logger.info(f"Restarting {AGENTS[agent]['name']}...")
        print(f"Restarting {AGENTS[agent]['name']}...")
        kill_process(agent)
    else:
        logger.info(f"{AGENTS[agent]['name']} is not running, starting it...")
        print(f"{AGENTS[agent]['name']} is not running, starting it...")

    # Run the agent
    run_agent(agent, sentiment=sentiment if agent == 'sentiment_tuner' else None)

def restart_pipeline(language: str, sentiment: str = 'uplifting') -> None:
    """Restart the pipeline for a specific language."""
    pipeline_key = f"pipeline_{language}"
    if pipeline_key in active_pipelines:
        logger.info(f"Restarting pipeline for language {language}...")
        print(f"Restarting pipeline for language {language}...")
        kill_pipeline(language)
    else:
        logger.info(f"No pipeline running for language {language}, starting it...")
        print(f"No pipeline running for language {language}, starting it...")

    run_pipeline(language, sentiment)

def list_agents() -> None:
    """List all available agents and their status."""
    print("Available Agents:")
    for agent_id, agent in AGENTS.items():
        status = "RUNNING" if agent_id in active_processes else "IDLE"
        print(f"  {agent_id}: {agent['name']} [{status}]")
    print("\nActive Pipelines:")
    if active_pipelines:
        for pipeline_key in active_pipelines:
            language = pipeline_key.replace("pipeline_", "")
            running_agents = active_pipelines[pipeline_key]
            print(f"  Language: {language} [RUNNING] - Agents: {', '.join(running_agents)}")
    else:
        print("  No active pipelines.")

def main() -> None:
    """Main function for Command Center CLI."""
    if len(sys.argv) < 2:
        print("Command Center CLI for Vaani Sentinel X")
        print("Usage: python command_center.py <command> [arguments]")
        print("\nAvailable Commands:")
        print("  run <agent> [--sentiment <sentiment>]\n    Run a specific agent manually.")
        print("    - Supported agents:", ", ".join(AGENTS.keys()))
        print("    - --sentiment: Optional for sentiment_tuner/ai_writer_voicegen (values: uplifting, neutral, devotional)")
        print("  run-pipeline <language> [--sentiment <sentiment>]\n    Run the full pipeline for a language.")
        print("    - Supported languages: en, hi, sa, all")
        print("    - --sentiment: Optional (values: uplifting, neutral, devotional)")
        print("  logs [agent]\n    View logs for a specific agent or all agents if no agent specified.")
        print("  kill <agent>\n    Kill a running agent.")
        print("  kill-pipeline <language>\n    Kill a running pipeline for a specific language.")
        print("  restart <agent> [--sentiment <sentiment>]\n    Restart a specific agent.")
        print("  restart-pipeline <language> [--sentiment <sentiment>]\n    Restart the pipeline for a specific language.")
        print("  list\n    List all agents and active pipelines with their status.")
        print("\nExample Usage:")
        print("  python command_center.py run miner_sanitizer")
        print("  python command_center.py run-pipeline en --sentiment neutral")
        print("  python command_center.py logs adaptive_targeter")
        print("  python command_center.py kill scheduler")
        print("  python command_center.py kill-pipeline en")
        print("  python command_center.py restart sentiment_tuner --sentiment devotional")
        print("  python command_center.py restart-pipeline hi")
        print("  python command_center.py list")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'run' and len(sys.argv) > 2:
        agent = sys.argv[2]
        sentiment = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '--sentiment' else 'uplifting'
        if agent not in AGENTS:
            print(f"Invalid agent: {agent}. Supported agents: {', '.join(AGENTS.keys())}")
            sys.exit(1)
        if agent == 'sentiment_tuner' and sentiment not in ALLOWED_SENTIMENTS:
            print(f"Invalid sentiment: {sentiment}. Supported sentiments: {', '.join(ALLOWED_SENTIMENTS)}")
            sys.exit(1)
        run_agent(agent, sentiment=sentiment if agent == 'sentiment_tuner' else None)
    elif command == 'run-pipeline' and len(sys.argv) > 2:
        language = sys.argv[2]
        sentiment = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '--sentiment' else 'uplifting'
        if language not in ALLOWED_LANGUAGES:
            print(f"Invalid language: {language}. Supported languages: {', '.join(ALLOWED_LANGUAGES)}")
            sys.exit(1)
        if sentiment not in ALLOWED_SENTIMENTS:
            print(f"Invalid sentiment: {sentiment}. Supported sentiments: {', '.join(ALLOWED_SENTIMENTS)}")
            sys.exit(1)
        run_pipeline(language, sentiment)
    elif command == 'logs':
        agent = sys.argv[2] if len(sys.argv) > 2 else None
        view_logs(agent)
    elif command == 'kill' and len(sys.argv) > 2:
        agent = sys.argv[2]
        if agent not in AGENTS:
            print(f"Invalid agent: {agent}. Supported agents: {', '.join(AGENTS.keys())}")
            sys.exit(1)
        kill_process(agent)
    elif command == 'kill-pipeline' and len(sys.argv) > 2:
        language = sys.argv[2]
        if language not in ALLOWED_LANGUAGES:
            print(f"Invalid language: {language}. Supported languages: {', '.join(ALLOWED_LANGUAGES)}")
            sys.exit(1)
        kill_pipeline(language)
    elif command == 'restart' and len(sys.argv) > 2:
        agent = sys.argv[2]
        sentiment = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '--sentiment' else 'uplifting'
        if agent not in AGENTS:
            print(f"Invalid agent: {agent}. Supported agents: {', '.join(AGENTS.keys())}")
            sys.exit(1)
        if agent == 'sentiment_tuner' and sentiment not in ALLOWED_SENTIMENTS:
            print(f"Invalid sentiment: {sentiment}. Supported sentiments: {', '.join(ALLOWED_SENTIMENTS)}")
            sys.exit(1)
        restart_agent(agent, sentiment)
    elif command == 'restart-pipeline' and len(sys.argv) > 2:
        language = sys.argv[2]
        sentiment = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '--sentiment' else 'uplifting'
        if language not in ALLOWED_LANGUAGES:
            print(f"Invalid language: {language}. Supported languages: {', '.join(ALLOWED_LANGUAGES)}")
            sys.exit(1)
        if sentiment not in ALLOWED_SENTIMENTS:
            print(f"Invalid sentiment: {sentiment}. Supported sentiments: {', '.join(ALLOWED_SENTIMENTS)}")
            sys.exit(1)
        restart_pipeline(language, sentiment)
    elif command == 'list':
        list_agents()
    else:
        print("Invalid command or missing arguments. Run without arguments to see usage.")
        sys.exit(1)

if __name__ == "__main__":
    main()