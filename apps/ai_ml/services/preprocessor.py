"""
Text preprocessing for complaint classification.
Handles English and transliterated Hindi/regional text.
"""
import re
import unicodedata


# Common stopwords (English + Hinglish transliterations)
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "has", "have", "had",
    "be", "been", "being", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "to", "of", "in",
    "on", "at", "by", "for", "with", "from", "and", "or", "but", "not",
    "this", "that", "these", "those", "i", "my", "we", "our", "you",
    "your", "he", "she", "it", "they", "their", "there", "here",
    "hai", "hain", "ka", "ki", "ke", "ko", "se", "mein", "par", "aur",
    "nahi", "nahin", "koi", "kuch", "ab", "jo", "jab", "tab", "ek",
}


def preprocess(text: str) -> str:
    """
    Clean and normalize complaint text for classification.
    Returns lowercased, punctuation-stripped, stopword-filtered text.
    """
    if not text:
        return ""

    # Normalize unicode (handle Devanagari transliterations, accents)
    text = unicodedata.normalize("NFKC", text)

    # Lowercase
    text = text.lower()

    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)

    # Remove phone numbers
    text = re.sub(r"\+?\d[\d\s\-]{8,}", " ", text)

    # Keep letters, digits, and spaces; strip punctuation
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\d+", " ", text)  # strip bare numbers

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Remove stopwords
    tokens = [w for w in text.split() if w not in STOPWORDS and len(w) > 1]

    return " ".join(tokens)
