import json
import re
from typing import Dict, List, Any, Union, Optional
import pandas as pd
from rapidfuzz import fuzz, process

class SearchEngine:
    """
    Search engine for NMBS API data that supports efficient searching across various data types
    """
    
    def __init__(self):
        self.indices = {}  # Cache for search indices
        self.search_cache = {}  # Cache for search results
    
    def build_index(self, data: List[Dict], field: str) -> Dict:
        """
        Build a search index for a specific field in the data
        
        Args:
            data: List of dictionaries containing the data
            field: Field name to index
            
        Returns:
            Dictionary mapping field values to indices in the data
        """
        index = {}
        for i, item in enumerate(data):
            if field in item:
                value = str(item[field])
                if value not in index:
                    index[value] = []
                index[value].append(i)
        return index
    
    def search_exact(self, data: List[Dict], field: str, value: str) -> List[Dict]:
        """
        Perform an exact match search on a field
        
        Args:
            data: List of dictionaries containing the data
            field: Field name to search in
            value: Value to search for
            
        Returns:
            List of dictionaries matching the search criteria
        """
        # Build or get index for efficient lookup
        index_key = f"{id(data)}:{field}"
        if index_key not in self.indices:
            self.indices[index_key] = self.build_index(data, field)
        
        index = self.indices[index_key]
        value_str = str(value)
        
        # Use index for O(1) lookup
        if value_str in index:
            return [data[i] for i in index[value_str]]
        return []
    
    def search_partial(self, data: List[Dict], field: str, value: str) -> List[Dict]:
        """
        Perform a partial match search on a field
        
        Args:
            data: List of dictionaries containing the data
            field: Field name to search in
            value: Value to search for
            
        Returns:
            List of dictionaries matching the search criteria
        """
        results = []
        value_lower = str(value).lower()
        
        for item in data:
            if field in item and item[field] is not None:
                item_value = str(item[field]).lower()
                if value_lower in item_value:
                    results.append(item)
        
        return results
    
    def search_fuzzy(self, data: List[Dict], field: str, value: str, threshold: int = 75) -> List[Dict]:
        """
        Perform a fuzzy match search on a field
        
        Args:
            data: List of dictionaries containing the data
            field: Field name to search in
            value: Value to search for
            threshold: Minimum similarity score (0-100)
            
        Returns:
            List of dictionaries matching the search criteria
        """
        results = []
        value_str = str(value)
        
        for item in data:
            if field in item and item[field] is not None:
                item_value = str(item[field])
                score = fuzz.partial_ratio(value_str.lower(), item_value.lower())
                if score >= threshold:
                    item['_score'] = score  # Add match score to results
                    results.append(item)
        
        # Sort by match score
        return sorted(results, key=lambda x: x.get('_score', 0), reverse=True)
    
    def search_realtime_data(self, 
                          data: Dict, 
                          search_field: str, 
                          search_value: str,
                          exact: bool = False) -> Dict:
        """
        Search in real-time GTFS data
        
        Args:
            data: GTFS real-time data dictionary
            search_field: Field name to search in
            search_value: Value to search for
            exact: Whether to perform exact matching
            
        Returns:
            Filtered GTFS real-time data
        """
        # Create a deep copy to avoid modifying the original
        result = {
            "header": data.get("header", {}),
            "entity": []
        }
        
        entities = data.get("entity", [])
        
        # Special handling for timestamp in header
        if search_field == "timestamp" and search_field in data.get("header", {}):
            header_timestamp = str(data["header"]["timestamp"])
            if (exact and header_timestamp == search_value) or (not exact and search_value in header_timestamp):
                return data
        
        # Handle id search at entity level
        if search_field == "id":
            for entity in entities:
                entity_id = entity.get("id", "")
                if (exact and entity_id == search_value) or (not exact and search_value in entity_id):
                    result["entity"].append(entity)
            return result
        
        # Handle stopId search in stopTimeUpdate
        if search_field == "stopId":
            for entity in entities:
                if "tripUpdate" in entity and "stopTimeUpdate" in entity["tripUpdate"]:
                    match_found = False
                    for update in entity["tripUpdate"]["stopTimeUpdate"]:
                        stop_id = update.get("stopId", "")
                        if (exact and stop_id == search_value) or (not exact and search_value in stop_id):
                            match_found = True
                            break
                    
                    if match_found:
                        result["entity"].append(entity)
            return result
        
        # Default case: return original data
        return data
    
    def search_planning_data(self,
                          data: List[Dict],
                          search_field: str,
                          search_value: str,
                          exact: bool = False) -> List[Dict]:
        """
        Search in planning data files
        
        Args:
            data: List of dictionaries containing planning data
            search_field: Field name to search in
            search_value: Value to search for
            exact: Whether to perform exact matching
            
        Returns:
            Filtered planning data
        """
        cache_key = f"{id(data)}:{search_field}:{search_value}:{exact}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        if exact:
            results = self.search_exact(data, search_field, search_value)
        elif search_field in ['stop_name', 'route_long_name', 'trip_headsign', 'translation']:
            # Use fuzzy search for text fields
            results = self.search_fuzzy(data, search_field, search_value)
        else:
            # Use partial match for other fields
            results = self.search_partial(data, search_field, search_value)
        
        # Cache results for future queries
        self.search_cache[cache_key] = results
        return results
    
    def execute_search(self,
                    data: Union[Dict, List[Dict]],
                    search_field: str,
                    search_value: str,
                    data_type: str = 'planning',
                    exact: bool = False,
                    limit: int = 1000) -> Union[Dict, List[Dict]]:
        """
        Execute a search on data
        
        Args:
            data: Data to search in (either GTFS real-time dictionary or planning data list)
            search_field: Field name to search in
            search_value: Value to search for
            data_type: Type of data ('realtime' or 'planning')
            exact: Whether to perform exact matching
            limit: Maximum number of results to return
            
        Returns:
            Filtered data
        """
        if data_type == 'realtime':
            results = self.search_realtime_data(data, search_field, search_value, exact)
        else:
            results = self.search_planning_data(data, search_field, search_value, exact)
            # Apply limit for planning data
            if isinstance(results, list) and len(results) > limit:
                results = results[:limit]
                
        return results
    
    def clear_cache(self):
        """Clear the search cache to free memory"""
        self.search_cache = {}
        self.indices = {}

# Create a global instance of the search engine
search_engine = SearchEngine()

def search_data(data, search_params, data_type='planning', limit=1000):
    """
    Search data based on parameters
    
    Args:
        data: Data to search in
        search_params: Dictionary of search parameters
        data_type: Type of data ('realtime' or 'planning')
        limit: Maximum number of results to return
        
    Returns:
        Filtered data
    """
    search_field = search_params.get('search')
    if not search_field:
        # No search requested, return original data
        return data
    
    search_value = search_params.get(search_field)
    if not search_value:
        # No search value provided, return original data
        return data
    
    exact = search_params.get('exact', '').lower() == 'true'
    
    return search_engine.execute_search(
        data=data,
        search_field=search_field,
        search_value=search_value,
        data_type=data_type,
        exact=exact,
        limit=int(search_params.get('limit', limit))
    )

def optimize_data_for_search(data, fields=None):
    """
    Optimize data for searching by pre-building indices
    
    Args:
        data: Data to optimize
        fields: List of fields to build indices for
        
    Returns:
        None
    """
    if not isinstance(data, list) or not data:
        return
    
    # If fields not provided, use all fields from first item
    if fields is None and data:
        fields = data[0].keys()
    
    # Build indices for specified fields
    for field in fields:
        search_engine.build_index(data, field)
