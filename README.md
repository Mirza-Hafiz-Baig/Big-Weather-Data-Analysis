# National Big Weather Data Analytics: Weather Event Register

A National Weather Big Data Analytics Platform prototype built for Smart India Hackathon 2026. It collects weather-related posts (rainfall, flooding, thunderstorms), classifies them, flags suspicious or duplicate reports, and shows everything on a live dashboard where an admin can verify or reject reports.

> **Note:** The incoming posts are simulated. A data simulator generates social-media-style posts for Indian cities so the full pipeline can be demonstrated without live API access.

## How it works

```
data_simulator.py  ->  MongoDB  ->  process_posts.py  ->  MongoDB  ->  app.py (Flask)  ->  Dashboard
 (fake live feed)                    (classify, dedupe,                  (JSON API + admin)
                                      fake-score)
```

1. **`data_simulator.py`** generates a new fake post every 3 seconds (text, city, GPS coordinates, source, hashtags, optional media) and inserts it into MongoDB.
2. **`process_posts.py`** polls for unprocessed posts and adds:
   - `predicted_category`: keyword-based event classification (rainfall / flooding / thunderstorm)
   - `is_duplicate`: flagged using text similarity (`difflib`, threshold 0.75)
   - `fake_score`: an explainable 0-1 heuristic (missing media, very short text, no hashtags, unverified citizen report)
   - `verification_status`: `duplicate`, `flagged`, or `pending`
3. **`app.py`** is a Flask backend that serves the dashboard and a JSON API.

## Features

- Filter posts by event type, city, verification status, and date range
- Event statistics via a MongoDB aggregation pipeline
- GeoJSON locations with a `2dsphere` index for map-based views
- Interactive map (Leaflet) with colour-coded event markers, and a Chart.js bar chart of reports by event type
- Live dashboard that auto-refreshes every 8 seconds
- Admin queue to verify or reject reports
- Rule-based scoring chosen so each decision can be explained

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard page |
| GET | `/api/posts` | Filtered posts (`event`, `city`, `status`, `date_from`, `date_to`) |
| GET | `/api/stats` | Post count per predicted category |
| GET | `/api/cities` | List of cities |
| POST | `/api/verify/<post_id>` | Mark a post as verified |
| POST | `/api/reject/<post_id>` | Mark a post as rejected |

## Tech stack

Python, Flask, MongoDB (PyMongo), Faker, difflib, HTML/CSS/JavaScript, Leaflet, Chart.js

## Project structure

```
.
├── app.py
├── data_simulator.py
├── process_posts.py
└── templates/
    └── dashboard.html
```

## Setup

**Requirements:** Python 3.8+ and MongoDB running locally on `mongodb://localhost:27017`.

```bash
pip install flask pymongo faker
```

Run each script in its own terminal:

```bash
python data_simulator.py
python process_posts.py
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Limitations

- Posts are simulated, not collected from real social media.
- Classification and fake detection are keyword and heuristic based, not a trained ML model.
- Duplicate detection compares recent posts pairwise, so it is not built for large scale.

## Future improvements

- Connect real data sources (social media APIs, IMD feeds)
- Replace the heuristics with a trained classifier
- Faster duplicate detection (e.g. TF-IDF or embeddings)
- Authentication for the admin panel

## Explanation of prototype
https://youtu.be/7ovA-PxZVec?si=24s6dU8a2x6rZ-p0
🗺️ Project Roadmap

* [x]	Simulated weather report generation
* [x]	Automated event classification
* [x]	Duplicate report detection
* [x]	Suspicious report scoring
* [x]	Interactive dashboard and geospatial visualization
* [ ]	Real-time weather data integration
* [ ]	AI-powered report verification
* [ ]	Multilingual report processing
* [ ]	Automated regional risk assessment
* [ ]	Scalable national weather monitoring


🧠 Weather Event Correlation

A future extension of the platform could correlate reports using geographical proximity, timestamps, event categories, and textual similarity.

How It Would Work

1. Collect reports from nearby geographical locations.
2. Compare their timestamps and predicted event categories.
3. Identify clusters of reports that may describe the same incident.
4. Assign a common event identifier to related reports.
5. Display the resulting event clusters on the dashboard.

Expected benefit: Transform isolated weather reports into a more coherent view of developing weather incidents.

This capability is proposed for future development and is not part of the current prototype unless implemented separately.

🌐 Multilingual Weather Intelligence

Weather reports may be submitted in different Indian languages, including Hindi, Marathi, Bengali, and English.

A future version could incorporate multilingual text processing to:

* Recognize weather-related keywords across supported languages.
* Translate reports into a common language for analysis.
* Classify incidents independently of the language used.
* Preserve original text for administrative verification.

This enhancement could make the platform more accessible to users across different regions of India.

