import os
import sys
import logging
import subprocess
import json
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple

# Add utils and config to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import get_config
from utils.common import setup_logger, HealthChecker, validate_input, get_timestamp

# Initialize configuration and logging
config = get_config()
USER_ID = 'command_center_user'
logger = setup_logger('command_center', USER_ID)

# Process tracking
active_processes: Dict[str, subprocess.Popen] = {}
active_pipelines: Dict[str, List[str]] = {}

# Agent configuration - now using config system
def get_agent_paths() -> Dict[str, Dict[str, str]]:
    """Get agent paths from configuration."""
    base_path = config.get_absolute_path('agents')
    return {
        'miner_sanitizer': {'name': 'Knowledge Miner & Sanitizer', 'path': str(base_path / 'miner_sanitizer.py')},
        'multilingual_pipeline': {'name': 'Multilingual Pipeline', 'path': str(base_path / 'multilingual_pipeline.py')},
        'translation_agent': {'name': 'Translator', 'path': str(base_path / 'translation_agent.py')},
        'personalization_agent': {'name': 'Personalizer', 'path': str(base_path / 'personalization_agent.py')},
        'sentiment_tuner': {'name': 'Sentiment Tuner', 'path': str(base_path / 'sentiment_tuner.py')},
        'ai_writer_voicegen': {'name': 'AI Writer & Voice Generator', 'path': str(base_path / 'ai_writer_voicegen.py')},
        'tts_simulator': {'name': 'TTS Simulator', 'path': str(base_path / 'tts_simulator.py')},
        'security_guard': {'name': 'Security Guard', 'path': str(base_path / 'security_guard.py')},
        'adaptive_targeter': {'name': 'Adaptive Targeter', 'path': str(base_path / 'adaptive_targeter.py')},
        'publisher_sim': {'name': 'Publisher Simulator', 'path': str(base_path / 'publisher_sim.py')},
        'analytics_collector': {'name': 'Analytics Collector', 'path': str(base_path / 'analytics_collector.py')},
        'strategy_recommender': {'name': 'Strategy Recommender', 'path': str(base_path / 'strategy_recommender.py')},
        'scheduler': {'name': 'Scheduler', 'path': str(base_path / 'scheduler.py')},
        'language_mapper': {'name': 'Language Mapper', 'path': str(base_path / 'language_mapper.py')},
        'simulate_translation': {'name': 'Simulated Translation Generator', 'path': str(base_path / 'simulate_translation.py')}
    }

AGENTS = get_agent_paths()

# Pipeline definition
PIPELINE: List[Tuple[str, str]] = [
    ("miner_sanitizer", "Agent A: Miner & Sanitizer"),
    ("multilingual_pipeline", "Agent F: Multilingual Router"),
    ("translation_agent", "Agent T: Translator"),
    ("personalization_agent", "Agent P: Personalizer"),
    ("sentiment_tuner", "Agent H: Sentiment Tuner"),
    ("ai_writer_voicegen", "Agent G: AI Writer & Voice Generator"),
    ("tts_simulator", "Agent V: TTS Simulator"),
    ("security_guard", "Agent E: Security & Compliance"),
    ("adaptive_targeter", "Agent I: Context-Aware Platform Targeter"),
    ("publisher_sim", "Agent J: Publisher Simulator"),
    ("analytics_collector", "Agent K: Analytics Collector"),
    ("strategy_recommender", "Agent R: Strategy Recommender"),
    ("scheduler", "Agent D: Scheduler"),
    ("language_mapper", "Helper: Language Mapper"),
    ("simulate_translation", "Helper: Simulated Translation Generator")
]

# Use configuration for allowed parameters
ALLOWED_SENTIMENTS = config.agents.supported_sentiments
ALLOWED_LANGUAGES = config.agents.supported_languages
ALLOWED_PLATFORMS = config.agents.supported_platforms

# Paths
CONTENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'content_ready')
SCHEDULER_DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'scheduler_db')
ANALYTICS_DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'analytics_db')
RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'raw')

