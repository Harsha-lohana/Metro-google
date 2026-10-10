"""PS-08 One City, One Journey. Reads data.json only (no external calls).
Local:  pip install flask && python app.py   -> http://127.0.0.1:5000"""
import json, os, re
from flask import Flask, jsonify, render_template, request

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
with open(os.path.join(BASE, "data.json"), encoding="utf-8") as f:
    DB = json.load(f)

OPS = {"Metro": "Gujarat Metro Rail Corp (GMRC)", "BRTS": "Ahmedabad Janmarg Ltd (BRTS)",
       "AMTS": "Ahmedabad Municipal Transport Service (AMTS)"}
TRIPS = {(t["from_stop"], t["to_stop"]): t for t in DB["trip_mappings"]}
num = lambda s: int(re.search(r"\d+", str(s)).group())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stops")
def api_stops():
    stops = {m: [{"id": s, "name": s} for s in v] for m, v in DB["modes_and_stops"].items()}
    trips = [{"from_mode": t["from_mode"], "from_stop": t["from_stop"],
              "to_mode": t["to_mode"], "to_stop": t["to_stop"]} for t in DB["trip_mappings"]]
    return jsonify(stops=stops, trips=trips)


@app.route("/api/plan-trip", methods=["GET", "POST"])
def plan_trip():
    q = request.get_json(silent=True) or request.args
    o, d = q.get("origin"), q.get("destination")
    if o == d:
        return jsonify(error="Origin and destination are the same stop."), 400
    t = TRIPS.get((o, d))
    if not t:
        return jsonify(error="This pair isn't in the demo data. Tap one of the sample trips below."), 404
    legs, ops, total = [], {}, t["total_fare"]
    for l in t["legs"]:
        if l["type"] == "Transfer Walk":
            m = re.search(r"(\d+)\s*m\b", l["details"])
            legs.append({"type": "walk", "details": l["details"], "minutes": num(l["duration"]),
                         "meters": int(m.group(1)) if m else 0})
        else:
            legs.append({"type": "ride", "mode": l["type"], "route": l["type"], "details": l["details"],
                         "operator": OPS[l["type"]], "fare": l["fare"], "ride_min": num(l["duration"])})
            ops[l["type"]] = ops.get(l["type"], 0) + l["fare"]
    operators = [{"mode": m, "operator": OPS[m], "standalone": f, "share_pct": round(f / total * 100, 1),
                  "payout": f} for m, f in ops.items()]
    walks = [l for l in legs if l["type"] == "walk"]
    return jsonify(
        origin=o, destination=d, legs=legs,
        summary={"total_fare": total, "gross_fare": total, "discount": 0, "total_minutes": num(t["total_time"]),
                 "walk_minutes": sum(w["minutes"] for w in walks), "walk_meters": sum(w["meters"] for w in walks),
                 "transfers": len(walks)},
        split={"operators": operators, "discount_pct": 0,
               "formula": "Operator share = operator's leg fare ÷ total journey fare. "
                          "Payout = share × total fare, so each operator receives the fare of its own leg; "
                          "transfer walks cost ₹0."},
        offline=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
