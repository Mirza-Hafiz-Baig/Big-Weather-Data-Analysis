"""
Weather Platform Dashboard - Backend
--------------------------------------
Flask app serving:
    - the dashboard page (map, filters, charts, admin panel)
    - a JSON API the frontend calls to fetch filtered posts and stats
    - admin endpoints to verify/reject reports

Setup:
    pip install flask pymongo

Run (with data_simulator.py and process_posts.py also running):
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

from datetime import datetime

from bson import ObjectId
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "weather_platform"
COLLECTION_NAME = "raw_posts"

app = Flask(__name__)
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]


def serialize_post(post):
    post["_id"] = str(post["_id"])
    if isinstance(post.get("timestamp"), datetime):
        post["timestamp"] = post["timestamp"].isoformat()
    if isinstance(post.get("processed_at"), datetime):
        post["processed_at"] = post["processed_at"].isoformat()
    return post


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/posts")
def get_posts():
    query = {}

    event = request.args.get("event")
    if event and event != "all":
        query["predicted_category"] = event

    city = request.args.get("city")
    if city and city != "all":
        query["city"] = city

    status = request.args.get("status")
    if status and status != "all":
        query["verification_status"] = status

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    if date_from or date_to:
        timestamp_filter = {}
        if date_from:
            timestamp_filter["$gte"] = datetime.fromisoformat(date_from)
        if date_to:
            timestamp_filter["$lte"] = datetime.fromisoformat(date_to)
        query["timestamp"] = timestamp_filter

    # only fully processed posts are useful to show on the dashboard
    query["fake_score"] = {"$ne": None}

    posts = list(collection.find(query).sort("timestamp", -1).limit(300))
    return jsonify([serialize_post(p) for p in posts])


@app.route("/api/stats")
def get_stats():
    pipeline = [
        {"$match": {"predicted_category": {"$exists": True}}},
        {"$group": {"_id": "$predicted_category", "count": {"$sum": 1}}},
    ]
    results = list(collection.aggregate(pipeline))
    return jsonify({r["_id"]: r["count"] for r in results})


@app.route("/api/cities")
def get_cities():
    cities = collection.distinct("city")
    return jsonify(sorted(cities))


@app.route("/api/verify/<post_id>", methods=["POST"])
def verify_post(post_id):
    collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"verification_status": "verified"}},
    )
    return jsonify({"success": True})


@app.route("/api/reject/<post_id>", methods=["POST"])
def reject_post(post_id):
    collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"verification_status": "rejected"}},
    )
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True)
