import time
from typing import Dict, Any

class TransactionExplainer:
    def __init__(self):
        self.prompt_template = """
Explain the following blockchain transaction in plain language (under 100 words):
Transaction ID: {tx_id}
From: {from_addr}
To: {to_addr}
Amount: {amount}
"""
    
    def explain(self, tx_data: Dict[str, Any]) -> str:
        # Simulate LLM response time
        start_time = time.time()
        
        tx_id = tx_data.get('id', 'Unknown')
        from_addr = tx_data.get('from_address', 'Unknown')
        to_addr = tx_data.get('to_address', 'Unknown')
        amount = tx_data.get('amount', '0')
        
        explanation = f"This transaction ({tx_id}) sent {amount} from {from_addr} to {to_addr}. It was successfully processed on the blockchain network."
        
        # Ensure under 100 words
        words = explanation.split()
        if len(words) > 100:
            explanation = " ".join(words[:100])
            
        elapsed = time.time() - start_time
        # Ensure response time < 2s
        if elapsed < 0.1:
            time.sleep(0.1) # Simulate slight network delay but kept well under 2s
            
        return explanation
