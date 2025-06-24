import json
import os
import logging
from typing import Dict, List

# Logging setup for Agent R: Strategy Recommender
USER_ID = 'agent_r_user'
logger = logging.getLogger('strategy_recommender')
logger.setLevel(logging.INFO)
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(log_dir, 'strategy_recommender.txt'), encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler, logging.StreamHandler()]
logger.info("Initializing strategy_recommender.py")

def calculate_score(stats: Dict) -> float:
    """Calculate a weighted score for a post."""
    weights = {
        'likes': 0.5,
        'shares': 0.3,
        'comments': 0.2,
        'retweets': 0.3,
        'quotes': 0.2,
        'views': 0.1
    }
    return sum(stats.get(key, 0) * weight for key, weight in weights.items())

def adjust_future_content_strategy(input_path: str, output_path: str, languages: List[str] = ['en', 'hi', 'sa']) -> None:
    """Run Agent R: Strategy Recommender for Weekly Adaptive Hook."""
    logger.info(f"Starting Agent R: Strategy Recommender for languages: {languages}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Clear weekly_strategy_recommendation.json
    if os.path.exists(output_path):
        os.remove(output_path)
        logger.info(f"Cleared weekly_strategy_recommendation.json: {output_path}")

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            metrics = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {input_path}: {str(e)}")
        return

    # Filter by supported languages
    metrics = [m for m in metrics if m.get('language') in languages]
    if not metrics:
        logger.warning(f"No metrics found for languages {languages}")
        return

    # Calculate scores
    scored_metrics = []
    for metric in metrics:
        score = calculate_score(metric['stats'])
        metric['score'] = score
        scored_metrics.append(metric)

    scored_metrics.sort(key=lambda x: x['score'], reverse=True)
    top_performers = scored_metrics[:3]
    underperformers = scored_metrics[-3:] if len(scored_metrics) >= 3 else scored_metrics

    suggestions = []
    for metric in top_performers:
        content_type = metric.get('content_type', 'post')
        suggestions.append({
            'type': 'high-performing',
            'platform': metric['platform'],
            'language': metric['language'],
            'tone': metric['tone'],
            'content_type': content_type,
            'content_id': metric['content_id'],
            'score': metric['score'],
            'message': f"Increase {metric['tone']} {metric['language']} {content_type} content on {metric['platform']} for better engagement."
        })
    for metric in underperformers:
        content_type = metric.get('content_type', 'post')
        suggestions.append({
            'type': 'underperforming',
            'platform': metric['platform'],
            'language': metric['language'],
            'tone': metric['tone'],
            'content_type': content_type,
            'content_id': metric['content_id'],
            'score': metric['score'],
            'message': f"Reduce {metric['tone']} {metric['language']} {content_type} content on {metric['platform']} due to low engagement."
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(suggestions, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(suggestions)} suggestions to {output_path}")

if __name__ == "__main__":
    input_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'analytics_db', 'post_metrics.json')
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'weekly_strategy_recommendation.json')
    adjust_future_content_strategy(input_path, output_path)