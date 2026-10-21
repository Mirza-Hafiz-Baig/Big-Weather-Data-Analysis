"""
Weather Data Simulator
-----------------------
Generates fake "social media style" weather posts for the SIH prototype
and pushes them into a MongoDB collection every few seconds, simulating
a real-time incoming feed (#IMD-tagged posts, citizen reports, etc.)

Covers 3 event categories: rainfall, flooding, thunderstorm.

Setup:
    pip install pymongo faker

Run:
    python data_simulator.py

Make sure MongoDB is running locally (default: mongodb://localhost:27017)
or update MONGO_URI below to your Atlas connection string.
"""

import random
import time
from datetime import datetime, timezone

from faker import Faker
from pymongo import MongoClient

# ---------- CONFIG ----------
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "weather_platform"
COLLECTION_NAME = "raw_posts"
POST_INTERVAL_SECONDS = 3  # how often a new fake post is generated

fake = Faker("en_IN")

# A handful of real Indian cities with rough GPS so pins land in sensible places
CITIES = [
    {"city": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lon": 72.8777},
    {"city": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lon": 79.0882},
    {"city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707},
    {"city": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lon": 88.3639},
    {"city": "Guwahati", "state": "Assam", "lat": 26.1445, "lon": 91.7362},
    {"city": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lon": 77.5946},
    {"city": "Patna", "state": "Bihar", "lat": 25.5941, "lon": 85.1376},
    {"city": "Delhi", "state": "Delhi", "lat": 28.7041, "lon": 77.1025},
]

EVENT_TEMPLATES = {
    "rainfall": [
        "Heavy rain lashing {city} since morning, roads waterlogged near the market. #IMD #Rainfall",
        "Continuous rainfall in {city} for the last 3 hours, visibility low. #WeatherAlert #{city}Rains",
        "{city} witnessing moderate to heavy showers, IMD had issued a warning. #IMD #MonsoonUpdate",
    ],
    "flooding": [
        "Flooding reported near the river in {city}, several low-lying areas submerged. #FloodAlert #IMD",
        "Water level rising fast in {city}, families being evacuated from riverside colonies. #{state}Floods",
        "Streets in {city} flooded after overnight rain, vehicles stranded. #IMD #FloodWatch",
    ],
    "thunderstorm": [
        "Severe thunderstorm with lightning hit {city} this evening, trees uprooted. #IMD #Thunderstorm",
        "Dark clouds and heavy thunder over {city}, IMD orange alert in effect. #WeatherAlert",
        "Sudden thunderstorm in {city} caused a brief power outage in several areas. #IMD #{state}Weather",
    ],
}

SOURCES = ["twitter_sim", "citizen_report", "facebook_sim"]


def generate_fake_post():
    location = random.choice(CITIES)
    category = random.choice(list(EVENT_TEMPLATES.keys()))
    template = random.choice(EVENT_TEMPLATES[category])
    text = template.format(city=location["city"], state=location["state"])

    # small random jitter on GPS so pins aren't all stacked on one point
    lat = location["lat"] + random.uniform(-0.05, 0.05)
    lon = location["lon"] + random.uniform(-0.05, 0.05)

    post = {
        "text": text,
        "source": random.choice(SOURCES),
        "username": fake.user_name(),
        "city": location["city"],
        "state": location["state"],
        "location": {"type": "Point", "coordinates": [lon, lat]},  # GeoJSON format
        "timestamp": datetime.now(timezone.utc),
        "event_category": category,  # ground-truth label for demo purposes
        "media_url": fake.image_url() if random.random() < 0.4 else None,
        "hashtags": ["#IMD", f"#{category.capitalize()}"],
        "verification_status": "pending",
        "is_duplicate": False,
        "fake_score": None,  # to be filled in by the processing script
    }
    return post


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # geospatial index so location-based queries/filters work later
    collection.create_index([("location", "2dsphere")])

    print(f"Simulator running. Pushing a new post every {POST_INTERVAL_SECONDS}s. Ctrl+C to stop.")

    try:
        while True:
            post = generate_fake_post()
            result = collection.insert_one(post)
            print(f"[{post['timestamp'].isoformat()}] Inserted post {result.inserted_id} "
                  f"({post['event_category']} in {post['city']})")
            time.sleep(POST_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