def validate_environment() -> bool:
    """Validate required directories and configuration."""
    try:
        # Use health checker for comprehensive validation
        health_checker = HealthChecker()
        health_status = health_checker.full_health_check()
        
        # Check dependencies
        missing_deps = [dep for dep, status in health_status['dependencies'].items() if not status]
        if missing_deps:
            logger.error(f"Missing dependencies: {missing_deps}")
            return False
        
        # Check directories
        missing_dirs = [dir_name for dir_name, status in health_status['directories'].items() if not status]
        if missing_dirs:
            logger.warning(f"Missing directories (will be created): {missing_dirs}")
        
        # Create directories using config
        config._create_directories()
        
        logger.info("Environment validation completed successfully")
        return True
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        return False

def run_agent(agent: str, languages: Optional[List[str]] = None, sentiment: Optional[str] = None, platform: Optional[str] = None, content_id: Optional[str] = None, input_file: Optional[str] = None) -> subprocess.Popen:
    """Run a single agent."""
    if agent not in AGENTS:
        logger.error(f"Unknown agent: {agent}")
        raise ValueError(f"Unknown agent: {agent}")
    
    if not os.path.exists(AGENTS[agent]['path']):
        logger.error(f"Agent file not found: {AGENTS[agent]['path']}")
        raise FileNotFoundError(f"Agent file not found: {AGENTS[agent]['path']}")
    
    cmd = [sys.executable, AGENTS[agent]['path']]
    if agent == 'miner_sanitizer':
        if input_file:
            cmd.extend(['--input', input_file])
        if languages:
            cmd.extend(['--languages'] + languages)
        if platform:
            cmd.extend(['--platforms', platform])
        if sentiment:
            cmd.extend(['--sentiment', sentiment])
    elif agent == 'multilingual_pipeline':
        if languages:
            cmd.extend(['--languages'] + languages)
        if platform:
            cmd.extend(['--platforms', platform])
        if sentiment:
            cmd.extend(['--sentiment', sentiment])
    elif agent == 'translation_agent':
        if content_id:
            cmd.extend(['--content_id', content_id])
        if platform:
            cmd.extend(['--platform', platform])
    
    logger.info(f"Executing command: {' '.join(cmd)}")
    try:
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

def run_pipeline(languages: List[str], sentiment: str = 'neutral', platform: str = None, content_id: str = None, input_file: str = None) -> None:
    """Run the pipeline for specified languages."""
    if not validate_environment():
        return
    
    pipeline_key = f"pipeline_{'_'.join(languages)}_{platform}_{content_id}" if platform and content_id else f"pipeline_{'_'.join(languages)}"
    if pipeline_key in active_pipelines:
        logger.warning(f"Pipeline {pipeline_key} is already running")
        print(f"Pipeline {pipeline_key} is already running")
        return
    
    active_pipelines[pipeline_key] = []
    logger.info(f"Starting pipeline: {pipeline_key} (sentiment: {sentiment})")
    print(f"Starting pipeline: {pipeline_key} (sentiment: {sentiment})")
    
    try:
        for agent_id, agent_name in PIPELINE:
            print(f"Running {agent_name}...")
            logger.info(f"Running {agent_name}...")
            process = run_agent(
                agent_id,
                languages=languages if languages != ['all'] else ALLOWED_LANGUAGES,
                sentiment=sentiment,
                platform=platform,
                content_id=content_id,
                input_file=input_file
            )
            active_processes[agent_id] = process
            active_pipelines[pipeline_key].append(agent_id)
            
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
            
            if agent_id in active_processes:
                del active_processes[agent_id]
        
        logger.info(f"Pipeline {pipeline_key} completed successfully")
        print(f"Pipeline {pipeline_key} completed successfully")
    
    except Exception as e:
        logger.error(f"Pipeline {pipeline_key} failed: {str(e)}")
        print(f"Pipeline {pipeline_key} failed: {str(e)}")
        raise
    finally:
        if pipeline_key in active_pipelines:
            del active_pipelines[pipeline_key]

def view_logs(agent: Optional[str] = None) -> None:
    """View logs for an agent or all agents."""
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
            logger.warning(f"No log file for {AGENTS[agent]['name']}")
            print(f"No log file for {AGENTS[agent]['name']}")
            return
        with open(log_file, 'r', encoding='utf-8') as f:
            print(f"\n=== Logs for {AGENTS[agent]['name']} ===")
            print(f.read())
    else:
        for log_file in os.listdir(log_dir):
            if log_file.endswith('.txt'):
                print(f"\n=== {log_file} ===")
                with open(os.path.join(log_dir, log_file), 'r', encoding='utf-8') as f:
                    print(f.read())

