#!/usr/bin/env python3
"""
Parameter Tuning Script for IT Newsfeed Platform

This script evaluates different alpha and decay parameters for the hybrid scoring
algorithm using synthetic data. It tests various parameter combinations and generates
a comprehensive report with false positive/negative rates and other relevant metrics.
"""

import asyncio
import json
import logging
import time
import math
from datetime import datetime
from typing import Dict, List, Tuple, Any
import httpx
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TuningResult:
    """Results for a single parameter combination"""
    alpha: float
    decay_param: float
    retrieved_ids: List[str]
    total_retrieved: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    response_time_ms: float
    # Relevance-based metrics
    high_relevant_retrieved: int
    medium_relevant_retrieved: int
    low_relevant_retrieved: int
    total_high_relevant: int
    total_medium_relevant: int
    total_low_relevant: int
    high_recall: float
    medium_recall: float
    low_recall: float
    high_precision: float
    medium_precision: float
    low_precision: float
    # Ranking metrics
    precision_at_5: float
    precision_at_10: float
    precision_at_15: float
    precision_at_20: float
    ndcg_at_5: float
    ndcg_at_10: float
    ndcg_at_15: float
    ndcg_at_20: float
    map_score: float
    weighted_precision_at_10: float


class ParameterTuner:
    """Handles parameter tuning for the newsfeed platform"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.synthetic_data_path = Path("data/synthetic_news_labeled.json")
        self.evaluation_results_path = Path("data/evaluation_results_20250806_002305.json")
        
        # Load synthetic data and ground truth
        self.synthetic_events = self._load_synthetic_data()
        self.ground_truth = self._load_ground_truth()
        
        # Define parameter ranges to test
        self.alpha_values = [0.1, 0.3, 0.5, 0.7, 0.9]  # Full range including extremes
        self.decay_values = [0.01, 0.05, 0.1, 0.2, 0.5]  # Full range including extremes
        
        logger.info(f"Loaded {len(self.synthetic_events)} synthetic events")
        logger.info(f"Loaded ground truth for {len(self.ground_truth)} events")
    
    def _load_synthetic_data(self) -> List[Dict[str, Any]]:
        """Load synthetic news events"""
        try:
            with open(self.synthetic_data_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Synthetic data file not found: {self.synthetic_data_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing synthetic data: {e}")
            return []
    
    def _load_ground_truth(self) -> Dict[str, Dict[str, Any]]:
        """Load ground truth from the labeled synthetic data"""
        try:
            events = self._load_synthetic_data()
            ground_truth = {}
            
            for event in events:
                event_id = event['id']
                ground_truth[event_id] = {
                    'filter_out': event.get('filter_out', False),
                    'relevant': event.get('relevant', 'LOW'),
                    'source': event.get('source', ''),
                    'title': event.get('title', ''),
                    'published_at': event.get('published_at', '')
                }
            
            return ground_truth
        except Exception as e:
            logger.error(f"Error creating ground truth from labeled data: {e}")
            return {}
    
    def _get_expected_keep_ids(self) -> List[str]:
        """Get IDs of events that should be kept (filter_out=False)"""
        keep_ids = []
        for event_id, truth in self.ground_truth.items():
            if not truth.get('filter_out', True):  # Default to True (filter out) if not specified
                keep_ids.append(event_id)
        return keep_ids
    
    def _get_expected_discard_ids(self) -> List[str]:
        """Get IDs of events that should be discarded (filter_out=True)"""
        discard_ids = []
        for event_id, truth in self.ground_truth.items():
            if truth.get('filter_out', True):  # Default to True (filter out) if not specified
                discard_ids.append(event_id)
        return discard_ids
    
    def _get_high_relevant_ids(self) -> List[str]:
        """Get IDs of events that are highly relevant (relevant=HIGH)"""
        high_relevant_ids = []
        for event_id, truth in self.ground_truth.items():
            if truth.get('relevant') == 'HIGH':
                high_relevant_ids.append(event_id)
        return high_relevant_ids
    
    def _get_medium_relevant_ids(self) -> List[str]:
        """Get IDs of events that are medium relevant (relevant=MEDIUM)"""
        medium_relevant_ids = []
        for event_id, truth in self.ground_truth.items():
            if truth.get('relevant') == 'MEDIUM':
                medium_relevant_ids.append(event_id)
        return medium_relevant_ids
    
    def _get_low_relevant_ids(self) -> List[str]:
        """Get IDs of events that are low relevant (relevant=LOW)"""
        low_relevant_ids = []
        for event_id, truth in self.ground_truth.items():
            if truth.get('relevant') == 'LOW':
                low_relevant_ids.append(event_id)
        return low_relevant_ids
    
    def _get_relevance_score(self, event_id: str) -> int:
        """Get relevance score for an event (HIGH=3, MEDIUM=2, LOW=1, DISCARD=0)"""
        truth = self.ground_truth.get(event_id, {})
        if truth.get('filter_out', True):
            return 0  # DISCARD
        relevance = truth.get('relevant', 'LOW')
        if relevance == 'HIGH':
            return 3
        elif relevance == 'MEDIUM':
            return 2
        else:  # LOW
            return 1
    
    def _calculate_precision_at_k(self, retrieved_ids: List[str], k: int) -> float:
        """Calculate precision@k (binary: keep vs discard)"""
        if k == 0:
            return 0.0
        
        k_actual = min(k, len(retrieved_ids))
        if k_actual == 0:
            return 0.0
        
        keep_count = 0
        for i in range(k_actual):
            event_id = retrieved_ids[i]
            if not self.ground_truth.get(event_id, {}).get('filter_out', True):
                keep_count += 1
        
        return keep_count / k_actual
    
    def _calculate_weighted_precision_at_k(self, retrieved_ids: List[str], k: int) -> float:
        """Calculate weighted precision@k using relevance scores"""
        if k == 0:
            return 0.0
        
        k_actual = min(k, len(retrieved_ids))
        if k_actual == 0:
            return 0.0
        
        total_score = 0
        for i in range(k_actual):
            event_id = retrieved_ids[i]
            relevance_score = self._get_relevance_score(event_id)
            total_score += relevance_score
        
        return total_score / k_actual
    
    def _calculate_dcg_at_k(self, retrieved_ids: List[str], k: int) -> float:
        """Calculate Discounted Cumulative Gain at k"""
        if k == 0:
            return 0.0
        
        k_actual = min(k, len(retrieved_ids))
        dcg = 0.0
        
        for i in range(k_actual):
            event_id = retrieved_ids[i]
            relevance_score = self._get_relevance_score(event_id)
            # DCG formula: relevance_score / log2(i + 2) where i is 0-indexed
            dcg += relevance_score / math.log2(i + 2)
        
        return dcg
    
    def _calculate_idcg_at_k(self, k: int) -> float:
        """Calculate Ideal DCG at k (perfect ranking)"""
        if k == 0:
            return 0.0
        
        # Create ideal ranking: all HIGH relevance first, then MEDIUM, then LOW
        ideal_ranking = []
        
        # Add HIGH relevance items
        high_ids = self._get_high_relevant_ids()
        ideal_ranking.extend(high_ids)
        
        # Add MEDIUM relevance items
        medium_ids = self._get_medium_relevant_ids()
        ideal_ranking.extend(medium_ids)
        
        # Add LOW relevance items
        low_ids = self._get_low_relevant_ids()
        ideal_ranking.extend(low_ids)
        
        # Calculate DCG for ideal ranking
        return self._calculate_dcg_at_k(ideal_ranking, k)
    
    def _calculate_ndcg_at_k(self, retrieved_ids: List[str], k: int) -> float:
        """Calculate Normalized Discounted Cumulative Gain at k"""
        dcg = self._calculate_dcg_at_k(retrieved_ids, k)
        idcg = self._calculate_idcg_at_k(k)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def _calculate_map(self, retrieved_ids: List[str]) -> float:
        """Calculate Mean Average Precision"""
        if not retrieved_ids:
            return 0.0
        
        # Get all relevant items (not filtered out)
        relevant_ids = set(self._get_expected_keep_ids())
        
        if not relevant_ids:
            return 0.0
        
        precision_sum = 0.0
        relevant_count = 0
        
        for i, event_id in enumerate(retrieved_ids):
            if event_id in relevant_ids:
                relevant_count += 1
                # Precision at this position
                precision_at_i = relevant_count / (i + 1)
                precision_sum += precision_at_i
        
        return precision_sum / len(relevant_ids) if relevant_ids else 0.0
    
    async def _call_retrieve_api(self, alpha: float, decay_param: float) -> Tuple[List[str], float]:
        """Call the /retrieve API with given parameters"""
        url = f"{self.api_base_url}/retrieve"
        params = {
            'limit': 100,
            'days_back': 30,
            'alpha': alpha,
            'decay_param': decay_param
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                events = response.json()
                retrieved_ids = [event['id'] for event in events]
                
                response_time_ms = (time.time() - start_time) * 1000
                
                return retrieved_ids, response_time_ms
                
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            return [], 0.0
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            return [], 0.0
    
    def _calculate_metrics(self, retrieved_ids: List[str]) -> Dict[str, Any]:
        """Calculate precision, recall, F1-score and other metrics"""
        expected_keep_ids = set(self._get_expected_keep_ids())
        expected_discard_ids = set(self._get_expected_discard_ids())
        retrieved_set = set(retrieved_ids)
        
        # Calculate true positives, false positives, false negatives
        true_positives = len(retrieved_set & expected_keep_ids)
        false_positives = len(retrieved_set & expected_discard_ids)
        false_negatives = len(expected_keep_ids - retrieved_set)
        
        # Calculate precision, recall, F1-score
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Calculate relevance-based metrics
        high_relevant_ids = set(self._get_high_relevant_ids())
        medium_relevant_ids = set(self._get_medium_relevant_ids())
        low_relevant_ids = set(self._get_low_relevant_ids())
        
        # How many of each relevance level were retrieved
        high_retrieved = len(retrieved_set & high_relevant_ids)
        medium_retrieved = len(retrieved_set & medium_relevant_ids)
        low_retrieved = len(retrieved_set & low_relevant_ids)
        
        # Total counts for each relevance level
        total_high = len(high_relevant_ids)
        total_medium = len(medium_relevant_ids)
        total_low = len(low_relevant_ids)
        
        # Recall for each relevance level
        high_recall = high_retrieved / total_high if total_high > 0 else 0.0
        medium_recall = medium_retrieved / total_medium if total_medium > 0 else 0.0
        low_recall = low_retrieved / total_low if total_low > 0 else 0.0
        
        # Precision for each relevance level (assuming we want to prioritize HIGH relevance)
        high_precision = high_retrieved / len(retrieved_set) if len(retrieved_set) > 0 else 0.0
        medium_precision = medium_retrieved / len(retrieved_set) if len(retrieved_set) > 0 else 0.0
        low_precision = low_retrieved / len(retrieved_set) if len(retrieved_set) > 0 else 0.0
        
        return {
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'total_retrieved': len(retrieved_ids),
            'high_relevant_retrieved': high_retrieved,
            'medium_relevant_retrieved': medium_retrieved,
            'low_relevant_retrieved': low_retrieved,
            'total_high_relevant': total_high,
            'total_medium_relevant': total_medium,
            'total_low_relevant': total_low,
            'high_recall': high_recall,
            'medium_recall': medium_recall,
            'low_recall': low_recall,
            'high_precision': high_precision,
            'medium_precision': medium_precision,
            'low_precision': low_precision,
            # Ranking metrics
            'precision_at_5': self._calculate_precision_at_k(retrieved_ids, 5),
            'precision_at_10': self._calculate_precision_at_k(retrieved_ids, 10),
            'precision_at_15': self._calculate_precision_at_k(retrieved_ids, 15),
            'precision_at_20': self._calculate_precision_at_k(retrieved_ids, 20),
            'ndcg_at_5': self._calculate_ndcg_at_k(retrieved_ids, 5),
            'ndcg_at_10': self._calculate_ndcg_at_k(retrieved_ids, 10),
            'ndcg_at_15': self._calculate_ndcg_at_k(retrieved_ids, 15),
            'ndcg_at_20': self._calculate_ndcg_at_k(retrieved_ids, 20),
            'map_score': self._calculate_map(retrieved_ids),
            'weighted_precision_at_10': self._calculate_weighted_precision_at_k(retrieved_ids, 10)
        }
    
    async def test_parameter_combination(self, alpha: float, decay_param: float) -> TuningResult:
        """Test a single parameter combination"""
        logger.info(f"Testing α={alpha}, decay={decay_param}")
        
        # Call API
        retrieved_ids, response_time_ms = await self._call_retrieve_api(alpha, decay_param)
        
        # Calculate metrics
        metrics = self._calculate_metrics(retrieved_ids)
        
        return TuningResult(
            alpha=alpha,
            decay_param=decay_param,
            retrieved_ids=retrieved_ids,
            total_retrieved=metrics['total_retrieved'],
            true_positives=metrics['true_positives'],
            false_positives=metrics['false_positives'],
            false_negatives=metrics['false_negatives'],
            precision=metrics['precision'],
            recall=metrics['recall'],
            f1_score=metrics['f1_score'],
            response_time_ms=response_time_ms,
            # Relevance-based metrics
            high_relevant_retrieved=metrics['high_relevant_retrieved'],
            medium_relevant_retrieved=metrics['medium_relevant_retrieved'],
            low_relevant_retrieved=metrics['low_relevant_retrieved'],
            total_high_relevant=metrics['total_high_relevant'],
            total_medium_relevant=metrics['total_medium_relevant'],
            total_low_relevant=metrics['total_low_relevant'],
            high_recall=metrics['high_recall'],
            medium_recall=metrics['medium_recall'],
            low_recall=metrics['low_recall'],
            high_precision=metrics['high_precision'],
            medium_precision=metrics['medium_precision'],
            low_precision=metrics['low_precision'],
            # Ranking metrics
            precision_at_5=metrics['precision_at_5'],
            precision_at_10=metrics['precision_at_10'],
            precision_at_15=metrics['precision_at_15'],
            precision_at_20=metrics['precision_at_20'],
            ndcg_at_5=metrics['ndcg_at_5'],
            ndcg_at_10=metrics['ndcg_at_10'],
            ndcg_at_15=metrics['ndcg_at_15'],
            ndcg_at_20=metrics['ndcg_at_20'],
            map_score=metrics['map_score'],
            weighted_precision_at_10=metrics['weighted_precision_at_10']
        )
    
    async def run_tuning(self) -> List[TuningResult]:
        """Run the complete tuning process"""
        logger.info("Starting parameter tuning...")
        logger.info(f"Testing {len(self.alpha_values)} alpha values and {len(self.decay_values)} decay values")
        
        results = []
        total_combinations = len(self.alpha_values) * len(self.decay_values)
        current_combination = 0
        
        for alpha in self.alpha_values:
            for decay_param in self.decay_values:
                current_combination += 1
                logger.info(f"Progress: {current_combination}/{total_combinations}")
                
                result = await self.test_parameter_combination(alpha, decay_param)
                results.append(result)
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.5)
        
        logger.info("Parameter tuning completed!")
        return results
    
    def generate_report(self, results: List[TuningResult]) -> str:
        """Generate a comprehensive tuning report"""
        
        # Find best parameters by different metrics
        best_f1_result = max(results, key=lambda r: r.f1_score)
        best_ndcg10_result = max(results, key=lambda r: r.ndcg_at_10)
        best_map_result = max(results, key=lambda r: r.map_score)
        best_precision10_result = max(results, key=lambda r: r.precision_at_10)
        
        # Sort results by different metrics for ranking
        sorted_by_ndcg10 = sorted(results, key=lambda r: r.ndcg_at_10, reverse=True)
        sorted_by_map = sorted(results, key=lambda r: r.map_score, reverse=True)
        
        # Calculate summary statistics
        total_high = best_f1_result.total_high_relevant
        total_medium = best_f1_result.total_medium_relevant
        total_low = best_f1_result.total_low_relevant
        
        report = f"""
