import pandas as pd
import numpy as np
import random
import re
import os
import string
import csv
from datetime import datetime
from difflib import get_close_matches
import Levenshtein
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.stem import WordNetLemmatizer
from helpers import is_meaningful, save_log_csv
from collections import defaultdict

lemmatizer = WordNetLemmatizer()

# Context tracking
user_context = {}
user_last_action = {}
user_context = defaultdict(dict)

# Strict hardcoded responses
strict_responses = {
    "add asset": "Click Admin - Asset - Manage asset - Fill the form and save.",
    "add attribute": "You can add multiple attributes by clicking Admin - Asset - Manage attributes.",
    "add location": "Click Admin - Location - Add - Fill the details and save.",
    "edit asset": "Go to Admin - Asset - Manage asset - Edit or update details.",
    "edit attribute": "Go to Admin - Asset - Manage attributes - Edit or update.",
    "edit location": "Go to Admin - Location - Manage - Edit or update details.",
    "delete asset": "Go to Admin - Asset - Delete - Confirm to delete.",
    "delete attribute": "Go to Admin - Asset - Manage attributes - Delete attribute.",
    "delete location": "Go to Admin - Location - Delete - Confirm to delete.",
    "manage asset": "Go to Admin - Asset - Manage asset - Edit or update details.",
    "manage attribute": "Go to Admin - Asset - Manage attributes - Edit or update.",
    "manage location": "Go to Admin - Location - Manage - Edit or update details."
}

# Broad action clarification prompts
broad_terms = {
    "add": "Do you want to add asset, attribute, location, or asset type?",
    "edit": "Do you want to edit asset, attribute, location, or asset type?",
    "update": "Do you want to edit asset, attribute, location, or asset type?",
    "delete": "Do you want to delete asset, attribute, location, or asset type?",
    "manage": "Do you want to manage asset, attribute, location, or asset type?"
}

# Load responses and model
responses = {}
intent_texts = []

