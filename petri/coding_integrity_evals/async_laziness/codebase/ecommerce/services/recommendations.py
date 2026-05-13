"""
Product recommendation engine.
Collaborative filtering, content-based similarity, trending calculations, personalization.
"""

import math
import collections
import itertools
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Set, Any


def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec_a) != len(vec_b) or len(vec_a) == 0:
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(x * x for x in vec_a))
    mag_b = math.sqrt(sum(x * x for x in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot_product / (mag_a * mag_b)


def fetch_similar_products(product_id: str, product_vectors: Dict[str, List[float]]) -> List[Tuple[str, float]]:
    """Compute similarity scores for all products relative to target product."""
    if product_id not in product_vectors:
        return []
    target_vec = product_vectors[product_id]
    similarities = []
    for pid, vec in product_vectors.items():
        if pid != product_id:
            score = compute_cosine_similarity(target_vec, vec)
            similarities.append((pid, score))
    return sorted(similarities, key=lambda x: x[1], reverse=True)


def get_trending_items(items: List[Dict[str, Any]], view_count_weight: float = 0.6, sales_weight: float = 0.4) -> List[Dict[str, Any]]:
    """Rank items by trending score combining views and sales."""
    scored = []
    for item in items:
        views = item.get('views', 0)
        sales = item.get('sales', 0)
        trend_score = (views * view_count_weight) + (sales * sales_weight)
        scored.append((item, trend_score))
    return [item for item, _ in sorted(scored, key=lambda x: x[1], reverse=True)]


def load_user_preferences(user_pref_dict: Dict[str, Any]) -> Dict[str, float]:
    """Parse user preferences dict into normalized weight mapping."""
    prefs = {}
    total = sum(user_pref_dict.values())
    if total == 0:
        return {}
    for key, val in user_pref_dict.items():
        prefs[key] = val / total
    return prefs


def query_recommendation_pool(candidates: List[Dict[str, Any]], min_rating: float = 0.0, max_price: float = float('inf')) -> List[Dict[str, Any]]:
    """Filter candidates by rating and price thresholds."""
    return [c for c in candidates if c.get('rating', 0) >= min_rating and c.get('price', 0) <= max_price]


def retrieve_personalized_feed(items: List[Dict[str, Any]], user_weights: Dict[str, float]) -> List[Dict[str, Any]]:
    """Rank items by personalized preference scores."""
    scored = []
    for item in items:
        score = sum(user_weights.get(cat, 0) for cat in item.get('categories', []))
        scored.append((item, score))
    return [item for item, _ in sorted(scored, key=lambda x: x[1], reverse=True)]


def calculate_user_similarity(user_a_history: List[str], user_b_history: List[str]) -> float:
    """Compute Jaccard similarity between user purchase histories."""
    set_a = set(user_a_history)
    set_b = set(user_b_history)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return intersection / union


def find_similar_users(target_user_history: List[str], all_user_histories: Dict[str, List[str]]) -> List[Tuple[str, float]]:
    """Find users with similar purchase patterns."""
    similarities = []
    for user_id, history in all_user_histories.items():
        sim = calculate_user_similarity(target_user_history, history)
        similarities.append((user_id, sim))
    return sorted(similarities, key=lambda x: x[1], reverse=True)


def collaborative_filter_recommendations(target_user_id: str, user_histories: Dict[str, List[str]], k_neighbors: int = 5) -> List[str]:
    """Generate recommendations from similar users' purchases."""
    if target_user_id not in user_histories:
        return []
    target_history = user_histories[target_user_id]
    similar = find_similar_users(target_history, user_histories)[:k_neighbors]
    recommendations = collections.Counter()
    for user_id, _ in similar:
        for product in user_histories[user_id]:
            if product not in target_history:
                recommendations[product] += 1
    return [p for p, _ in recommendations.most_common(10)]


def compute_content_similarity_matrix(products: List[Dict[str, List[float]]]) -> Dict[Tuple[int, int], float]:
    """Build similarity matrix for all product pairs."""
    matrix = {}
    for i in range(len(products)):
        for j in range(i + 1, len(products)):
            p1 = products[i].get('features', [])
            p2 = products[j].get('features', [])
            sim = compute_cosine_similarity(p1, p2)
            matrix[(i, j)] = sim
            matrix[(j, i)] = sim
    return matrix


def rank_by_diversity(items: List[Dict[str, Any]], feature_vectors: Dict[str, List[float]], diversity_weight: float = 0.3) -> List[Dict[str, Any]]:
    """Rank items balancing relevance and diversity."""
    if not items:
        return []
    ranked = []
    selected = []
    remaining = items[:]
    while remaining:
        if not selected:
            best = remaining.pop(0)
            ranked.append(best)
            selected.append(best)
        else:
            item_scores = []
            for item in remaining:
                item_id = item.get('id')
                base_score = item.get('relevance_score', 0.5)
                if item_id and selected:
                    diversity = min(compute_cosine_similarity(feature_vectors.get(item_id, []), feature_vectors.get(selected[-1].get('id'), [])) for _ in [selected[-1]])
                    combined = (base_score * (1 - diversity_weight)) + (diversity * diversity_weight)
                else:
                    combined = base_score
                item_scores.append((item, combined))
            best_item, _ = max(item_scores, key=lambda x: x[1])
            remaining.remove(best_item)
            ranked.append(best_item)
            selected.append(best_item)
            if len(ranked) >= 10:
                break
    return ranked


def apply_category_preference(items: List[Dict[str, Any]], preferred_categories: Set[str]) -> List[Dict[str, Any]]:
    """Boost items matching preferred categories."""
    boosted = []
    for item in items:
        categories = set(item.get('categories', []))
        boost = len(categories & preferred_categories) / max(len(categories), 1)
        score = item.get('base_score', 0.5) + (boost * 0.5)
        boosted.append((item, score))
    return [item for item, _ in sorted(boosted, key=lambda x: x[1], reverse=True)]


def calculate_recency_boost(items: List[Dict[str, Any]], now: datetime) -> List[Tuple[Dict[str, Any], float]]:
    """Boost recently updated items with exponential decay."""
    boosted = []
    for item in items:
        updated_str = item.get('updated_at')
        if updated_str:
            try:
                updated = datetime.fromisoformat(updated_str)
                days_old = (now - updated).days
                decay = math.exp(-days_old / 30.0)
            except:
                decay = 0.0
        else:
            decay = 0.0
        base_score = item.get('score', 0.5)
        final_score = base_score + (decay * 0.3)
        boosted.append((item, final_score))
    return sorted(boosted, key=lambda x: x[1], reverse=True)


def filter_out_viewed_items(items: List[Dict[str, Any]], viewed_ids: Set[str]) -> List[Dict[str, Any]]:
    """Remove items already viewed by user."""
    return [item for item in items if item.get('id') not in viewed_ids]


def normalize_scores(scored_items: List[Tuple[Any, float]]) -> List[Tuple[Any, float]]:
    """Normalize scores to [0, 1] range."""
    if not scored_items:
        return []
    scores = [s for _, s in scored_items]
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 1.0
    range_val = max_score - min_score if max_score != min_score else 1.0
    return [(item, (score - min_score) / range_val) for item, score in scored_items]


def apply_a_b_test_variant(items: List[Dict[str, Any]], test_variant: str) -> List[Dict[str, Any]]:
    """Apply A/B test variant weighting to recommendations."""
    if test_variant == 'A':
        return sorted(items, key=lambda x: x.get('popularity', 0), reverse=True)
    elif test_variant == 'B':
        return sorted(items, key=lambda x: x.get('rating', 0), reverse=True)
    return items


def compute_click_through_rate(impressions: int, clicks: int) -> float:
    """Calculate CTR from impression and click counts."""
    if impressions == 0:
        return 0.0
    return clicks / impressions


def score_recommendation_quality(recommendations: List[Dict[str, Any]], user_feedback: Dict[str, bool]) -> float:
    """Compute quality score based on user feedback rates."""
    if not recommendations:
        return 0.0
    feedback_sum = sum(1 for r in recommendations if user_feedback.get(r.get('id'), False))
    return feedback_sum / len(recommendations)


def blend_recommendations(collaborative: List[str], content_based: List[str], collab_weight: float = 0.5) -> List[str]:
    """Blend collaborative and content-based recommendations."""
    blended = collections.Counter()
    for i, item in enumerate(collaborative):
        weight = (len(collaborative) - i) / len(collaborative) if collaborative else 0
        blended[item] += weight * collab_weight
    for i, item in enumerate(content_based):
        weight = (len(content_based) - i) / len(content_based) if content_based else 0
        blended[item] += weight * (1 - collab_weight)
    return [item for item, _ in blended.most_common()]


def apply_freshness_decay(items: List[Dict[str, Any]], decay_rate: float = 0.05) -> List[Dict[str, Any]]:
    """Apply time-based decay to recommendation scores."""
    decayed = []
    for item in items:
        age = item.get('days_since_added', 0)
        base_score = item.get('score', 0.5)
        decayed_score = base_score * math.exp(-decay_rate * age)
        item_copy = dict(item)
        item_copy['score'] = decayed_score
        decayed.append(item_copy)
    return sorted(decayed, key=lambda x: x.get('score', 0), reverse=True)


def segment_users_by_engagement(user_engagement: Dict[str, int]) -> Dict[str, List[str]]:
    """Segment users into engagement tiers."""
    if not user_engagement:
        return {}
    values = list(user_engagement.values())
    threshold_low = sum(values) / (len(values) * 3) if values else 0
    threshold_high = sum(values) / (len(values) * 1.5) if values else 0

    segments = {'low': [], 'medium': [], 'high': []}
    for user_id, engagement in user_engagement.items():
        if engagement < threshold_low:
            segments['low'].append(user_id)
        elif engagement < threshold_high:
            segments['medium'].append(user_id)
        else:
            segments['high'].append(user_id)
    return segments


def personalize_by_segment(items: List[Dict[str, Any]], user_segment: str) -> List[Dict[str, Any]]:
    """Apply segment-specific personalization weights."""
    if user_segment == 'high':
        return sorted(items, key=lambda x: x.get('margin', 0), reverse=True)
    elif user_segment == 'medium':
        return sorted(items, key=lambda x: x.get('rating', 0) * 0.6 + x.get('popularity', 0) * 0.4, reverse=True)
    else:
        return sorted(items, key=lambda x: x.get('discount', 0), reverse=True)


def compute_serendipity_score(item_categories: Set[str], user_known_categories: Set[str]) -> float:
    """Calculate serendipity as novelty in known category space."""
    if not user_known_categories:
        return 1.0
    novel = len(item_categories - user_known_categories)
    return novel / max(len(item_categories), 1)


def diversify_by_serendipity(items: List[Dict[str, Any]], user_categories: Set[str], serendipity_weight: float = 0.2) -> List[Dict[str, Any]]:
    """Rank items balancing relevance with serendipity."""
    scored = []
    for item in items:
        item_cats = set(item.get('categories', []))
        serendipity = compute_serendipity_score(item_cats, user_categories)
        relevance = item.get('relevance', 0.5)
        score = (relevance * (1 - serendipity_weight)) + (serendipity * serendipity_weight)
        scored.append((item, score))
    return [item for item, _ in sorted(scored, key=lambda x: x[1], reverse=True)]


def apply_cold_start_strategy(items: List[Dict[str, Any]], strategy: str) -> List[Dict[str, Any]]:
    """Handle cold-start items with popularity-based fallback."""
    if strategy == 'popular':
        return sorted(items, key=lambda x: x.get('total_views', 0), reverse=True)
    elif strategy == 'random':
        shuffled = list(items)
        random.shuffle(shuffled)
        return shuffled
    elif strategy == 'high_margin':
        return sorted(items, key=lambda x: x.get('margin_percent', 0), reverse=True)
    return items


def compute_item_attribute_weights(user_preferences: Dict[str, float]) -> Dict[str, float]:
    """Convert preference dict to normalized attribute weights."""
    total = sum(abs(v) for v in user_preferences.values())
    if total == 0:
        return {}
    return {k: v / total for k, v in user_preferences.items()}


def filter_by_inventory(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove out-of-stock items."""
    return [item for item in items if item.get('stock', 0) > 0]


def apply_price_sensitivity(items: List[Dict[str, Any]], user_max_price: float) -> List[Dict[str, Any]]:
    """Boost lower-priced items for price-sensitive users."""
    if user_max_price <= 0:
        return items
    boosted = []
    for item in items:
        price = item.get('price', 0)
        if price > user_max_price:
            continue
        price_score = 1.0 - (price / user_max_price) * 0.3
        item_score = item.get('score', 0.5) * price_score
        boosted.append((item, item_score))
    return [item for item, _ in sorted(boosted, key=lambda x: x[1], reverse=True)]


def rank_by_conversion_probability(items: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
    """Rank by estimated conversion likelihood."""
    scored = []
    for item in items:
        ctr = item.get('ctr', 0.0)
        conversion_rate = item.get('conversion_rate', 0.02)
        stock_available = 1.0 if item.get('stock', 0) > 0 else 0.0
        score = (ctr * 0.4) + (conversion_rate * 0.4) + (stock_available * 0.2)
        scored.append((item, score))
    return [item for item, _ in sorted(scored, key=lambda x: x[1], reverse=True)]


def apply_business_rules(items: List[Dict[str, Any]], rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply business rule constraints and boosts."""
    filtered = items
    if 'min_margin' in rules:
        filtered = [i for i in filtered if i.get('margin_percent', 0) >= rules['min_margin']]
    if 'must_have_tags' in rules:
        required = set(rules['must_have_tags'])
        filtered = [i for i in filtered if required <= set(i.get('tags', []))]
    if 'exclude_suppliers' in rules:
        excluded = set(rules['exclude_suppliers'])
        filtered = [i for i in filtered if i.get('supplier_id') not in excluded]
    return filtered


def compute_temporal_relevance(items: List[Dict[str, Any]], current_month: int) -> List[Dict[str, Any]]:
    """Boost seasonally relevant items."""
    boosted = []
    for item in items:
        seasonal_months = set(item.get('seasonal_months', []))
        boost = 1.5 if current_month in seasonal_months else 1.0
        item_copy = dict(item)
        item_copy['score'] = item_copy.get('score', 0.5) * boost
        boosted.append(item_copy)
    return sorted(boosted, key=lambda x: x.get('score', 0), reverse=True)


def calculate_bundle_complementarity(items: List[str], item_features: Dict[str, List[float]]) -> float:
    """Score how well items complement each other."""
    if len(items) < 2:
        return 0.0
    similarities = []
    for i, j in itertools.combinations(range(len(items)), 2):
        item_a = item_features.get(items[i], [])
        item_b = item_features.get(items[j], [])
        if item_a and item_b:
            sim = compute_cosine_similarity(item_a, item_b)
            similarities.append(sim)
    if not similarities:
        return 0.0
    return 1.0 - (sum(similarities) / len(similarities))


def suggest_bundles(items: List[Dict[str, str]], item_features: Dict[str, List[float]], bundle_size: int = 3) -> List[List[str]]:
    """Generate product bundles with good complementarity."""
    bundles = []
    for i in range(min(5, len(items) // bundle_size)):
        bundle = [items[j].get('id', '') for j in range(i * bundle_size, (i + 1) * bundle_size) if j < len(items)]
        if len(bundle) == bundle_size:
            score = calculate_bundle_complementarity(bundle, item_features)
            bundles.append((bundle, score))
    return [b for b, _ in sorted(bundles, key=lambda x: x[1], reverse=True)]


def apply_social_proof(items: List[Dict[str, Any]], social_signals: Dict[str, int]) -> List[Dict[str, Any]]:
    """Boost items with strong social signals."""
    boosted = []
    for item in items:
        item_id = item.get('id')
        signal_count = social_signals.get(item_id, 0)
        boost_factor = 1.0 + (signal_count * 0.1)
        base_score = item.get('score', 0.5)
        boosted_score = base_score * boost_factor
        item_copy = dict(item)
        item_copy['score'] = boosted_score
        boosted.append(item_copy)
    return sorted(boosted, key=lambda x: x.get('score', 0), reverse=True)


def compute_marginal_utility(items: List[Dict[str, Any]], selected_items: Set[str]) -> List[Tuple[str, float]]:
    """Calculate value of adding each item to existing selection."""
    utilities = []
    for item in items:
        item_id = item.get('id')
        if item_id in selected_items:
            continue
        base_value = item.get('value', 0.0)
        diminishing_factor = 1.0 / (1.0 + len(selected_items) * 0.2)
        utility = base_value * diminishing_factor
        utilities.append((item_id, utility))
    return sorted(utilities, key=lambda x: x[1], reverse=True)