# Parameter Tuning Report - Ranking Evaluation
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary
- Total parameter combinations tested: {len(results)}
- Dataset breakdown: {total_high} HIGH relevance, {total_medium} MEDIUM relevance, {total_low} LOW relevance

## Best Parameters by Different Metrics

### Best by F1-Score
- Parameters: α={best_f1_result.alpha}, decay={best_f1_result.decay_param}
- F1-Score: {best_f1_result.f1_score:.3f}
- Precision: {best_f1_result.precision:.3f}, Recall: {best_f1_result.recall:.3f}

### Best by NDCG@10 (Ranking Quality)
- Parameters: α={best_ndcg10_result.alpha}, decay={best_ndcg10_result.decay_param}
- NDCG@10: {best_ndcg10_result.ndcg_at_10:.3f}
- Precision@10: {best_ndcg10_result.precision_at_10:.3f}
- MAP: {best_ndcg10_result.map_score:.3f}

### Best by MAP (Mean Average Precision)
- Parameters: α={best_map_result.alpha}, decay={best_map_result.decay_param}
- MAP: {best_map_result.map_score:.3f}
- NDCG@10: {best_map_result.ndcg_at_10:.3f}

### Best by Precision@10
- Parameters: α={best_precision10_result.alpha}, decay={best_precision10_result.decay_param}
- Precision@10: {best_precision10_result.precision_at_10:.3f}
- NDCG@10: {best_precision10_result.ndcg_at_10:.3f}

