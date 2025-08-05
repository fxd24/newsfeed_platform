"""
Detailed Field Analyzer

This utility examines the specific fields, their types, and value ranges
from live news sources to understand what additional data we can capture
and extend the NewsEvent model with.
"""

import asyncio
import json
import logging
from collections import defaultdict, Counter
from datetime import datetime
from typing import Any, Dict, List, Set
from pathlib import Path

from src.sources.factory import SourceFactory
from src.config.config_manager import ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DetailedFieldAnalyzer:
    """Analyzer for detailed field examination from news sources"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.source_factory = SourceFactory()
        self.field_analysis: Dict[str, Dict[str, Any]] = {}
    
    async def analyze_source_fields(self, source_name: str) -> Dict[str, Any]:
        """Analyze fields and their values from a specific source"""
        logger.info(f"Analyzing fields for source: {source_name}")
        
        try:
            # Load configuration
            if not self.config_manager.load_from_file("config/sources.yaml"):
                logger.error("Failed to load configuration")
                return {}
            
            # Get source configuration
            source_config = self.config_manager.get_source_config(source_name)
            if not source_config:
                logger.error(f"Source '{source_name}' not found in configuration")
                return {}
            
            # Create news source and fetch raw data
            news_source = self.source_factory.create_source(source_config)
            raw_data = await news_source.fetcher.fetch(
                source_config.url,
                headers=source_config.headers or {}
            )
            
            # Analyze the raw data structure
            analysis = self._analyze_raw_fields(raw_data, source_name)
            
            await news_source.fetcher.close()
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing source {source_name}: {e}")
            return {'error': str(e)}
    
    def _analyze_raw_fields(self, raw_data: Any, source_name: str) -> Dict[str, Any]:
        """Analyze fields and their values in raw data"""
        analysis = {
            'source_name': source_name,
            'data_type': type(raw_data).__name__,
            'timestamp': datetime.now().isoformat(),
            'field_analysis': {},
            'value_ranges': {},
            'sample_data': {}
        }
        
        if isinstance(raw_data, dict):
            analysis.update(self._analyze_dict_fields(raw_data))
        elif isinstance(raw_data, list):
            analysis.update(self._analyze_list_fields(raw_data))
        
        return analysis
    
    def _analyze_dict_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze fields in dictionary structure"""
        analysis = {
            'top_level_fields': {},
            'nested_structures': {}
        }
        
        for key, value in data.items():
            field_info = self._analyze_field_value(key, value)
            analysis['top_level_fields'][key] = field_info
            
            # If it's a list of items, analyze the items
            if isinstance(value, list) and len(value) > 0:
                analysis['nested_structures'][key] = self._analyze_list_items(value)
        
        return analysis
    
    def _analyze_list_fields(self, data: List[Any]) -> Dict[str, Any]:
        """Analyze fields in list structure"""
        if len(data) == 0:
            return {'list_length': 0, 'item_analysis': {}}
        
        analysis = {
            'list_length': len(data),
            'item_types': list(set(type(item).__name__ for item in data)),
            'item_analysis': {}
        }
        
        # Analyze first few items to understand structure
        sample_items = data[:min(10, len(data))]
        
        if isinstance(sample_items[0], dict):
            analysis['item_analysis'] = self._analyze_list_items(sample_items)
        
        return analysis
    
    def _analyze_list_items(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze fields across list items"""
        if not items:
            return {}
        
        # Collect all unique field names
        all_fields = set()
        for item in items:
            if isinstance(item, dict):
                all_fields.update(item.keys())
        
        field_analysis = {}
        value_ranges = {}
        sample_data = {}
        
        for field in all_fields:
            field_values = []
            field_types = set()
            
            for item in items:
                if isinstance(item, dict) and field in item:
                    value = item[field]
                    field_values.append(value)
                    field_types.add(type(value).__name__)
            
            # Analyze this field
            field_info = self._analyze_field_values(field, field_values)
            field_analysis[field] = field_info
            
            # Store value ranges for enum-like fields
            if field_info['is_enum_like']:
                value_ranges[field] = field_info['unique_values']
            
            # Store sample data
            sample_data[field] = field_values[:3]  # First 3 values
        
        return {
            'fields': field_analysis,
            'value_ranges': value_ranges,
            'sample_data': sample_data,
            'total_items_analyzed': len(items)
        }
    
    def _analyze_field_value(self, field_name: str, value: Any) -> Dict[str, Any]:
        """Analyze a single field value"""
        return {
            'type': type(value).__name__,
            'value': value,
            'is_enum_like': False,
            'unique_values': [],
            'description': self._get_field_description(field_name)
        }
    
    def _analyze_field_values(self, field_name: str, values: List[Any]) -> Dict[str, Any]:
        """Analyze multiple values for a field"""
        if not values:
            return {
                'type': 'empty',
                'count': 0,
                'is_enum_like': False,
                'unique_values': [],
                'description': self._get_field_description(field_name)
            }
        
        # Filter out unhashable types for counting
        hashable_values = []
        unhashable_types = set()
        
        for value in values:
            try:
                # Try to make it hashable for counting
                if isinstance(value, (list, dict)):
                    # Convert to string representation for counting
                    hashable_values.append(str(value))
                    unhashable_types.add(type(value).__name__)
                else:
                    hashable_values.append(value)
            except (TypeError, ValueError):
                # If we can't make it hashable, convert to string
                hashable_values.append(str(value))
                unhashable_types.add(type(value).__name__)
        
        # Count occurrences
        value_counts = Counter(hashable_values)
        unique_values = list(value_counts.keys())
        
        # Determine if it's enum-like (limited set of values)
        is_enum_like = len(unique_values) <= 20 and all(
            isinstance(v, (str, int, bool)) for v in unique_values
        )
        
        # Get most common values
        most_common = value_counts.most_common(5)
        
        return {
            'type': type(values[0]).__name__,
            'count': len(values),
            'unique_count': len(unique_values),
            'is_enum_like': is_enum_like,
            'unique_values': unique_values,
            'most_common': most_common,
            'unhashable_types': list(unhashable_types),
            'description': self._get_field_description(field_name)
        }
    
    def _get_field_description(self, field_name: str) -> str:
        """Get description for common field names"""
        descriptions = {
            'id': 'Unique identifier for the item',
            'name': 'Human-readable name or title',
            'title': 'Title or headline',
            'body': 'Main content or description',
            'description': 'Detailed description',
            'summary': 'Brief summary',
            'status': 'Current status (e.g., investigating, resolved)',
            'impact': 'Impact level (e.g., minor, major, critical)',
            'created_at': 'Creation timestamp',
            'updated_at': 'Last update timestamp',
            'published_at': 'Publication timestamp',
            'resolved_at': 'Resolution timestamp',
            'started_at': 'Start timestamp',
            'monitoring_at': 'Monitoring start timestamp',
            'shortlink': 'Short URL link',
            'page_id': 'Reference to parent page',
            'incident_updates': 'List of incident updates',
            'components': 'Affected components',
            'reminder_intervals': 'Reminder configuration',
            'url': 'URL link',
            'link': 'URL link',
            'author': 'Author information',
            'category': 'Category or classification',
            'tags': 'Tags or labels',
            'priority': 'Priority level',
            'severity': 'Severity level',
            'type': 'Type classification',
            'source': 'Source information'
        }
        
        return descriptions.get(field_name, 'Unknown field')
    
    async def analyze_all_sources(self) -> Dict[str, Any]:
        """Analyze fields from all configured sources"""
        # Load configuration first
        if not self.config_manager.load_from_file("config/sources.yaml"):
            logger.error("Failed to load configuration")
            return {}
        
        source_configs = self.config_manager.get_enabled_source_configs()
        results = {}
        
        for source_config in source_configs:
            source_name = source_config.name
            results[source_name] = await self.analyze_source_fields(source_name)
            # Small delay to be respectful to APIs
            await asyncio.sleep(1)
        
        return results
    
    def save_analysis(self, analysis: Dict[str, Any], filename: str = None):
        """Save analysis results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detailed_field_analysis_{timestamp}.json"
        
        output_path = Path("data") / filename
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        logger.info(f"Analysis saved to {output_path}")
        return output_path
    
    def generate_news_event_extensions(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations for extending NewsEvent model"""
        extensions = {
            'recommended_fields': [],
            'source_specific_fields': {},
            'enum_fields': {},
            'field_mappings': {}
        }
        
        for source_name, source_analysis in analysis.items():
            if 'error' in source_analysis:
                continue
            
            source_extensions = {
                'fields': [],
                'enums': {},
                'mappings': {}
            }
            
            # Analyze nested structures (like incidents)
            nested = source_analysis.get('nested_structures', {})
            for container_name, container_data in nested.items():
                if 'fields' in container_data:
                    for field_name, field_info in container_data['fields'].items():
                        # Check if this is a valuable field
                        if self._is_valuable_field(field_name, field_info):
                            source_extensions['fields'].append({
                                'name': field_name,
                                'type': field_info['type'],
                                'description': field_info['description'],
                                'is_enum': field_info['is_enum_like']
                            })
                            
                            # Store enum values
                            if field_info['is_enum_like']:
                                source_extensions['enums'][field_name] = field_info['unique_values']
                            
                            # Store field mapping
                            source_extensions['mappings'][field_name] = {
                                'source_field': field_name,
                                'target_field': self._suggest_target_field(field_name),
                                'transformation': self._suggest_transformation(field_name, field_info)
                            }
            
            if source_extensions['fields']:
                extensions['source_specific_fields'][source_name] = source_extensions
        
        # Generate common field recommendations
        common_fields = self._find_common_fields(analysis)
        extensions['recommended_fields'] = common_fields
        
        return extensions
    
    def _is_valuable_field(self, field_name: str, field_info: Dict[str, Any]) -> bool:
        """Determine if a field is valuable for NewsEvent extension"""
        valuable_fields = {
            'status', 'impact', 'priority', 'severity', 'type', 'category',
            'components', 'tags', 'author', 'url', 'link', 'shortlink'
        }
        
        # Check if it's a known valuable field
        if field_name in valuable_fields:
            return True
        
        # Check if it's an enum-like field with meaningful values
        if field_info['is_enum_like'] and len(field_info['unique_values']) > 1:
            return True
        
        # Check if it's a timestamp field
        if 'time' in field_name.lower() or 'at' in field_name.lower():
            return True
        
        return False
    
    def _suggest_target_field(self, field_name: str) -> str:
        """Suggest target field name for NewsEvent model"""
        mappings = {
            'status': 'status',
            'impact': 'impact_level',
            'priority': 'priority',
            'severity': 'severity',
            'type': 'event_type',
            'category': 'category',
            'components': 'affected_components',
            'tags': 'tags',
            'author': 'author',
            'url': 'url',
            'link': 'url',
            'shortlink': 'short_url'
        }
        
        return mappings.get(field_name, f"extended_{field_name}")
    
    def _suggest_transformation(self, field_name: str, field_info: Dict[str, Any]) -> str:
        """Suggest transformation for field value"""
        if field_info['type'] == 'str':
            return 'string'
        elif field_info['type'] == 'int':
            return 'integer'
        elif field_info['type'] == 'bool':
            return 'boolean'
        elif 'time' in field_name.lower() or 'at' in field_name.lower():
            return 'datetime'
        else:
            return 'string'
    
    def _find_common_fields(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find fields that are common across multiple sources"""
        field_counts = Counter()
        field_info = {}
        
        for source_name, source_analysis in analysis.items():
            if 'error' in source_analysis:
                continue
            
            nested = source_analysis.get('nested_structures', {})
            for container_name, container_data in nested.items():
                if 'fields' in container_data:
                    for field_name, field_data in container_data['fields'].items():
                        field_counts[field_name] += 1
                        if field_name not in field_info:
                            field_info[field_name] = field_data
        
        # Return fields that appear in multiple sources
        common_fields = []
        for field_name, count in field_counts.most_common():
            if count >= 2:  # Appears in at least 2 sources
                common_fields.append({
                    'name': field_name,
                    'occurrence_count': count,
                    'type': field_info[field_name]['type'],
                    'description': field_info[field_name]['description'],
                    'is_enum': field_info[field_name]['is_enum_like']
                })
        
        return common_fields


async def main():
    """Main function to run detailed field analysis"""
    analyzer = DetailedFieldAnalyzer()
    
    print("🔍 Detailed Field Analyzer - Newsfeed Platform")
    print("=" * 50)
    
    # Analyze all sources
    print("\n📊 Analyzing fields from all configured sources...")
    analysis = await analyzer.analyze_all_sources()
    
    # Save detailed analysis
    output_file = analyzer.save_analysis(analysis)
    
    # Generate NewsEvent extension recommendations
    extensions = analyzer.generate_news_event_extensions(analysis)
    
    # Save extension recommendations
    extensions_file = Path("data") / f"news_event_extensions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(extensions_file, 'w') as f:
        json.dump(extensions, f, indent=2, default=str)
    
    # Print summary
    print(f"\n✅ Analysis complete!")
    print(f"📄 Detailed analysis: {output_file}")
    print(f"📄 Extension recommendations: {extensions_file}")
    
    print(f"\n📋 Summary:")
    for source_name, result in analysis.items():
        if 'error' in result:
            print(f"  ❌ {source_name}: {result['error']}")
        else:
            data_type = result.get('data_type', 'Unknown')
            nested_count = len(result.get('nested_structures', {}))
            print(f"  ✅ {source_name}: {data_type} with {nested_count} nested structures")
    
    # Print extension recommendations
    print(f"\n🔧 NewsEvent Extension Recommendations:")
    print(f"  Common fields across sources: {len(extensions['recommended_fields'])}")
    print(f"  Source-specific extensions: {len(extensions['source_specific_fields'])}")
    
    if extensions['recommended_fields']:
        print(f"\n📝 Recommended Common Fields:")
        for field in extensions['recommended_fields'][:5]:  # Show top 5
            print(f"  • {field['name']} ({field['type']}) - {field['description']}")
            print(f"    Appears in {field['occurrence_count']} sources")
    
    print(f"\n📄 Full extension recommendations available in: {extensions_file}")


if __name__ == "__main__":
    asyncio.run(main()) 