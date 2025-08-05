"""
Synthetic Data Analyzer

This utility analyzes the synthetic news data to understand patterns,
content structure, and characteristics that can inform filtering logic.
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from src.models.domain import NewsEvent


class SyntheticDataAnalyzer:
    """Analyzer for synthetic news data"""
    
    def __init__(self, data_file: str = "data/synthetic_news.json"):
        self.data_file = Path(data_file)
        self.events: List[NewsEvent] = []
        self.raw_data: List[Dict[str, Any]] = []
    
    def load_data(self) -> bool:
        """Load and parse synthetic data"""
        if not self.data_file.exists():
            print(f"❌ Data file not found: {self.data_file}")
            return False
        
        try:
            with open(self.data_file, 'r') as f:
                self.raw_data = json.load(f)
            
            # Convert to NewsEvent objects
            for item in self.raw_data:
                try:
                    event = NewsEvent(
                        id=item['id'],
                        source=item['source'],
                        title=item['title'],
                        body=item.get('body', ''),
                        published_at=datetime.fromisoformat(item['published_at'].replace('Z', '+00:00'))
                    )
                    self.events.append(event)
                except Exception as e:
                    print(f"⚠️  Error parsing event {item.get('id', 'unknown')}: {e}")
            
            print(f"✅ Loaded {len(self.events)} events from {self.data_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def analyze_sources(self) -> Dict[str, Any]:
        """Analyze source distribution and characteristics"""
        source_counts = Counter(event.source for event in self.events)
        
        analysis = {
            'total_events': len(self.events),
            'unique_sources': len(source_counts),
            'source_distribution': dict(source_counts),
            'source_analysis': {}
        }
        
        for source in source_counts.keys():
            source_events = [e for e in self.events if e.source == source]
            analysis['source_analysis'][source] = {
                'count': len(source_events),
                'has_body': sum(1 for e in source_events if e.body.strip()),
                'avg_body_length': sum(len(e.body) for e in source_events) / len(source_events),
                'avg_title_length': sum(len(e.title) for e in source_events) / len(source_events),
                'sample_titles': [e.title for e in source_events[:3]]
            }
        
        return analysis
    
    def analyze_content_patterns(self) -> Dict[str, Any]:
        """Analyze content patterns and keywords"""
        all_text = ' '.join([f"{e.title} {e.body}" for e in self.events])
        
        # Extract technical terms and patterns
        technical_terms = re.findall(r'\b[A-Z]{2,}(?:-[A-Z0-9]+)*\b', all_text)
        cve_patterns = re.findall(r'CVE-\d{4}-\d+', all_text)
        version_patterns = re.findall(r'\d+\.\d+(?:\.\d+)*', all_text)
        
        # Common IT terms
        it_keywords = [
            'vulnerability', 'security', 'outage', 'disruption', 'patch', 'update',
            'critical', 'emergency', 'exploit', 'malware', 'ransomware', 'breach',
            'authentication', 'authorization', 'database', 'server', 'network',
            'cloud', 'service', 'API', 'endpoint', 'firewall', 'encryption'
        ]
        
        keyword_counts = {}
        for keyword in it_keywords:
            count = len(re.findall(rf'\b{keyword}\b', all_text, re.IGNORECASE))
            if count > 0:
                keyword_counts[keyword] = count
        
        return {
            'technical_terms': Counter(technical_terms).most_common(20),
            'cve_references': len(cve_patterns),
            'version_references': len(version_patterns),
            'it_keyword_frequency': dict(sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)),
            'total_words': len(all_text.split()),
            'avg_words_per_event': len(all_text.split()) / len(self.events)
        }
    
    def analyze_urgency_indicators(self) -> Dict[str, Any]:
        """Analyze urgency and severity indicators"""
        urgency_keywords = {
            'critical': ['critical', 'emergency', 'urgent', 'immediate'],
            'high': ['high', 'severe', 'serious', 'major'],
            'medium': ['medium', 'moderate', 'minor'],
            'low': ['low', 'minor', 'informational']
        }
        
        urgency_analysis = defaultdict(int)
        severity_indicators = defaultdict(int)
        
        for event in self.events:
            text = f"{event.title} {event.body}".lower()
            
            # Check urgency levels
            for level, keywords in urgency_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        urgency_analysis[level] += 1
                        break
            
            # Check for specific severity indicators
            if 'cve' in text:
                severity_indicators['has_cve'] += 1
            if 'cvss' in text:
                severity_indicators['has_cvss'] += 1
            if 'exploit' in text or 'exploitation' in text:
                severity_indicators['mentions_exploitation'] += 1
            if 'patch' in text or 'update' in text:
                severity_indicators['mentions_patch'] += 1
            if 'outage' in text or 'disruption' in text:
                severity_indicators['mentions_outage'] += 1
        
        return {
            'urgency_distribution': dict(urgency_analysis),
            'severity_indicators': dict(severity_indicators),
            'total_events': len(self.events)
        }
    
    def analyze_temporal_patterns(self) -> Dict[str, Any]:
        """Analyze temporal patterns in the data"""
        timestamps = [event.published_at for event in self.events]
        timestamps.sort()
        
        # Calculate time spans
        if timestamps:
            time_span = timestamps[-1] - timestamps[0]
            avg_interval = time_span / (len(timestamps) - 1) if len(timestamps) > 1 else None
        else:
            time_span = None
            avg_interval = None
        
        # Group by hour to see distribution
        hour_distribution = Counter(timestamp.hour for timestamp in timestamps)
        
        return {
            'time_span_hours': time_span.total_seconds() / 3600 if time_span else None,
            'avg_interval_minutes': avg_interval.total_seconds() / 60 if avg_interval else None,
            'hour_distribution': dict(hour_distribution),
            'earliest_event': timestamps[0].isoformat() if timestamps else None,
            'latest_event': timestamps[-1].isoformat() if timestamps else None
        }
    
    def generate_filtering_insights(self) -> Dict[str, Any]:
        """Generate insights for filtering logic"""
        insights = {
            'recommended_keywords': [],
            'recommended_sources': [],
            'content_characteristics': {},
            'filtering_strategies': []
        }
        
        # Analyze which sources have the most relevant content
        source_relevance = {}
        for source in set(event.source for event in self.events):
            source_events = [e for e in self.events if e.source == source]
            relevant_count = sum(1 for e in source_events if any(
                keyword in f"{e.title} {e.body}".lower() 
                for keyword in ['critical', 'vulnerability', 'outage', 'security', 'emergency']
            ))
            source_relevance[source] = relevant_count / len(source_events)
        
        insights['recommended_sources'] = [
            source for source, relevance in sorted(source_relevance.items(), key=lambda x: x[1], reverse=True)
            if relevance > 0.5
        ]
        
        # Content characteristics
        body_lengths = [len(e.body) for e in self.events if e.body.strip()]
        insights['content_characteristics'] = {
            'avg_body_length': sum(body_lengths) / len(body_lengths) if body_lengths else 0,
            'events_with_body': sum(1 for e in self.events if e.body.strip()),
            'events_without_body': sum(1 for e in self.events if not e.body.strip())
        }
        
        # Filtering strategies
        insights['filtering_strategies'] = [
            "Keyword-based filtering for security terms (CVE, vulnerability, exploit)",
            "Source-based filtering for high-relevance sources",
            "Content length filtering (events with detailed descriptions)",
            "Temporal filtering (recent events)",
            "Urgency indicator filtering (critical, emergency, immediate)"
        ]
        
        return insights
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """Run complete analysis of synthetic data"""
        if not self.load_data():
            return {}
        
        analysis = {
            'sources': self.analyze_sources(),
            'content_patterns': self.analyze_content_patterns(),
            'urgency_indicators': self.analyze_urgency_indicators(),
            'temporal_patterns': self.analyze_temporal_patterns(),
            'filtering_insights': self.generate_filtering_insights()
        }
        
        return analysis
    
    def save_analysis(self, analysis: Dict[str, Any], filename: str = None):
        """Save analysis results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"synthetic_data_analysis_{timestamp}.json"
        
        output_path = Path("data") / filename
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"📄 Analysis saved to: {output_path}")
        return output_path