## Detailed Best Parameter Analysis (NDCG@10 Winner)
- Alpha: {best_ndcg10_result.alpha}
- Decay Parameter: {best_ndcg10_result.decay_param}
- Overall Precision: {best_ndcg10_result.precision:.3f}
- Overall Recall: {best_ndcg10_result.recall:.3f}
- Overall F1-Score: {best_ndcg10_result.f1_score:.3f}
- True Positives: {best_ndcg10_result.true_positives}
- False Positives: {best_ndcg10_result.false_positives}
- False Negatives: {best_ndcg10_result.false_negatives}
- Response Time: {best_ndcg10_result.response_time_ms:.1f}ms

### Ranking Performance (Best NDCG@10)
- Precision@5: {best_ndcg10_result.precision_at_5:.3f}
- Precision@10: {best_ndcg10_result.precision_at_10:.3f}
- Precision@15: {best_ndcg10_result.precision_at_15:.3f}
- Precision@20: {best_ndcg10_result.precision_at_20:.3f}
- NDCG@5: {best_ndcg10_result.ndcg_at_5:.3f}
- NDCG@10: {best_ndcg10_result.ndcg_at_10:.3f}
- NDCG@15: {best_ndcg10_result.ndcg_at_15:.3f}
- NDCG@20: {best_ndcg10_result.ndcg_at_20:.3f}
- MAP: {best_ndcg10_result.map_score:.3f}
- Weighted Precision@10: {best_ndcg10_result.weighted_precision_at_10:.3f}