def view_alerts() -> None:
    """View security alerts."""
    alerts_path = os.path.join(log_dir, 'alert_dashboard.json')
    try:
        if os.path.exists(alerts_path):
            with open(alerts_path, 'r', encoding='utf-8') as f:
                alerts = json.load(f)
            print("\n=== Security Alerts ===")
            for a in alerts:
                print(f"ID: {a['content_id']} | Platform: {a['platform']} | Lang: {a['language']}")
                print(f"Reason: {a['reason']}")
                print(f"Snippet: {a['snippet']}")
                print("-" * 50)
        else:
            print("No alerts found")
    except Exception as e:
        logger.error(f"Failed to view alerts: {str(e)}")
        print(f"Error: Failed to view alerts: {str(e)}")

def kill_process(agent: str) -> None:
    """Kill a running agent process."""
    if agent not in active_processes:
        logger.warning(f"No active process for {AGENTS.get(agent, {}).get('name', agent)}")
        print(f"No active process for {AGENTS.get(agent, {}).get('name', agent)}")
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
    finally:
        if agent in active_processes:
            del active_processes[agent]

def kill_pipeline(languages: List[str], platform: str = None, content_id: str = None) -> None:
    """Kill a running pipeline."""
    pipeline_key = f"pipeline_{'_'.join(languages)}_{platform}_{content_id}" if platform and content_id else f"pipeline_{'_'.join(languages)}"
    if pipeline_key not in active_pipelines:
        logger.warning(f"No active pipeline for {pipeline_key}")
        print(f"No active pipeline for {pipeline_key}")
        return
    
    for agent_id in active_pipelines[pipeline_key]:
        if agent_id in active_processes:
            kill_process(agent_id)
    
    logger.info(f"Pipeline {pipeline_key} terminated")
    print(f"Pipeline {pipeline_key} terminated")
    del active_pipelines[pipeline_key]

