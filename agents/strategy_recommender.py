import json
import os
import logging
from typing import Dict, List

# Logging setup for Strategy Recommender
USER_ID = 'strategy_recommender_user'
logger = logging.getLogger('strategy_recommender')
logger.setLevel(logging.INFO)
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(log_dir, 'strategy_recommender.txt'), encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - User: %(user)s - %(message)s')
file_handler.setFormatter(formatter)
file_handler.addFilter(lambda record: setattr(record, 'user', USER_ID) or True)
logger.handlers = [file_handler]

def calculate_score(stats: Dict) -> float:
    """Calculate a weighted score for a post."""
    weights = {'likes': 0.5, 'shares': 0.3, 'comments': 0.2, 'retweets': 0.3, 'quotes': 0.2, 'views': 0.1}
    return sum(stats.get(key, 0) * weight for key, weight in weights.items())

def adjust_future_content_strategy(input_path: str, output_dir: str) -> None:
    """Run Adaptive Improvement Trigger."""
    logger.info("Starting Adaptive Improvement Trigger")
    os.makedirs(output_dir, exist_ok=True)

    # Clear strategy_suggestions.json
    output_path = os.path.join(output_dir, 'strategy_suggestions.json')
    if os.path.exists(output_path):
        os.remove(output_path)
        logger.info(f"Cleared strategy_suggestions.json: {output_path}")

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            metrics = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {input_path}: {str(e)}")
        return

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
        suggestions.append({
            'type': 'high-performing',
            'platform': metric['platform'],
            'language': metric['language'],
            'sentiment': metric['sentiment'],
            'content_id': metric['content_id'],
            'score': metric['score'],
            'message': f"Increase {metric['sentiment']} {metric['language']} content on {metric['platform']} for better engagement."
        })
    for metric in underperformers:
        suggestions.append({
            'type': 'underperforming',
            'platform': metric['platform'],
            'language': metric['language'],
            'sentiment': metric['sentiment'],
            'content_id': metric['content_id'],
            'score': metric['score'],
            'message': f"Reduce {metric['sentiment']} {metric['language']} content on {metric['platform']} due to low engagement."
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(suggestions, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(suggestions)} suggestions to {output_path}")

if __name__ == "__main__":
    input_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'analytics_db', 'post_metrics.json')
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'analytics_db')
    adjust_future_content_strategy(input_path, output_dir)