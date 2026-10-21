"""
Weather Post Processor
-----------------------
Reads unprocessed posts from MongoDB (inserted by data_simulator.py),
and enriches each one with:
    - predicted_category  : ML/keyword-based event classification
    - is_duplicate         : text-similarity based duplicate flag
    - fake_score            : heuristic likelihood the post is fake/untrusted
    - verification_status  : auto-set to "flagged" / "duplicate" / "pending"

Runs continuously, polling for new posts every few seconds.

Setup:
    pip install pymongo scikit-learn

Run (after data_simulator.py is already running in another terminal):
    python process_posts.py
"""

import time
from datetime import datetime, timezone

from difflib import SequenceMatcher

from pymongo import MongoClient

# ---------- CONFIG ----------
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "weather_platform"
COLLECTION_NAME = "raw_posts"
POLL_INTERVAL_SECONDS = 5
DUPLICATE_SIMILARITY_THRESHOLD = 0.75
FAKE_SCORE_FLAG_THRESHOLD = 0.6
RECENT_WINDOW = 200  # how many recent posts to compare against for duplicates

# Keyword sets for simple, explainable event categorization.
# (Swap this for a trained classifier later if you want — this is enough
# for a prototype demo and is easy to explain to a panel.)
CATEGORY_KEYWORDS = {
    "rainfall": ["rain", "rainfall", "showers", "monsoon", "drizzle"],
    "flooding": ["flood", "flooding", "waterlogged", "submerged", "evacuat", "water level"],
    "thunderstorm": ["thunderstorm", "thunder", "lightning", "storm"],
}


def predict_category(text: str) -> str:
    text_lower = text.lower()
    scores = {
        category: sum(1 for kw in keywords if kw in text_lower)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best_category = max(scores, key=scores.get)
    if scores[best_category] == 0:
        return "uncategorized"
    return best_category


def compute_fake_score(post: dict) -> float:
    """
    Simple explainable heuristic (0 = looks trustworthy, 1 = highly suspect).
    Swap/extend with a trained model later — for the demo, being able to
    explain *why* a score was given is more valuable than raw accuracy.
    """
    score = 0.0

    if not post.get("media_url"):
        score += 0.3  # no supporting photo/video

    if len(post.get("text", "")) < 40:
        score += 0.2  # very short, low-detail report

    if not post.get("hashtags"):
        score += 0.2  # no hashtags/context tags at all

    if post.get("source") == "citizen_report" and not post.get("media_url"):
        score += 0.2  # unverified citizen report with no evidence attached

    return round(min(score, 1.0), 2)


def text_similarity(a: str, b: str) -> float:
    """Pure-Python text similarity (0 to 1) using difflib — no external ML library needed."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_duplicates(collection):
    """
    Compares the text of recent posts pairwise using difflib's sequence matcher.
    Flags posts that are near-identical to another post already in the window.
    """
    recent_posts = list(
        collection.find({}, {"_id": 1, "text": 1})
        .sort("timestamp", -1)
        .limit(RECENT_WINDOW)
    )

    if len(recent_posts) < 2:
        return set()

    duplicate_ids = set()
    for i in range(len(recent_posts)):
        for j in range(i + 1, len(recent_posts)):
            similarity = text_similarity(recent_posts[i]["text"], recent_posts[j]["text"])
            if similarity >= DUPLICATE_SIMILARITY_THRESHOLD:
                # mark the newer one (lower index, since sorted by newest first) as the duplicate
                duplicate_ids.add(recent_posts[i]["_id"])

    return duplicate_ids


def process_new_posts(collection):
    # "unprocessed" = fake_score still None, set by the simulator on insert
    unprocessed = list(collection.find({"fake_score": None}))
    if not unprocessed:
        return 0

    duplicate_ids = find_duplicates(collection)

    for post in unprocessed:
        predicted_category = predict_category(post["text"])
        fake_score = compute_fake_score(post)
        is_duplicate = post["_id"] in duplicate_ids

        if is_duplicate:
            verification_status = "duplicate"
        elif fake_score >= FAKE_SCORE_FLAG_THRESHOLD:
            verification_status = "flagged"
        else:
            verification_status = "pending"  # still needs human review in the admin panel

        collection.update_one(
            {"_id": post["_id"]},
            {
                "$set": {
                    "predicted_category": predicted_category,
                    "category_match": predicted_category == post.get("event_category"),
                    "is_duplicate": is_duplicate,
                    "fake_score": fake_score,
                    "verification_status": verification_status,
                    "processed_at": datetime.now(timezone.utc),
                }
            },
        )

        print(
            f"Processed {post['_id']} [{post.get('city')}]: predicted={predicted_category} "
            f"(true={post.get('event_category')}), fake_score={fake_score}, "
            f"duplicate={is_duplicate}, status={verification_status}"
        )

    return len(unprocessed)


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    print(f"Processor running. Polling every {POLL_INTERVAL_SECONDS}s. Ctrl+C to stop.")

    try:
        while True:
            count = process_new_posts(collection)
            if count == 0:
                print("No new posts to process, waiting...")
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nProcessor stopped.")
    finally:
        client.close()


if __name__ == "__main__":
    main()