### Relevance-Based Performance (Best NDCG@10)
- HIGH Relevance: {best_ndcg10_result.high_relevant_retrieved}/{total_high} retrieved (Recall: {best_ndcg10_result.high_recall:.3f})
- MEDIUM Relevance: {best_ndcg10_result.medium_relevant_retrieved}/{total_medium} retrieved (Recall: {best_ndcg10_result.medium_recall:.3f})
- LOW Relevance: {best_ndcg10_result.low_relevant_retrieved}/{total_low} retrieved (Recall: {best_ndcg10_result.low_recall:.3f})

### Ranking Examples (Best NDCG@10 Parameters: α={best_ndcg10_result.alpha}, decay={best_ndcg10_result.decay_param})

#### Top 3 Retrieved Items:
"""
        
        # Get ranking examples for the best NDCG result
        examples = self._get_ranking_examples(best_ndcg10_result.retrieved_ids, 3)
        
        for item in examples['top']:
            relevance_emoji = "🟢" if item['relevant'] == 'HIGH' else "🟡" if item['relevant'] == 'MEDIUM' else "🔴"
            filter_emoji = "✅" if not item['filter_out'] else "❌"
            report += f"""
{item['position']}. {relevance_emoji} {filter_emoji} **{item['title']}**
   - Source: {item['source']}
   - Relevance: {item['relevant']} (Score: {item['relevance_score']})
   - ID: {item['id']}
