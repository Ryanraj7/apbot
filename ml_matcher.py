import re
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class MLMatcher:
    def __init__(self, csv_path, model_name="all-MiniLM-L6-v2"):
        """Initialize ML Matcher"""
        self.df = pd.read_csv(csv_path, sep='|', header=None, names=['intent', 'response']).dropna()

        self.intents = self.df['intent'].astype(str).tolist()
        self.responses = self.df['response'].astype(str).tolist()

        print("[MLMatcher] Encoding all intents...")
        self.model = SentenceTransformer(model_name)
        self.intent_embeddings = self.model.encode(self.intents, show_progress_bar=False)

    def _match_single(self, text, threshold=0.55):
        """Match a single phrase"""
        if not text.strip():
            return None, 0.0

        user_embedding = self.model.encode([text])[0]
        similarities = cosine_similarity([user_embedding], self.intent_embeddings)[0]

        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]

        if best_score < threshold:
            return None, best_score

        return self.responses[best_idx], best_score

    def match(self, user_id, user_input, threshold=0.55):
        """
        Match user input with optional multi-intent splitting.
        Context storage is disabled here — handled in match_logic.py instead.
        """
        user_input = user_input.strip()
        parts = re.split(r'\s+(?:and|also|then|,|;)\s+', user_input, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip()]
        results = []

        for part in parts:
            resp, score = self._match_single(part, threshold)
            if resp:
                results.append((part, resp))

        if not results:
            return None, 0.0

        if len(results) == 1:
            return results[0][1], 1.0

        matched_intents = [p for p, _ in results]
        intent_embs = self.model.encode(matched_intents)
        sim_matrix = cosine_similarity(intent_embs)

        if np.mean(sim_matrix) > 0.65:
            return " ".join([r for _, r in results]), 1.0
        else:
            return "\n\n".join([f"**For:** {p}\n{r}" for p, r in results]), 1.0
