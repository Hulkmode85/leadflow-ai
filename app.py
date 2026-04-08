"""
LeadFlow AI — Autonomous Lead-Gen & Qualifier Engine
MVP: Flask app with mock Google Maps data + Claude Haiku scoring
"""

import os
import csv
import io
import json
import random
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, redirect

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

# ---------------------------------------------------------------------------
# Mock data generator (used when Google Maps API key is not set)
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Bright", "Sunrise", "Valley", "Premier", "Elite", "Pacific", "Golden",
    "Summit", "Apex", "Harbor", "Cedar", "Oak", "Silver", "Metro", "Liberty",
    "Heritage", "Cascade", "Cornerstone", "Pinnacle", "Sterling"
]

BUSINESS_SUFFIXES = {
    "dentists": ["Dental", "Dentistry", "Dental Care", "Dental Group", "Smiles"],
    "plumbers": ["Plumbing", "Plumbing & Heating", "Pipe Works", "Drain Solutions"],
    "restaurants": ["Kitchen", "Bistro", "Grill", "Eatery", "Cafe"],
    "lawyers": ["Law Group", "Legal Services", "Attorneys", "Law Office"],
    "gyms": ["Fitness", "Gym", "Training Center", "CrossFit", "Athletic Club"],
    "salons": ["Salon", "Hair Studio", "Beauty Bar", "Cuts & Color"],
    "chiropractors": ["Chiropractic", "Spine & Wellness", "Chiropractic Center"],
    "accountants": ["Accounting", "CPA Group", "Tax Services", "Financial"],
    "default": ["Services", "Solutions", "Group", "Professionals", "Associates"],
}

REVIEW_TEMPLATES = [
    "Great service, very professional staff.",
    "Waited too long but the work was decent.",
    "Absolutely amazing experience. Highly recommend!",
    "Average. Nothing special but gets the job done.",
    "Terrible experience. Will not return.",
    "Friendly team, fair pricing. Would come back.",
    "The best in the area, hands down.",
    "Overpriced for what you get.",
    "Clean facility, knowledgeable staff.",
    "They need a better website and online booking.",
    "Hard to reach by phone. No online presence at all.",
    "Found them on Google, easy to book, great results.",
    "Their social media is outdated. Service was okay.",
    "No website, no email — I had to just walk in.",
    "Modern office, they use the latest technology.",
]


def _seed(query: str, i: int) -> random.Random:
    h = hashlib.md5(f"{query}:{i}".encode()).hexdigest()
    return random.Random(h)


def _detect_niche(query: str) -> str:
    q = query.lower()
    for niche in BUSINESS_SUFFIXES:
        if niche in q:
            return niche
    return "default"


def generate_mock_leads(query: str, count: int = 15) -> list[dict]:
    niche = _detect_niche(query)
    suffixes = BUSINESS_SUFFIXES[niche]
    leads = []
    for i in range(count):
        rng = _seed(query, i)
        first = rng.choice(FIRST_NAMES)
        suffix = rng.choice(suffixes)
        name = f"{first} {suffix}"
        rating = round(rng.uniform(1.5, 5.0), 1)
        review_count = rng.randint(2, 320)
        has_website = rng.random() > 0.3
        has_email = rng.random() > 0.4
        phone = f"({rng.randint(200,999)}) {rng.randint(200,999)}-{rng.randint(1000,9999)}"
        domain = name.lower().replace(" ", "").replace("&", "")
        website = f"https://{domain}.com" if has_website else None
        email = f"info@{domain}.com" if has_email else None
        reviews = [rng.choice(REVIEW_TEMPLATES) for _ in range(min(review_count, 5))]
        leads.append({
            "name": name, "phone": phone, "email": email, "website": website,
            "rating": rating, "review_count": review_count, "sample_reviews": reviews,
            "address": f"{rng.randint(100,9999)} {rng.choice(['Main','Oak','Elm','Broadway','Market'])} St",
        })
    return leads


def fetch_google_leads(query: str, count: int = 15) -> list[dict]:
    try:
        import requests
    except ImportError:
        return generate_mock_leads(query, count)
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": GOOGLE_MAPS_API_KEY}
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    if data.get("status") != "OK":
        return generate_mock_leads(query, count)
    leads = []
    for place in data.get("results", [])[:count]:
        place_id = place.get("place_id", "")
        detail = {}
        if place_id:
            detail_url = "https://maps.googleapis.com/maps/api/place/details/json"
            detail_params = {"place_id": place_id, "fields": "formatted_phone_number,website,reviews", "key": GOOGLE_MAPS_API_KEY}
            dr = requests.get(detail_url, params=detail_params, timeout=10)
            detail = dr.json().get("result", {})
        reviews_raw = detail.get("reviews", [])
        sample_reviews = [r.get("text", "")[:200] for r in reviews_raw[:5]]
        leads.append({
            "name": place.get("name", "Unknown"), "phone": detail.get("formatted_phone_number"),
            "email": None, "website": detail.get("website"), "rating": place.get("rating", 0),
            "review_count": place.get("user_ratings_total", 0), "sample_reviews": sample_reviews,
            "address": place.get("formatted_address", ""),
        })
    return leads