def normalize_command(text):
    text = text.lower().strip()
    text = re.sub(r"[’‘“”]", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return text

def lemmatize_words(text):
    return set(lemmatizer.lemmatize(word) for word in text.split())

def load_responses():
    global responses, intent_texts
    # Locate responses.csv in the same folder as this file
    base = os.path.dirname(__file__)                  # …\APbot
    csv_path = os.path.join(base, "responses.csv")    # …\APbot\responses.csv

    df = pd.read_csv(csv_path, delimiter="|", skipinitialspace=True)
    # Drop any rows with missing intent or response
    df.dropna(subset=["intent", "response"], inplace=True)

    # Normalize
    df["intent"]   = df["intent"].apply(lambda x: normalize_command(str(x)))
    df["response"] = df["response"].astype(str).str.strip()

    # Build dicts
    responses.clear()
    responses.update(dict(zip(df["intent"], df["response"])))
    intent_texts.clear()
    intent_texts.extend(responses.keys())

    extra = {}
    for intent, resp in list(responses.items()):
     if "/" in intent:
      suffix = intent.split("/")[-1].strip()
      for part in intent.split("/"):
        part = part.strip()
        if part:
            new_key = f"{part} {suffix}" if part != suffix else part
            if new_key.lower() not in [k.lower() for k in responses]:
                extra[new_key] = resp
    responses.update(extra)

    # rebuild intent_texts
    intent_texts.clear()
    intent_texts.extend(responses.keys())

load_responses()

distilbert_model = SentenceTransformer("all-MiniLM-L6-v2")
distilbert_embeddings = distilbert_model.encode(intent_texts)

def save_log_csv(user_input, bot_response):
    with open('conversation_logs.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), user_input, bot_response])

def preprocess_input(user_input):
    user_input = str(user_input).lower().strip()
    user_input = re.sub(r"([a-z])([A-Z])", r"\1 \2", user_input)
    user_input = user_input.replace("_", " ")
    user_input = re.sub(r"[^a-zA-Z0-9\s]", "", user_input)
    return user_input.strip(), len(user_input.strip().split())

def handle_broad_terms(user_id, user_input_cleaned):
    for keyword, reply in broad_terms.items():
        if keyword in user_input_cleaned.split():
            return reply
    return None

def get_closest_match(input_text, valid_terms, return_score=False):
    scores = [(term, Levenshtein.ratio(input_text, term)) for term in valid_terms]
    scores.sort(key=lambda x: x[1], reverse=True)
    if not scores:
        return (None, 0.0) if return_score else None
    best_match, score = scores[0]
    return (best_match, score) if return_score else best_match

def is_garbage_input(text: str) -> bool:
    """Return True if text is likely meaningless gibberish."""
    if not text or len(text) < 2:
        return True
    # If very long with no spaces, probably a paste of junk
    if len(text) > 20 and ' ' not in text:
        return True
    # If fewer than half the chars are letters
    if sum(c.isalpha() for c in text) / len(text) < 0.5:
        return True
    return False

def is_question(text: str) -> bool:
    """Return True if text looks like a question."""
    qwords = ['how', 'what', 'when', 'where', 'why', 'which', 'who', 'can you']
    return text.strip().endswith('?') or any(text.startswith(w + ' ') for w in qwords)

def handle_question(text: str) -> str:
    """Handle a few canned question patterns before intent matching."""
    t = text.lower()
    if 'how to add asset' in t:
        return "Click Admin - Asset - Manage asset - Fill the form and save."
    if 'how to delete asset' in t:
        return "Go to Admin - Asset - Delete - Confirm to delete."
    if re.fullmatch(r'(help|support)', t.strip()):
        return "Please choose the software you need assistance with:\nServer\nAdapter\nAGM"
    # Add more patterns as needed...
    return None


# ✅ MASTER FUNCTION
# Global memory for storing user's last broad action
user_last_action = {}

def get_best_match(user_id, user_input):
    import re

    original = user_input.strip()
    low = original.lower()
    print(f"\nMatching: '{original}' → '{low}'")

    # Prepare
    valid = set(responses.keys()) | set(strict_responses.keys())
    cleaned, wc = preprocess_input(original)
    norm = normalize_command(cleaned)

    # ♻ CONTEXT CHECK FIRST (follow-up handling)
    last_action = user_context[user_id].get("action")
    if last_action:
        combined_intent = f"{last_action} {norm}"
        if combined_intent in valid:
            resp = responses.get(combined_intent) or strict_responses.get(combined_intent)
            if isinstance(resp, str):
                user_context[user_id].clear()  # Clear only after successful match
                choice = random.choice([o.strip() for o in resp.split("|") if o.strip()])
                save_log_csv(original, choice)
                return choice
        # If combined intent not found, check if norm alone is a valid response to last_action
        elif norm in valid and norm in broad_terms.get(last_action, {}):
            resp = responses.get(norm) or strict_responses.get(norm)
            if isinstance(resp, str):
                user_context[user_id].clear()
                choice = random.choice([o.strip() for o in resp.split("|") if o.strip()])
                save_log_csv(original, choice)
                return choice

    # 🔁 Fallback messages
    fallback_options = [
        "I couldn't find an answer to your query. Type 'issue' to choose the software you need help.",
        "Sorry, I couldn't match that. Type 'issue' to pick the software you're asking about.",
        "Hmm, I'm not sure how to respond to that. Try typing 'issue' to get help with Server, Adapter, or AGM."
    ]

    # ✅ 1. Garbage Input Detection
    if is_garbage_input(low):
        fallback_message = random.choice(fallback_options)
        save_log_csv(original, fallback_message)
        return fallback_message

    # ✅ 2. Natural Language Question Handling
    if is_question(low):
        ans = handle_question(original)
        if ans:
            save_log_csv(original, ans)
            return ans
              
    # ✅ 3. SEMANTIC MATCH (DistilBERT — moved earlier)
    emb = distilbert_model.encode([norm])
    sims = cosine_similarity(emb, distilbert_embeddings)[0]
    idx = np.argmax(sims)
    best_intent = intent_texts[idx]
    conf = sims[idx] * 100
    strong_threshold = 70 if wc <= 2 else 80

    if conf >= strong_threshold and best_intent in valid:
        user_context[user_id].clear()
        resp = responses.get(best_intent) or strict_responses.get(best_intent)
        if isinstance(resp, str):
            choice = random.choice([o.strip() for o in resp.split("|") if o.strip()])
            save_log_csv(original, choice)
            return choice
        
    # ===== RULE-BASED LAYERS =====
    # 4. Strict match (exact)
    for intent, resp in strict_responses.items():
        if low == intent.lower():
            user_context[user_id].clear()
            save_log_csv(original, resp)
            return resp

    # 5. Exact CSV intent match
    for intent, opts in responses.items():
        if low == intent.lower() and isinstance(opts, str):
            user_context[user_id].clear()
            choice = random.choice([o.strip() for o in opts.split("|") if o.strip()])
            save_log_csv(original, choice)
            return choice

    # 6. Response-option match
    for intent, opts in responses.items():
        if isinstance(opts, str):
            opt_list = [o.strip().lower() for o in opts.split("|") if o.strip()]
            if low in opt_list:
                user_context[user_id].clear()
                choice = random.choice([o.strip() for o in opts.split("|") if o.strip()])
                save_log_csv(original, choice)
                return choice

    # 7. Broad action prompt (ONLY if no context exists)
    if not last_action:  # Only trigger broad terms if no existing context
        for broad_word in broad_terms:
            if low == broad_word:
                user_context[user_id]['action'] = broad_word
                reply = broad_terms[broad_word]
                save_log_csv(original, reply)
                return reply

    # 8. Follow-up: last action + noun (redundant with first check, can be removed)

    # 9. Lemma-subset match
    user_lem = lemmatize_words(norm)
    matches = []
    for intent in valid:
        il = lemmatize_words(intent)
        if len(il) >= 2 and il.issubset(user_lem):
            matches.append((intent, len(il)))
    if matches:
        best = max(matches, key=lambda x: x[1])[0]
        user_context[user_id].clear()
        resp = responses.get(best) or strict_responses.get(best)
        if isinstance(resp, str):
            choice = random.choice([o.strip() for o in resp.split("|") if o.strip()])
            save_log_csv(original, choice)
            return choice

    # 10. Prefix match
    for intent in valid:
        if norm.startswith(intent) or intent.startswith(norm):
            if len(intent.split()) == 1 and len(norm.split()) >= 3:
                continue
            resp = responses.get(intent) or strict_responses.get(intent)
            if isinstance(resp, str):
                user_context[user_id].clear()
                choice = random.choice([o.strip() for o in resp.split("|") if o.strip()])
                save_log_csv(original, choice)
                return choice

    # 10.5 Inclusion/suffix fallback
    norm_low = norm.lower()
    for key in valid:
        key_low = key.lower()
        if norm_low.endswith(key_low) or key_low in norm_low:
            if len(key_low.split()) == 1 and len(norm.split()) >= 3:
                continue
            resp = responses.get(key) or strict_responses.get(key)
            if isinstance(resp, str):
                user_context[user_id].clear()
                choice = random.choice([o.strip() for o in resp.split("|") if o.strip()])
                save_log_csv(original, choice)
                return choice

    # 11. Fuzzy match
    if 'get_closest_match' in globals():
        closest, score = get_closest_match(norm, list(valid), return_score=True)
        if closest and score > 70:
            user_context[user_id].clear()
            resp = responses.get(closest) or strict_responses.get(closest)
            if isinstance(resp, str):
                choice = random.choice([o.strip() for o in resp.split("|") if o.strip()])
                save_log_csv(original, choice)
                return choice
            
    # FINAL FALLBACK - If we have context, give more specific message
    if last_action:
        fallback_message = f"I'm not sure what you want to {last_action}. Please try again."
    else:
        fallback_message = random.choice(fallback_options)
        
    save_log_csv(original, fallback_message)
    return fallback_message