def main():
    """Main function to run synthetic data analysis"""
    analyzer = SyntheticDataAnalyzer()
    
    print("🔍 Synthetic Data Analyzer - Newsfeed Platform")
    print("=" * 50)
    
    analysis = analyzer.run_full_analysis()
    
    if not analysis:
        print("❌ Analysis failed - could not load data")
        return
    
    # Print key insights
    print(f"\n📊 Analysis Results:")
    print(f"  Total events: {analysis['sources']['total_events']}")
    print(f"  Unique sources: {analysis['sources']['unique_sources']}")
    
    print(f"\n🔍 Source Distribution:")
    for source, count in analysis['sources']['source_distribution'].items():
        print(f"  {source}: {count} events")
    
    print(f"\n⚠️  Urgency Distribution:")
    for level, count in analysis['urgency_indicators']['urgency_distribution'].items():
        print(f"  {level}: {count} events")
    
    print(f"\n🔑 Top IT Keywords:")
    for keyword, count in list(analysis['content_patterns']['it_keyword_frequency'].items())[:10]:
        print(f"  {keyword}: {count} occurrences")
    
    print(f"\n💡 Filtering Insights:")
    for strategy in analysis['filtering_insights']['filtering_strategies']:
        print(f"  • {strategy}")
    
    # Save detailed analysis
    output_file = analyzer.save_analysis(analysis)
    print(f"\n📄 Detailed analysis available in: {output_file}")


if __name__ == "__main__":
    main() 