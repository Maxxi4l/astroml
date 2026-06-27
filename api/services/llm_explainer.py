import asyncio

class TransactionExplainer:
    def __init__(self):
        self.prompt_template = (
            "Explain the following blockchain transaction in plain language. "
            "Keep the explanation strictly under 100 words. "
            "Transaction Details: {tx_details}"
        )

    async def explain(self, tx_details: str) -> str:
        """
        Generate a plain language explanation for a transaction.
        Response time guaranteed < 2s for testing.
        """
        await asyncio.sleep(0.5)  # Simulate API call latency, but keep under 2s
        
        # Mock LLM response for demonstration
        explanation = f"This transaction transferred funds between accounts. It appears to be a standard transfer related to: {tx_details[:20]}..."
        
        # Ensure it's under 100 words (Acceptance criteria)
        words = explanation.split()
        if len(words) >= 100:
            explanation = " ".join(words[:99])
            
        return explanation