"""
        
        report += "\n#### Bottom 3 Retrieved Items:\n"
        
        for item in examples['bottom']:
            relevance_emoji = "🟢" if item['relevant'] == 'HIGH' else "🟡" if item['relevant'] == 'MEDIUM' else "🔴"
            filter_emoji = "✅" if not item['filter_out'] else "❌"
            report += f"""
{item['position']}. {relevance_emoji} {filter_emoji} **{item['title']}**
   - Source: {item['source']}
   - Relevance: {item['relevant']} (Score: {item['relevance_score']})
   - ID: {item['id']}
"""
        
        report += "\n#### Ranking Examples for Comparison (Best F1 vs Best NDCG@10):\n"
        
        # Compare best F1 vs best NDCG
        best_f1_examples = self._get_ranking_examples(best_f1_result.retrieved_ids, 3)
        best_ndcg_examples = self._get_ranking_examples(best_ndcg10_result.retrieved_ids, 3)
        
        report += f"\n**Best F1 Parameters (α={best_f1_result.alpha}, decay={best_f1_result.decay_param}) - Top 3:**\n"
        for item in best_f1_examples['top']:
            relevance_emoji = "🟢" if item['relevant'] == 'HIGH' else "🟡" if item['relevant'] == 'MEDIUM' else "🔴"
            filter_emoji = "✅" if not item['filter_out'] else "❌"
            report += f"- {relevance_emoji} {filter_emoji} {item['title']} ({item['relevant']}, Score: {item['relevance_score']})\n"
        
        report += f"\n**Best NDCG@10 Parameters (α={best_ndcg10_result.alpha}, decay={best_ndcg10_result.decay_param}) - Top 3:**\n"
        for item in best_ndcg_examples['top']:
            relevance_emoji = "🟢" if item['relevant'] == 'HIGH' else "🟡" if item['relevant'] == 'MEDIUM' else "🔴"
            filter_emoji = "✅" if not item['filter_out'] else "❌"
            report += f"- {relevance_emoji} {filter_emoji} {item['title']} ({item['relevant']}, Score: {item['relevance_score']})\n"
        
        report += "\n## Parameter Rankings\n"
        for i, result in enumerate(sorted_by_ndcg10[:10], 1):
            report += f"""
{i}. α={result.alpha}, decay={result.decay_param}
   - NDCG@10: {result.ndcg_at_10:.3f}, Precision@10: {result.precision_at_10:.3f}, MAP: {result.map_score:.3f}
   - F1: {result.f1_score:.3f}, Precision: {result.precision:.3f}, Recall: {result.recall:.3f}
   - Response Time: {result.response_time_ms:.1f}ms
