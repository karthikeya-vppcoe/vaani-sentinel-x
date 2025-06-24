import json
import os
import logging
import glob
import random
from datetime import datetime
from typing import Dict, List

# Logging setup for Agent K (Analytics Collector)
USER_ID = 'agent_k_user'
logger = logging.getLogger('analytics_collector')
logger.setLevel(logging.INFO)
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(log_dir, 'analytics_collector.txt'), encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler, logging.StreamHandler()]
logger.info("Initializing analytics_collector.py")

def generate_engagement_stats(platform: str, language: str, tone: str) -> Dict:
    """Generate realistic dummy engagement stats."""
    ranges = {
        'instagram': {'likes': (100, 500), 'comments': (10, 50), 'shares': (20, 100), 'views': (500, 2000)},
        'twitter': {'likes': (20, 100), 'retweets': (10, 50), 'quotes': (5, 20), 'views': (200, 1000)},
        'linkedin': {'likes': (50, 300), 'comments': (10, 40), 'shares': (10, 50), 'views': (300, 1500)},
        'sanatan': {'likes': (50, 200), 'comments': (5, 30), 'shares': (10, 50), 'views': (200, 1000)}
    }
    stats = ranges.get(platform, ranges['instagram'])
    multiplier = 1.2 if tone == 'uplifting' and language in ['hi', 'sa'] else 1.0

    return {
        'likes': int(random.uniform(*stats.get('likes', (0, 0))) * multiplier),
        'comments': int(random.uniform(*stats.get('comments', (0, 0))) * multiplier),
        'shares': int(random.uniform(*stats.get('shares', (0, 0))) * multiplier),
        'views': int(random.uniform(*stats.get('views', (0, 0))) * multiplier),
        'retweets': int(random.uniform(*stats.get('retweets', (0, 0))) * multiplier) if platform == 'twitter' else 0,
        'quotes': int(random.uniform(*stats.get('quotes', (0, 0))) * multiplier) if platform == 'twitter' else 0
    }

def run_analytics_collector(input_dir: str, output_dir: str, languages: List[str] = ['en', 'hi', 'sa']) -> None:
    """Run Agent K: Analytics Collector."""
    logger.info(f"Starting Agent K: Analytics Collector for languages: {languages}")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, 'post_metrics.json')
    if os.path.exists(output_path):
        os.remove(output_path)
        logger.info(f"Cleared post_metrics.json: {output_path}")

    metrics = []
    for file_path in glob.glob(os.path.join(input_dir, '*.json')):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = json.load(f)
            if post.get('status') not in ['success', 'published']:
                logger.info(f"Skipping post {post.get('post_id', 'unknown')} (status: {post.get('status')})")
                continue
            post_id = post.get('post_id', 'unknown')
            content_id = post.get('content_id', 'unknown')
            platform = post.get('platform', 'unknown')
            language = post.get('language', 'en')
            if language not in languages:
                logger.info(f"Skipping post {post_id} (language {language} not in {languages})")
                continue
            tone = post.get('tone', 'neutral')
            content_type = 'voice_script' if platform == 'sanatan' else 'post'

            stats = generate_engagement_stats(platform, language, tone)
            metric = {
                'post_id': post_id,
                'content_id': content_id,
                'platform': platform,
                'language': language,
                'tone': tone,
                'content_type': content_type,
                'timestamp': datetime.now().isoformat(),
                'stats': stats
            }
            metrics.append(metric)
            logger.info(f"Generated stats for post ID {post_id} (content ID: {content_id}, platform: {platform}, lang: {language})")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(metrics)} metrics to {output_path}")

if __name__ == "__main__":
    input_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scheduled_posts')
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'analytics_db')
    run_analytics_collector(input_dir, output_dir)