def view_analytics() -> None:
    """View engagement metrics."""
    metrics_path = config.get_absolute_path(f"{config.database.analytics_db_dir}/post_metrics.json")
    try:
        if metrics_path.exists():
            with open(metrics_path, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            print("\n=== Engagement Metrics ===")
            for m in metrics:
                print(f"ID: {m['content_id']} | Platform: {m['platform']} | Lang: {m['lang']}")
                print(f"Content: {m['content']}")
                print(f"Stats: {m['stats']}")
                print(f"Performance: {m['performance']} | Sentiment: {m['sentiment']}")
                print("-" * 50)
        else:
            print("No metrics found")
    except Exception as e:
        logger.error(f"Failed to view analytics: {str(e)}")
        print(f"Error: Failed to view analytics: {str(e)}")

def view_suggestions() -> None:
    """View strategy suggestions."""
    suggestions_path = config.get_absolute_path(f"{config.database.analytics_db_dir}/strategy_suggestions.json")
    try:
        if suggestions_path.exists():
            with open(suggestions_path, 'r', encoding='utf-8') as f:
                suggestions = json.load(f)
            print("\n=== Strategy Suggestions ===")
            for s in suggestions:
                print(f"Platform: {s['platform']} | Lang: {s['lang']}")
                print(f"Suggestion: {s['suggestion']}")
                print(f"Basis: {s['basis']}")
                print("-" * 50)
        else:
            print("No suggestions found")
    except Exception as e:
        logger.error(f"Failed to view suggestions: {str(e)}")
        print(f"Error: Failed to view suggestions: {str(e)}")

def health_check() -> None:
    """Perform comprehensive health check of the system."""
    print("\n=== Vaani Sentinel X Health Check ===")
    print(f"Timestamp: {get_timestamp()}")
    print(f"Environment: {config.environment}")
    
    try:
        health_checker = HealthChecker()
        health_status = health_checker.full_health_check()
        
        # Dependencies check
        print("\n--- Dependencies Status ---")
        for dep, status in health_status['dependencies'].items():
            status_str = "✓ OK" if status else "✗ MISSING"
            print(f"  {dep}: {status_str}")
        
        # Directories check
        print("\n--- Directories Status ---")
        for dir_name, status in health_status['directories'].items():
            status_str = "✓ OK" if status else "✗ MISSING"
            print(f"  {dir_name}: {status_str}")
        
        # Configuration files check
        print("\n--- Configuration Files ---")
        for file_name, status in health_status['config_files'].items():
            status_str = "✓ OK" if status else "✗ MISSING"
            print(f"  {file_name}: {status_str}")
        
        # API Keys check (without exposing values)
        print("\n--- API Keys Status ---")
        api_status = {
            'GROQ_API_KEY': bool(config.apis.groq_api_key),
            'GOOGLE_API_KEY': bool(config.apis.google_api_key),
            'JWT_SECRET': bool(config.security.jwt_secret),
            'SECRET_KEY': bool(config.web.secret_key),
        }
        for key, status in api_status.items():
            status_str = "✓ SET" if status else "✗ NOT SET"
            print(f"  {key}: {status_str}")
        
        # Overall status
        overall_ok = (
            all(health_status['dependencies'].values()) and
            all(health_status['directories'].values()) and
            all(health_status['config_files'].values())
        )
        
        print(f"\n--- Overall Status ---")
        print(f"System Status: {'✓ HEALTHY' if overall_ok else '✗ ISSUES DETECTED'}")
        
        if not overall_ok:
            print("\nRecommendations:")
            if not all(health_status['dependencies'].values()):
                print("  - Install missing dependencies: pip install -r requirements-minimal.txt")
            if not all(health_status['config_files'].values()):
                print("  - Copy .env.template to .env and configure required settings")
            if not config.apis.groq_api_key:
                print("  - Set GROQ_API_KEY in .env for AI functionality")
            if not config.security.jwt_secret:
                print("  - Set JWT_SECRET in .env for security")
        
        return overall_ok
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        print(f"Health check failed: {e}")
        return False

def restart_agent(agent: str, languages: List[str] = None, sentiment: str = 'neutral', platform: str = None, content_id: str = None, input_file: str = None) -> None:
    """Restart an agent."""
    if agent not in AGENTS:
        logger.error(f"Unknown agent: {agent}")
        print(f"Unknown agent: {agent}")
        return
    
    if agent in active_processes:
        logger.info(f"Restarting {AGENTS[agent]['name']}...")
        print(f"Restarting {AGENTS[agent]['name']}...")
        kill_process(agent)
    else:
        logger.info(f"Starting {AGENTS[agent]['name']}...")
        print(f"Starting {AGENTS[agent]['name']}...")
    
    run_agent(agent, languages, sentiment, platform, content_id, input_file)

def restart_pipeline(languages: List[str], sentiment: str = 'neutral', platform: str = None, content_id: str = None, input_file: str = None) -> None:
    """Restart a pipeline."""
    pipeline_key = f"pipeline_{'_'.join(languages)}_{platform}_{content_id}" if platform and content_id else f"pipeline_{'_'.join(languages)}"
    if pipeline_key in active_pipelines:
        logger.info(f"Restarting pipeline {pipeline_key}...")
        print(f"Restarting pipeline {pipeline_key}...")
        kill_pipeline(languages, platform, content_id)
    else:
        logger.info(f"Starting pipeline {pipeline_key}...")
        print(f"Starting pipeline {pipeline_key}...")
    
    run_pipeline(languages, sentiment, platform, content_id, input_file)

def list_agents() -> None:
    """List agents and pipelines."""
    print("Available Agents:")
    for agent_id, agent in AGENTS.items():
        status = "RUNNING" if agent_id in active_processes else "IDLE"
        print(f"  {agent_id}: {agent['name']} [{status}]")
    print("\nActive Pipelines:")
    if active_pipelines:
        for pipeline_key in active_pipelines:
            print(f"  {pipeline_key}: Agents: {', '.join(active_pipelines[pipeline_key])}")
    else:
        print("  No active pipelines")

def main() -> None:
    """Main CLI function."""
    if len(sys.argv) < 2:
        print("Vaani Sentinel X Command Center CLI")
        print("Usage: python command_center.py <command> [arguments]")
        print("\nCommands:")
        print("  run <agent> [--languages <lang1 lang2 ...>] [--sentiment <sentiment>] [--platform <platform>] [--content_id <id>] [--input <file>]\n    Run an agent")
        print("  run-pipeline [--languages <lang1 lang2 ...>] [--sentiment <sentiment>] [--platform <platform>] [--content_id <id>] [--input <file>]\n    Run pipeline")
        print("  logs [agent]\n    View logs")
        print("  view-alerts\n    View security alerts")
        print("  kill <agent>\n    Kill an agent")
        print("  kill-pipeline <lang1 lang2 ...> [--platform <platform>] [--content_id <id>]\n    Kill a pipeline")
        print("  restart <agent> [--languages <lang1 lang2 ...>] [--sentiment <sentiment>] [--platform <platform>] [--content_id <id>] [--input <file>]\n    Restart an agent")
        print("  restart-pipeline [--languages <lang1 lang2 ...>] [--sentiment <sentiment>] [--platform <platform>] [--content_id <id>] [--input <file>]\n    Restart a pipeline")
        print("  collect-analytics\n    Run analytics and view metrics")
        print("  suggest-strategy\n    Run strategy recommender and view suggestions")
        print("  health\n    Perform system health check")
        print("  list\n    List agents and pipelines")
        print("\nParameters:")
        print(f"  Languages: {', '.join(ALLOWED_LANGUAGES)}")
        print(f"  Sentiments: {', '.join(ALLOWED_SENTIMENTS)}")
        print(f"  Platforms: {', '.join(ALLOWED_PLATFORMS)}")
        print("  Input: Path to input file (for miner_sanitizer)")
        print("\nExamples:")
        print("  python command_center.py run miner_sanitizer --languages en hi sa --sentiment uplifting --platform instagram --input ../content/raw/sample.csv")
        print("  python command_center.py run-pipeline --languages en hi sa --sentiment devotional --platform sanatan")
        print("  python command_center.py logs translation_agent")
        print("  python command_center.py view-alerts")
        print("  python command_center.py kill sentiment_tuner")
        print("  python command_center.py kill-pipeline en hi --platform instagram")
        print("  python command_center.py restart translation_agent --content_id 1 --platform linkedin")
        print("  python command_center.py restart-pipeline --languages sa hi --sentiment neutral --input ../content/raw/sample.csv")
        print("  python command_center.py collect-analytics")
        print("  python command_center.py suggest-strategy")
        print("  python command_center.py list")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    params = {}
    i = 0
    while i < len(args):
        if args[i].startswith('--'):
            if i + 1 < len(args) and not args[i + 1].startswith('--'):
                param_values = []
                j = i + 1
                while j < len(args) and not args[j].startswith('--'):
                    param_values.append(args[j])
                    j += 1
                params[args[i][2:]] = param_values if len(param_values) > 1 else param_values[0]
                i = j
            else:
                print(f"Missing value for {args[i]}")
                sys.exit(1)
        else:
            params['agent' if command in ['run', 'kill', 'restart'] else 'languages'] = args[i].split() if command == 'run-pipeline' else [args[i]]
            i += 1
    
    if command == 'run':
        agent = params.get('agent', [''])[0]
        if not agent or agent not in AGENTS:
            print(f"Invalid agent. Supported: {', '.join(AGENTS.keys())}")
            sys.exit(1)
        languages = params.get('languages', params.get('language', ALLOWED_LANGUAGES))
        if isinstance(languages, str):
            languages = [languages]
        if languages and any(lang not in ALLOWED_LANGUAGES for lang in languages):
            print(f"Invalid language(s). Supported: {', '.join(ALLOWED_LANGUAGES)}")
            sys.exit(1)
        sentiment = params.get('sentiment', 'neutral')
        if sentiment not in ALLOWED_SENTIMENTS:
            print(f"Invalid sentiment. Supported: {', '.join(ALLOWED_SENTIMENTS)}")
            sys.exit(1)
        platform = params.get('platform')
        if platform and platform not in ALLOWED_PLATFORMS:
            print(f"Invalid platform. Supported: {', '.join(ALLOWED_PLATFORMS)}")
            sys.exit(1)
        run_agent(
            agent,
            languages,
            sentiment,
            platform,
            params.get('content_id'),
            params.get('input')
        )
    elif command == 'run-pipeline':
        languages = params.get('languages', ALLOWED_LANGUAGES)
        if isinstance(languages, str):
            languages = [languages]
        if not languages or any(lang not in ALLOWED_LANGUAGES for lang in languages):
            print(f"Invalid language(s). Supported: {', '.join(ALLOWED_LANGUAGES)}")
            sys.exit(1)
        sentiment = params.get('sentiment', 'neutral')
        if sentiment not in ALLOWED_SENTIMENTS:
            print(f"Invalid sentiment. Supported: {', '.join(ALLOWED_SENTIMENTS)}")
            sys.exit(1)
        platform = params.get('platform')
        if platform and platform not in ALLOWED_PLATFORMS:
            print(f"Invalid platform. Supported: {', '.join(ALLOWED_PLATFORMS)}")
            sys.exit(1)
        run_pipeline(
            languages,
            sentiment,
            platform,
            params.get('content_id'),
            params.get('input')
        )
    elif command == 'logs':
        view_logs(params.get('agent', [''])[0])
    elif command == 'view-alerts':
        view_alerts()
    elif command == 'kill':
        agent = params.get('agent', [''])[0]
        if not agent or agent not in AGENTS:
            print(f"Invalid agent. Supported: {', '.join(AGENTS.keys())}")
            sys.exit(1)
        kill_process(agent)
    elif command == 'kill-pipeline':
        languages = params.get('languages', [])
        if isinstance(languages, str):
            languages = [languages]
        if not languages or any(lang not in ALLOWED_LANGUAGES for lang in languages):
            print(f"Invalid language(s). Supported: {', '.join(ALLOWED_LANGUAGES)}")
            sys.exit(1)
        kill_pipeline(
            languages,
            params.get('platform'),
            params.get('content_id')
        )
    elif command == 'restart':
        agent = params.get('agent', [''])[0]
        if not agent or agent not in AGENTS:
            print(f"Invalid agent. Supported: {', '.join(AGENTS.keys())}")
            sys.exit(1)
        languages = params.get('languages', params.get('language', ALLOWED_LANGUAGES))
        if isinstance(languages, str):
            languages = [languages]
        if languages and any(lang not in ALLOWED_LANGUAGES for lang in languages):
            print(f"Invalid language(s). Supported: {', '.join(ALLOWED_LANGUAGES)}")
            sys.exit(1)
        sentiment = params.get('sentiment', 'neutral')
        if sentiment not in ALLOWED_SENTIMENTS:
            print(f"Invalid sentiment. Supported: {', '.join(ALLOWED_SENTIMENTS)}")
            sys.exit(1)
        platform = params.get('platform')
        if platform and platform not in ALLOWED_PLATFORMS:
            print(f"Invalid platform. Supported: {', '.join(ALLOWED_PLATFORMS)}")
            sys.exit(1)
        restart_agent(
            agent,
            languages,
            sentiment,
            platform,
            params.get('content_id'),
            params.get('input')
        )
    elif command == 'restart-pipeline':
        languages = params.get('languages', ALLOWED_LANGUAGES)
        if isinstance(languages, str):
            languages = [languages]
        if not languages or any(lang not in ALLOWED_LANGUAGES for lang in languages):
            print(f"Invalid language(s). Supported: {', '.join(ALLOWED_LANGUAGES)}")
            sys.exit(1)
        sentiment = params.get('sentiment', 'neutral')
        if sentiment not in ALLOWED_SENTIMENTS:
            print(f"Invalid sentiment. Supported: {', '.join(ALLOWED_SENTIMENTS)}")
            sys.exit(1)
        platform = params.get('platform')
        if platform and platform not in ALLOWED_PLATFORMS:
            print(f"Invalid platform. Supported: {', '.join(ALLOWED_PLATFORMS)}")
            sys.exit(1)
        restart_pipeline(
            languages,
            sentiment,
            platform,
            params.get('content_id'),
            params.get('input')
        )
    elif command == 'collect-analytics':
        run_agent('analytics_collector')
        view_analytics()
    elif command == 'suggest-strategy':
        run_agent('strategy_recommender')
        view_suggestions()
    elif command == 'health':
        health_check()
    elif command == 'list':
        list_agents()
    else:
        print("Invalid command")
        sys.exit(1)

if __name__ == "__main__":
    main()