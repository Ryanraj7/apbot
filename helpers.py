import re
import string
import csv
from datetime import datetime
from nltk.stem import WordNetLemmatizer
from nltk.corpus import words
import nltk
import random

nltk.download('wordnet', quiet=True)
nltk.download('words', quiet=True)

lemmatizer = WordNetLemmatizer()
meaningful_words = set(words.words())
meaningful_words = {'agm', 'api', 'url', 'rfid', 'otp', 'id', 'pin'}


def normalize_command(text):
    text = text.lower().strip()
    text = re.sub(r"[’‘“”]", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s/\.]", "", text)  # Keep slashes and dots
    return text

def lemmatize_words(text):
    return set(lemmatizer.lemmatize(word) for word in text.split())

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

def pick_response(response_text):
    return random.choice(response_text.split('|')) if '|' in response_text else response_text

def is_meaningful(user_input):
    return len(user_input) >= 3 or user_input in meaningful_words
