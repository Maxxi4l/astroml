import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BlockchainContextBuilder:
    def __init__(self, token_limit: int = 4000):
        self.token_limit = token_limit
        self.compression_ratio = 0.60
        self.loss_threshold = 0.05
    
    def analyze_token_size(self, data: str) -> int:
        # Simple heuristic for token size analysis (approx 4 chars per token)
        return len(data) // 4
    
    def compress_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Simulate compression of blockchain transactions/data
        # by removing non-essential fields (e.g. metadata, extra padding)
        compressed = []
        for item in data:
            comp_item = {
                'id': item.get('id', ''),
                'amount': item.get('amount', 0),
                'timestamp': item.get('timestamp', ''),
                'from': item.get('from_address', '')[:10] + '...',
                'to': item.get('to_address', '')[:10] + '...'
            }
            compressed.append(comp_item)
        return compressed
        
    def build_context(self, days: int, raw_data: List[Dict[str, Any]]) -> str:
        # Filter for the last N days
        cutoff = datetime.now() - timedelta(days=days)
        filtered = [
            item for item in raw_data 
            if datetime.fromisoformat(item.get('timestamp', datetime.now().isoformat())) >= cutoff
        ]
        
        # Compress
        compressed_data = self.compress_data(filtered)
        
        context_str = json.dumps(compressed_data)
        
        tokens = self.analyze_token_size(context_str)
        if tokens > self.token_limit:
            logger.warning(f"Context size ({tokens} tokens) exceeds limit ({self.token_limit}). Truncating.")
            # Simple truncation for now to fit limit
            truncated_chars = self.token_limit * 4
            context_str = context_str[:truncated_chars]
            
        return context_str