def score_leads_with_haiku(leads: list[dict], niche: str) -> list[dict]:
    if not ANTHROPIC_API_KEY:
        return _score_heuristic(leads)
    try:
        import anthropic
    except ImportError:
        return _score_heuristic(leads)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    scored = []
    for lead in leads:
        prompt = f"""Score this business lead from 1 to 10 for outreach potential.

Business: {lead['name']}
Niche: {niche}
Rating: {lead['rating']}/5 ({lead['review_count']} reviews)
Has website: {"Yes — " + lead['website'] if lead['website'] else "No"}
Has email: {"Yes" if lead['email'] else "No"}
Sample reviews: {json.dumps(lead['sample_reviews'][:3])}

Score criteria (weight equally):
1. Review sentiment — negative reviews = more pain points = higher need
2. Online presence quality — no website/email = higher need for digital help
3. Likely need for AI automation — high review volume + complaints about wait times, booking, responsiveness = high need

Return ONLY a JSON object with these exact keys:
{{"score": <int 1-10>, "reasoning": "<one sentence>", "approach": "<one sentence recommended outreach angle>"}}"""
        try:
            msg = client.messages.create(model="claude-haiku-4-20250414", max_tokens=200, messages=[{"role": "user", "content": prompt}])
            result = json.loads(msg.content[0].text)
            lead["score"] = result["score"]
            lead["reasoning"] = result["reasoning"]
            lead["approach"] = result["approach"]
        except Exception:
            lead = _score_single_heuristic(lead)
        scored.append(lead)
    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    return scored


def _score_heuristic(leads: list[dict]) -> list[dict]:
    return sorted([_score_single_heuristic(lead) for lead in leads], key=lambda x: x["score"], reverse=True)


def _score_single_heuristic(lead: dict) -> dict:
    score = 5
    if not lead.get("website"): score += 2
    if not lead.get("email"): score += 1
    if lead["rating"] < 3.5: score += 1
    elif lead["rating"] >= 4.5: score -= 1
    if lead["review_count"] < 20: score += 1
    review_text = " ".join(lead.get("sample_reviews", [])).lower()
    pain_signals = ["wait", "slow", "phone", "hard to reach", "no website", "outdated", "never called back", "rude"]
    for signal in pain_signals:
        if signal in review_text: score += 0.5
    score = max(1, min(10, round(score)))
    approaches = {
        range(8, 11): "Strong need — lead with ROI case study, offer free audit",
        range(6, 8): "Moderate need — highlight specific gaps found in their online presence",
        range(4, 6): "Some need — nurture with educational content first",
        range(1, 4): "Low priority — add to long-term drip campaign",
    }
    approach = "General outreach"
    for r, a in approaches.items():
        if score in r:
            approach = a
            break
    lead["score"] = score
    lead["reasoning"] = f"Heuristic: rating={lead['rating']}, reviews={lead['review_count']}, website={'yes' if lead.get('website') else 'no'}"
    lead["approach"] = approach
    return lead


@app.route("/")
def landing():
    return redirect("/search")


@app.route("/search")
def search_page():
    return render_template("search.html")


@app.route("/results", methods=["POST"])
def results():
    query = request.form.get("query", "").strip()
    count = min(int(request.form.get("count", 15)), 30)
    if not query:
        return render_template("search.html", error="Please enter a search query.")
    if GOOGLE_MAPS_API_KEY:
        leads = fetch_google_leads(query, count)
    else:
        leads = generate_mock_leads(query, count)
    niche = _detect_niche(query)
    scored_leads = score_leads_with_haiku(leads, niche)
    return render_template("results.html", leads=scored_leads, query=query)


@app.route("/export", methods=["POST"])
def export_csv():
    leads_json = request.form.get("leads", "[]")
    leads = json.loads(leads_json)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Score", "Phone", "Email", "Website", "Rating", "Reviews", "Address", "Reasoning", "Approach"])
    for lead in leads:
        writer.writerow([lead.get("name",""), lead.get("score",""), lead.get("phone",""), lead.get("email",""), lead.get("website",""), lead.get("rating",""), lead.get("review_count",""), lead.get("address",""), lead.get("reasoning",""), lead.get("approach","")])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=leadflow_export_{timestamp}.csv"})


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(force=True)
    query = data.get("query", "").strip()
    count = min(data.get("count", 15), 30)
    if not query:
        return jsonify({"error": "query is required"}), 400
    if GOOGLE_MAPS_API_KEY:
        leads = fetch_google_leads(query, count)
    else:
        leads = generate_mock_leads(query, count)
    niche = _detect_niche(query)
    scored_leads = score_leads_with_haiku(leads, niche)
    return jsonify({"query": query, "count": len(scored_leads), "leads": scored_leads})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