"""
        
        report += "\n### Top 10 by MAP (Mean Average Precision)\n"
        for i, result in enumerate(sorted_by_map[:10], 1):
            report += f"""
{i}. α={result.alpha}, decay={result.decay_param}
   - MAP: {result.map_score:.3f}, NDCG@10: {result.ndcg_at_10:.3f}, Precision@10: {result.precision_at_10:.3f}
   - F1: {result.f1_score:.3f}, Precision: {result.precision:.3f}, Recall: {result.recall:.3f}
   - Response Time: {result.response_time_ms:.1f}ms
"""
        
        # Alpha analysis with ranking metrics
        report += "\n## Alpha Parameter Analysis\n"
        alpha_groups = {}
        for result in results:
            if result.alpha not in alpha_groups:
                alpha_groups[result.alpha] = []
            alpha_groups[result.alpha].append(result)
        
        for alpha in sorted(alpha_groups.keys()):
            avg_f1 = sum(r.f1_score for r in alpha_groups[alpha]) / len(alpha_groups[alpha])
            avg_ndcg10 = sum(r.ndcg_at_10 for r in alpha_groups[alpha]) / len(alpha_groups[alpha])
            avg_map = sum(r.map_score for r in alpha_groups[alpha]) / len(alpha_groups[alpha])
            avg_precision10 = sum(r.precision_at_10 for r in alpha_groups[alpha]) / len(alpha_groups[alpha])
            report += f"- α={alpha}: Avg F1={avg_f1:.3f}, Avg NDCG@10={avg_ndcg10:.3f}, Avg MAP={avg_map:.3f}, Avg P@10={avg_precision10:.3f}\n"
        
        # Decay analysis with ranking metrics
        report += "\n## Decay Parameter Analysis\n"
        decay_groups = {}
        for result in results:
            if result.decay_param not in decay_groups:
                decay_groups[result.decay_param] = []
            decay_groups[result.decay_param].append(result)
        
        for decay in sorted(decay_groups.keys()):
            avg_f1 = sum(r.f1_score for r in decay_groups[decay]) / len(decay_groups[decay])
            avg_ndcg10 = sum(r.ndcg_at_10 for r in decay_groups[decay]) / len(decay_groups[decay])
            avg_map = sum(r.map_score for r in decay_groups[decay]) / len(decay_groups[decay])
            avg_precision10 = sum(r.precision_at_10 for r in decay_groups[decay]) / len(decay_groups[decay])
            report += f"- decay={decay}: Avg F1={avg_f1:.3f}, Avg NDCG@10={avg_ndcg10:.3f}, Avg MAP={avg_map:.3f}, Avg P@10={avg_precision10:.3f}\n"
        
        # Performance analysis
        report += "\n## Performance Analysis\n"
        avg_response_time = sum(r.response_time_ms for r in results) / len(results)
        min_response_time = min(r.response_time_ms for r in results)
        max_response_time = max(r.response_time_ms for r in results)
        report += f"- Average Response Time: {avg_response_time:.1f}ms\n"
        report += f"- Min Response Time: {min_response_time:.1f}ms\n"
        report += f"- Max Response Time: {max_response_time:.1f}ms\n"
        
        # Detailed results table
        report += "\n## Detailed Results (Top 15 by NDCG@10)\n"
        report += "| Alpha | Decay | NDCG@10 | P@10 | MAP | F1 | P@5 | P@15 | P@20 | Response Time (ms) |\n"
        report += "|-------|-------|---------|------|-----|----|-----|------|------|-------------------|\n"
        
        for result in sorted_by_ndcg10[:15]:
            report += f"| {result.alpha} | {result.decay_param} | {result.ndcg_at_10:.3f} | {result.precision_at_10:.3f} | {result.map_score:.3f} | {result.f1_score:.3f} | {result.precision_at_5:.3f} | {result.precision_at_15:.3f} | {result.precision_at_20:.3f} | {result.response_time_ms:.1f} |\n"
        
        return report
    
    def save_results(self, results: List[TuningResult], report: str):
        """Save results and report to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Find best result for dataset summary
        best_result = max(results, key=lambda r: r.f1_score)

        # Save detailed results as JSON
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'total_combinations': len(results),
            'best_f1_score': max(r.f1_score for r in results),
            'best_alpha': max(results, key=lambda r: r.f1_score).alpha,
            'best_decay': max(results, key=lambda r: r.f1_score).decay_param,
            'dataset_summary': {
                'total_high_relevant': best_result.total_high_relevant,
                'total_medium_relevant': best_result.total_medium_relevant,
                'total_low_relevant': best_result.total_low_relevant
            },
            'results': [
                {
                    'alpha': r.alpha,
                    'decay_param': r.decay_param,
                    'f1_score': r.f1_score,
                    'precision': r.precision,
                    'recall': r.recall,
                    'true_positives': r.true_positives,
                    'false_positives': r.false_positives,
                    'false_negatives': r.false_negatives,
                    'response_time_ms': r.response_time_ms,
                    'retrieved_ids': r.retrieved_ids,
                    'relevance_metrics': {
                        'high_relevant_retrieved': r.high_relevant_retrieved,
                        'medium_relevant_retrieved': r.medium_relevant_retrieved,
                        'low_relevant_retrieved': r.low_relevant_retrieved,
                        'total_high_relevant': r.total_high_relevant,
                        'total_medium_relevant': r.total_medium_relevant,
                        'total_low_relevant': r.total_low_relevant,
                        'high_recall': r.high_recall,
                        'medium_recall': r.medium_recall,
                        'low_recall': r.low_recall,
                        'high_precision': r.high_precision,
                        'medium_precision': r.medium_precision,
                        'low_precision': r.low_precision
                    },
                    'ranking_metrics': {
                        'precision_at_5': r.precision_at_5,
                        'precision_at_10': r.precision_at_10,
                        'precision_at_15': r.precision_at_15,
                        'precision_at_20': r.precision_at_20,
                        'ndcg_at_5': r.ndcg_at_5,
                        'ndcg_at_10': r.ndcg_at_10,
                        'ndcg_at_15': r.ndcg_at_15,
                        'ndcg_at_20': r.ndcg_at_20,
                        'map_score': r.map_score,
                        'weighted_precision_at_10': r.weighted_precision_at_10
                    }
                }
                for r in results
            ]
        }
        
        results_file = f"data/tuning_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        # Save report as markdown
        report_file = f"data/tuning_report_{timestamp}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Results saved to {results_file}")
        logger.info(f"Report saved to {report_file}")
        
        return results_file, report_file

    def _get_event_details(self, event_id: str) -> Dict[str, Any]:
        """Get detailed information about an event for display"""
        # Find the event in synthetic data
        for event in self.synthetic_events:
            if event['id'] == event_id:
                return {
                    'id': event['id'],
                    'title': event['title'],
                    'source': event['source'],
                    'relevant': event.get('relevant', 'LOW'),
                    'filter_out': event.get('filter_out', True),
                    'relevance_score': self._get_relevance_score(event_id)
                }
        return {
            'id': event_id,
            'title': 'Unknown',
            'source': 'Unknown',
            'relevant': 'LOW',
            'filter_out': True,
            'relevance_score': 0
        }
    
    def _get_ranking_examples(self, retrieved_ids: List[str], k: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """Get examples from the top and bottom of the ranking"""
        if not retrieved_ids:
            return {'top': [], 'bottom': []}
        
        # Get top k items
        top_items = []
        for i, event_id in enumerate(retrieved_ids[:k]):
            details = self._get_event_details(event_id)
            details['position'] = i + 1
            top_items.append(details)
        
        # Get bottom k items
        bottom_items = []
        for i, event_id in enumerate(retrieved_ids[-k:]):
            details = self._get_event_details(event_id)
            details['position'] = len(retrieved_ids) - k + i + 1
            bottom_items.append(details)
        
        return {'top': top_items, 'bottom': bottom_items}


async def main():
    """Main function to run the tuning process"""
    logger.info("Starting IT Newsfeed Platform Parameter Tuning")
    
    # Initialize tuner
    tuner = ParameterTuner()
    
    # Check if synthetic data is available
    if not tuner.synthetic_events:
        logger.error("No synthetic data available. Please ensure data/synthetic_news_labeled.json exists.")
        return
    
    if not tuner.ground_truth:
        logger.error("No ground truth data available. Please ensure data/evaluation_results_*.json exists.")
        return
    
    # Run tuning
    results = await tuner.run_tuning()
    
    # Generate and save report
    report = tuner.generate_report(results)
    results_file, report_file = tuner.save_results(results, report)
    
    # Print summary
    best_result = max(results, key=lambda r: r.f1_score)
    best_ndcg_result = max(results, key=lambda r: r.ndcg_at_10)
    print(f"\n{'='*60}")
    print("TUNING COMPLETED")
    print(f"{'='*60}")
    print(f"Best F1-Score: {best_result.f1_score:.3f} (α={best_result.alpha}, decay={best_result.decay_param})")
    print(f"Best NDCG@10: {best_ndcg_result.ndcg_at_10:.3f} (α={best_ndcg_result.alpha}, decay={best_ndcg_result.decay_param})")
    print(f"Best MAP: {max(r.map_score for r in results):.3f}")
    print(f"Best Precision@10: {max(r.precision_at_10 for r in results):.3f}")
    print(f"\nDetailed results: {results_file}")
    print(f"Full report: {report_file}")


if __name__ == "__main__":
    asyncio.run(main()) 