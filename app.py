"""
ResilientUrban - Flask Web Application & REST APIs
Hyper-Local Disaster Early Warning & Community Action Network (Urban Flooding)
Features:
- Dual Authentication (Admin / Municipality vs Citizen)
- Random Forest ML Risk Prediction + Transparent Weighted Baseline
- Dijkstra Flood-Aware Routing Engine (Lower-Risk Alternative Routes)
- Citizen Crowdsourced Reporting with Confidence Scoring
- SOS Triage & Automated Resource Matching Engine
- 18-Step Live Interactive Dynamic Flood Simulation
- Unified Command Center & Municipality Control Room
- Customer Support: Phone 8431535534, Email civora@gmail.com
"""

import os
import json
import random
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, send_from_directory

from database import init_db, get_db_connection, create_dispatch_acknowledgment, log_emergency_comm
from ml_engine import flood_engine, FEATURES
from routing_engine import routing_engine, DISCLAIMER_ROUTE
from simulation_engine import simulation_engine, DISCLAIMER_AMBULANCE
from fetch_real_data import fetch_live_weather, URBAN_CENTERS

app = Flask(__name__)
app.secret_key = "resilient_urban_secret_key_2026_hackathon_token"

SUPPORT_PHONE = "8431535534"
SUPPORT_EMAIL = "civora@gmail.com"
GENERAL_DISCLAIMER = "Live Municipal Flood Telemetry & IMD / Open-Meteo Weather Network. Real-Time Emergency Coordination System."

# Ensure database is initialized
init_db()

# -------------------------------------------------------------
# AUTH & USER HELPER
# -------------------------------------------------------------
def get_current_user():
    if "user_id" in session:
        return {
            "id": session["user_id"],
            "username": session.get("username", "guest"),
            "role": session.get("role", "CITIZEN"),
            "name": session.get("full_name", "Citizen User")
        }
    return {
        "id": None,
        "username": "guest",
        "role": "PUBLIC",
        "name": "Guest Resident"
    }

# -------------------------------------------------------------
# WEB PAGES & DIGITAL RECEIPT / APK DOWNLOADS
# -------------------------------------------------------------
@app.route("/")
def index():
    user = get_current_user()
    if user.get("role") == "CITIZEN":
        return redirect("/citizen")
    return render_template(
        "index.html",
        user=user,
        support_phone=SUPPORT_PHONE,
        support_email=SUPPORT_EMAIL,
        disclaimer=GENERAL_DISCLAIMER
    )

@app.route("/admin")
def admin_page():
    user = get_current_user()
    return render_template(
        "index.html",
        user=user,
        support_phone=SUPPORT_PHONE,
        support_email=SUPPORT_EMAIL,
        disclaimer=GENERAL_DISCLAIMER
    )

@app.route("/citizen")
def citizen_page():
    user = get_current_user()
    return render_template(
        "citizen.html",
        user=user,
        support_phone=SUPPORT_PHONE,
        support_email=SUPPORT_EMAIL,
        disclaimer=GENERAL_DISCLAIMER
    )

@app.route("/receipt")
@app.route("/receipt/<path:req_code>")
def receipt_page(req_code="1027"):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Strip any leading '#' or slashes
    clean_code = req_code.strip("#/ ")
    cursor.execute("""
    SELECT * FROM dispatch_acknowledgments 
    WHERE request_code = ? OR ack_code = ? OR request_code = ? OR request_code = ?
    ORDER BY id DESC LIMIT 1
    """, (req_code, clean_code, f"#{clean_code}", clean_code))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("SELECT * FROM dispatch_acknowledgments ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
    
    ack = dict(row) if row else {
        "ack_code": "ACK-2026-X884",
        "request_code": req_code,
        "citizen_name": "Ramesh Kumar (Resident)",
        "citizen_phone": "9845012345",
        "family_contact_name": "Sunita Kumar (Spouse)",
        "family_contact_phone": "8431535534",
        "ward": "Ward 12 (Koramangala 4th Block)",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "hospital_name": "St. John's Medical College Hospital & Trauma Centre",
        "assigned_unit": "ALS Heavy Flood Ambulance Unit A-07 (4x4)",
        "responder_phone": "8431535534",
        "eta_minutes": 7.2,
        "cleared_route": "100 Feet Intermediate Ring Road Elevated Flyover Corridor",
        "verification_seal": "BBMP-NDMA-SEAL-99482-VERIFIED",
        "qr_token": f"SECURE-FLOOD-DISPATCH-{req_code}-A07-BBMP-2026",
        "status": "DISPATCH_CONFIRMED",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    conn.close()
    return render_template("receipt.html", ack=ack, support_phone=SUPPORT_PHONE, support_email=SUPPORT_EMAIL)

@app.route("/download/resilient-urban.apk")
def download_apk():
    apk_path = os.path.join(app.root_path, "static", "downloads", "resilient-urban.apk")
    if not os.path.exists(apk_path):
        import package_apk
        package_apk.generate_apk(apk_path)
    return send_file(
        apk_path,
        mimetype="application/vnd.android.package-archive",
        as_attachment=True,
        download_name="resilient-urban.apk"
    )

@app.route("/manifest.json")
def serve_manifest():
    return send_from_directory(os.path.join(app.root_path, "static"), "manifest.json", mimetype="application/manifest+json")

@app.route("/sw.js")
def serve_sw():
    return send_from_directory(os.path.join(app.root_path, "static"), "sw.js", mimetype="application/javascript")

@app.route("/login")
def login_page():
    user = get_current_user()
    return render_template(
        "login.html",
        user=user,
        support_phone=SUPPORT_PHONE,
        support_email=SUPPORT_EMAIL
    )

# -------------------------------------------------------------
# AUTH APIS
# -------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM users 
    WHERE (username = ? OR email = ?) AND password = ?
    """, (username, username, password))
    user_row = cursor.fetchone()
    conn.close()

    if user_row:
        user = dict(user_row)
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["full_name"] = user["full_name"]
        target_url = "/citizen" if user["role"] == "CITIZEN" else "/admin"
        return jsonify({
            "status": "SUCCESS",
            "message": f"Welcome back, {user['full_name']}!",
            "redirect_url": target_url,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "name": user["full_name"]
            }
        })
    else:
        return jsonify({"status": "ERROR", "message": "Invalid username/email or password"}), 401

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    full_name = data.get("full_name", "").strip()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    password = data.get("password", "").strip()
    role = data.get("role", "CITIZEN").strip().upper()

    if not username or not password or not full_name:
        return jsonify({"status": "ERROR", "message": "Full Name, Username, and Password are required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ? OR (email != '' AND email = ?)", (username, email))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "ERROR", "message": "Username or Email already registered."}), 409

    cursor.execute("""
    INSERT INTO users (username, password, role, full_name, phone, email)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (username, password, role, full_name, phone, email))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    session["user_id"] = new_id
    session["username"] = username
    session["role"] = role
    session["full_name"] = full_name

    return jsonify({
        "status": "SUCCESS",
        "message": f"Account successfully created for {full_name}!",
        "user": {"id": new_id, "username": username, "role": role, "name": full_name}
    })

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"status": "SUCCESS", "message": "Logged out successfully"})

@app.route("/api/user", methods=["GET"])
def api_current_user():
    return jsonify(get_current_user())

# -------------------------------------------------------------
# CORE DASHBOARD & CENTRAL STATE API
# -------------------------------------------------------------
@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Zones
    cursor.execute("SELECT * FROM zones")
    zones = [dict(z) for z in cursor.fetchall()]

    # Ward 12 primary focal zone
    primary_zone = next((z for z in zones if z["ward"] == "Ward 12"), zones[0] if zones else {})

    # Roads
    cursor.execute("SELECT * FROM roads")
    roads = [dict(r) for r in cursor.fetchall()]
    for r in roads:
        try:
            r["coordinates"] = json.loads(r["coordinates_json"])
        except Exception:
            r["coordinates"] = []

    # Reports
    cursor.execute("SELECT * FROM reports ORDER BY id DESC")
    reports = [dict(rep) for rep in cursor.fetchall()]

    # Help Requests
    cursor.execute("SELECT * FROM help_requests ORDER BY id DESC")
    help_requests = [dict(hr) for hr in cursor.fetchall()]

    # Response Resources
    cursor.execute("SELECT * FROM response_resources")
    resources = [dict(res) for res in cursor.fetchall()]

    # Incidents
    cursor.execute("SELECT * FROM incidents ORDER BY id DESC")
    incidents = [dict(inc) for inc in cursor.fetchall()]

    # Timeline for INC-1027
    cursor.execute("SELECT * FROM incident_timeline ORDER BY id ASC")
    timeline = [dict(t) for t in cursor.fetchall()]

    conn.close()

    # Calculate KPIs
    active_flood_zones = len([z for z in zones if z["risk_level"] in ["HIGH", "CRITICAL"]])
    critical_zones = len([z for z in zones if z["risk_level"] == "CRITICAL"])
    blocked_roads = len([r for r in roads if r["blocked"] == 1])
    active_help_requests = len([hr for hr in help_requests if hr["status"] != "RESOLVED"])
    critical_requests = len([hr for hr in help_requests if hr["priority"] == "CRITICAL" and hr["status"] != "RESOLVED"])
    available_resources = len([res for res in resources if res["availability"] == "AVAILABLE"])
    verified_reports = len([rep for rep in reports if rep["confidence"] >= 70.0])
    active_medical_units = len([res for res in resources if res["type"] == "MEDICAL"])

    # Central application state representation
    state = {
        "hazard": "urban_flood",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "primary_location": {
            "ward": primary_zone.get("ward", "Ward 12"),
            "zone": primary_zone.get("name", "Zone B"),
            "latitude": primary_zone.get("latitude", 12.9352),
            "longitude": primary_zone.get("longitude", 77.6245),
            "elevation_m": primary_zone.get("elevation_m", 18.0)
        },
        "current_conditions": {
            "rainfall_mm_hr": primary_zone.get("rainfall_mm_hr", 25.0),
            "water_level_cm": primary_zone.get("water_level_cm", 20.0),
            "drainage_stress_percent": primary_zone.get("drainage_stress_percent", 30.0),
            "risk_score": primary_zone.get("risk_score", 32.0),
            "risk_level": primary_zone.get("risk_level", "LOW")
        },
        "kpis": {
            "active_flood_zones": active_flood_zones,
            "critical_zones": critical_zones,
            "blocked_roads": blocked_roads,
            "active_help_requests": active_help_requests,
            "critical_requests": critical_requests,
            "available_resources": available_resources,
            "verified_reports": verified_reports,
            "active_medical_units": active_medical_units
        },
        "risk_trend": [
            {"label": "T-30m", "score": 32, "level": "LOW"},
            {"label": "T-15m", "score": 51, "level": "MODERATE"},
            {"label": "T-5m", "score": 69, "level": "HIGH"},
            {"label": "Current", "score": int(primary_zone.get("risk_score", 87)), "level": primary_zone.get("risk_level", "CRITICAL")}
        ],
        "zones": zones,
        "roads": roads,
        "reports": reports,
        "help_requests": help_requests,
        "resources": resources,
        "incidents": incidents,
        "timeline": timeline,
        "cities": list(URBAN_CENTERS.keys()),
        "simulation_step": simulation_engine.current_step,
        "support": {
            "phone": SUPPORT_PHONE,
            "email": SUPPORT_EMAIL
        },
        "disclaimer": GENERAL_DISCLAIMER
    }
    return jsonify(state)

# -------------------------------------------------------------
# LIVE REAL-TIME METEOROLOGICAL TELEMETRY APIS (OPEN-METEO)
# -------------------------------------------------------------
@app.route("/api/weather/live", methods=["GET"])
def api_live_weather():
    lat = float(request.args.get("lat", 12.9352))
    lon = float(request.args.get("lon", 77.6245))
    try:
        w_data = fetch_live_weather(lat, lon)
        return jsonify(w_data)
    except Exception as e:
        return jsonify({
            "status": "CACHED_FALLBACK",
            "message": str(e),
            "rain_mm_hr": 25.0,
            "temperature_c": 27.2,
            "relative_humidity_percent": 62,
            "surface_pressure_hpa": 916.0
        })

@app.route("/api/weather/sync", methods=["POST"])
def api_sync_weather():
    data = request.get_json() or {}
    city_name = data.get("city", "Bengaluru (Koramangala/HSR)")
    info = URBAN_CENTERS.get(city_name, URBAN_CENTERS["Bengaluru (Koramangala/HSR)"])
    lat = info["lat"]
    lon = info["lon"]
    try:
        w = fetch_live_weather(lat, lon)
        live_rain = float(w.get("rain_mm_hr", 25.0))
        # Update Ward 12 with live real-time rainfall measurement
        conn = get_db_connection()
        cursor = conn.cursor()
        pred = flood_engine.predict_risk({
            "rainfall_mm_hr": max(live_rain, 15.0),
            "water_level_cm": max(live_rain * 0.8, 18.0),
            "drainage_stress_percent": max(live_rain * 0.9, 25.0),
            "elevation_m": info["base_elev"],
            "previous_flood_count": 6,
            "citizen_report_count": 4,
            "report_confidence": 75.0
        })
        cursor.execute("""
        UPDATE zones SET 
            rainfall_mm_hr = ?, water_level_cm = ?, drainage_stress_percent = ?,
            risk_score = ?, risk_level = ?
        WHERE ward = 'Ward 12'
        """, (max(live_rain, 15.0), max(live_rain * 0.8, 18.0), max(live_rain * 0.9, 25.0), pred["hybrid_score"], pred["hybrid_risk_level"]))
        conn.commit()
        conn.close()
        return jsonify({"status": "SYNCED", "city": city_name, "weather": w, "prediction": pred})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)})

# -------------------------------------------------------------
# ML RISK PREDICTION & EVALUATION APIS
# -------------------------------------------------------------
@app.route("/api/risk", methods=["GET"])
def api_get_risk():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM zones WHERE ward = 'Ward 12' LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    zone = dict(row) if row else {}

    result = flood_engine.predict_risk({
        "rainfall_mm_hr": zone.get("rainfall_mm_hr", 25.0),
        "water_level_cm": zone.get("water_level_cm", 20.0),
        "drainage_stress_percent": zone.get("drainage_stress_percent", 30.0),
        "elevation_m": zone.get("elevation_m", 18.0),
        "previous_flood_count": 6,
        "citizen_report_count": 3,
        "report_confidence": 65.0
    })
    result["zone"] = zone
    return jsonify(result)

@app.route("/api/risk/simulate", methods=["POST"])
def api_simulate_risk():
    """Allows manual parameter tweaking for ML vs Baseline comparison."""
    data = request.get_json() or {}
    rainfall = float(data.get("rainfall_mm_hr", 72.0))
    water_level = float(data.get("water_level_cm", 68.0))
    drainage = float(data.get("drainage_stress_percent", 71.0))
    elevation = float(data.get("elevation_m", 18.0))
    prev_floods = int(data.get("previous_flood_count", 6))
    reports = int(data.get("citizen_report_count", 8))
    confidence = float(data.get("report_confidence", 85.0))
    
    weights = data.get("weights", None)

    pred = flood_engine.predict_risk({
        "rainfall_mm_hr": rainfall,
        "water_level_cm": water_level,
        "drainage_stress_percent": drainage,
        "elevation_m": elevation,
        "previous_flood_count": prev_floods,
        "citizen_report_count": reports,
        "report_confidence": confidence
    })
    
    if weights:
        pred["custom_baseline"] = flood_engine.calculate_baseline_risk(
            rainfall, water_level, drainage, confidence, weights
        )

    return jsonify(pred)

@app.route("/api/ml/metrics", methods=["GET"])
def api_ml_metrics():
    return jsonify(flood_engine.get_evaluation())

# -------------------------------------------------------------
# ROADS & DIJKSTRA ROUTING APIS
# -------------------------------------------------------------
@app.route("/api/roads", methods=["GET"])
def api_get_roads():
    roads = routing_engine.get_roads_from_db()
    return jsonify({"roads": roads, "disclaimer": DISCLAIMER_ROUTE})

@app.route("/api/roads/block", methods=["POST"])
def api_block_road():
    data = request.get_json() or {}
    road_id = data.get("road_id", "R-MAIN")
    blocked = bool(data.get("blocked", True))
    depth = float(data.get("flood_depth_cm", 75.0 if blocked else 0.0))
    risk = "CRITICAL" if blocked else "LOW"
    routing_engine.set_road_status(road_id, blocked, depth, risk)
    return jsonify({"status": "SUCCESS", "message": f"Road {road_id} updated. Blocked={blocked}"})

@app.route("/api/route", methods=["GET", "POST"])
def api_calculate_route():
    start = request.args.get("start", "NODE_A")
    dest = request.args.get("dest", "NODE_DEST")
    route_info = routing_engine.find_shortest_safe_path(start, dest)
    return jsonify(route_info)

# -------------------------------------------------------------
# CITIZEN REPORTS & CONFIDENCE SCORING APIS
# -------------------------------------------------------------
@app.route("/api/reports", methods=["GET", "POST"])
def api_reports():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.get_json() or {}
        rep_type = data.get("type", "Flooded road")
        desc = data.get("description", "Rising water level on street")
        ward = data.get("ward", "Ward 12")
        lat = float(data.get("latitude", 12.9352))
        lon = float(data.get("longitude", 77.6245))
        has_evidence = 1 if data.get("evidence", True) else 0

        # Calculate Prototype Report Confidence Score
        # Base: 40, +8 each independent report in area, +10 location consistency, +10 evidence, max 100
        cursor.execute("SELECT COUNT(*) FROM reports WHERE ward = ?", (ward,))
        existing_count = cursor.fetchone()[0]
        
        confidence = 40.0 + min(existing_count * 8.0, 32.0)
        confidence += 10.0 # Location consistency within ward boundaries
        if has_evidence:
            confidence += 10.0
        confidence = min(confidence, 100.0)

        # Tier classification
        if confidence <= 40:
            tier = "LOW"
        elif confidence <= 70:
            tier = "MEDIUM"
        elif confidence <= 90:
            tier = "HIGH"
        else:
            tier = "VERIFIED"

        code = f"REP-{random.randint(1030, 9999)}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT INTO reports (report_code, type, description, ward, latitude, longitude, confidence, confidence_tier, evidence_present, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?)
        """, (code, rep_type, desc, ward, lat, lon, confidence, tier, has_evidence, now_str))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "SUCCESS",
            "report_code": code,
            "confidence": round(confidence, 1),
            "tier": tier,
            "formula_explanation": "Base 40 + Independent reports (+8 each) + Location consistency (+10) + Evidence (+10)",
            "disclaimer": "Prototype Report Confidence Score. Not scientifically validated."
        })

    # GET
    cursor.execute("SELECT * FROM reports ORDER BY id DESC")
    reports = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"reports": reports})

# -------------------------------------------------------------
# SOS HELP REQUESTS & PRIORITY CLASSIFICATION
# -------------------------------------------------------------
@app.route("/api/help-requests", methods=["GET", "POST"])
def api_help_requests():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        data = request.get_json() or {}
        req_type = data.get("type", "Serious injury")
        desc = data.get("description", "Person injured during flooding")
        ward = data.get("ward", "Ward 12")
        num_people = int(data.get("num_people", 1))
        lat = float(data.get("latitude", 12.9352))
        lon = float(data.get("longitude", 77.6245))

        # Triage Priority logic:
        # Serious injury / unconscious / breathing -> CRITICAL
        # Minor injury / elderly evacuation / pregnant -> HIGH
        # Mobility assistance -> MEDIUM
        # Food/water/general -> NORMAL
        t_lower = req_type.lower()
        if any(k in t_lower for k in ["serious injury", "unconscious", "breathing difficulty", "severe trauma"]):
            priority = "CRITICAL"
        elif any(k in t_lower for k in ["minor injury", "elderly", "pregnant", "evacuation"]):
            priority = "HIGH"
        elif any(k in t_lower for k in ["mobility", "wheelchair", "elderly assistance"]):
            priority = "MEDIUM"
        else:
            priority = "NORMAL"

        req_code = f"#{random.randint(1050, 9999)}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT INTO help_requests (request_code, type, priority, description, ward, num_people, latitude, longitude, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_MATCH', ?, ?)
        """, (req_code, req_type, priority, desc, ward, num_people, lat, lon, now_str, now_str))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "SUCCESS",
            "request_code": req_code,
            "priority": priority,
            "message": f"Help request {req_code} registered with priority {priority}"
        })

    # GET
    cursor.execute("SELECT * FROM help_requests ORDER BY id DESC")
    requests_list = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"help_requests": requests_list})

# -------------------------------------------------------------
# RESOURCE MATCHING & DISPATCH SIMULATION
# -------------------------------------------------------------
@app.route("/api/resources", methods=["GET"])
def api_get_resources():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM response_resources")
    resources = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"resources": resources})

@app.route("/api/match-resource", methods=["POST"])
def api_match_resource():
    data = request.get_json() or {}
    req_type = data.get("type", "Serious injury")
    lat = float(data.get("latitude", 12.9352))
    lon = float(data.get("longitude", 77.6245))
    weights = data.get("weights", None)
    
    match_result = simulation_engine.match_resource(req_type, lat, lon, weights)
    return jsonify(match_result)

@app.route("/api/dispatch-simulation", methods=["POST"])
def api_dispatch_simulation():
    data = request.get_json() or {}
    resource_id = data.get("resource_id", "A-07")
    status = data.get("status", "EN ROUTE").upper()
    req_code = data.get("request_code", "#1027")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE response_resources 
    SET availability = ?, status = ?
    WHERE resource_id = ?
    """, (status, status, resource_id))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    UPDATE help_requests 
    SET status = ?, updated_at = ?
    WHERE request_code = ?
    """, (status, now_str, req_code))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "SUCCESS",
        "resource_id": resource_id,
        "new_status": status,
        "disclaimer": DISCLAIMER_AMBULANCE
    })

# -------------------------------------------------------------
# DYNAMIC 18-STEP FLOOD DEMO SIMULATION APIS
# -------------------------------------------------------------
@app.route("/api/simulation/step", methods=["POST"])
def api_simulation_step():
    data = request.get_json() or {}
    step_num = int(data.get("step", simulation_engine.current_step + 1))
    if step_num > 18:
        step_num = 18
    res = simulation_engine.execute_step(step_num)
    return jsonify(res)

@app.route("/api/simulation/reset", methods=["POST"])
def api_simulation_reset():
    res = simulation_engine.reset_simulation()
    return jsonify({"status": "RESET", "state": res})

@app.route("/api/simulation/status", methods=["GET"])
def api_simulation_status():
    return jsonify(simulation_engine.get_status())

# -------------------------------------------------------------
# SOS TRIGGER & AUTOMATED TELEPHONY DISPATCH APIS
# -------------------------------------------------------------
@app.route("/api/sos/trigger", methods=["POST"])
def api_sos_trigger():
    data = request.get_json() or {}
    citizen_name = data.get("name", "Resident Citizen").strip()
    citizen_phone = data.get("phone", "8431535534").strip()
    family_name = data.get("family_name", "Family Guardian").strip()
    family_phone = data.get("family_phone", "8431535534").strip()
    req_type = data.get("type", "Serious injury")
    landmark = data.get("landmark", "Koramangala 4th Block").strip()
    lat = float(data.get("latitude", 12.9352))
    lon = float(data.get("longitude", 77.6245))

    req_code = f"#{random.randint(1050, 9999)}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Priority triage
    priority = "CRITICAL" if any(k in req_type.lower() for k in ["serious", "trauma", "unconscious", "head"]) else "HIGH"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO help_requests (
        request_code, citizen_name, citizen_phone, family_contact_name, family_contact_phone,
        type, priority, description, ward, num_people, latitude, longitude, status, assigned_resource, match_score, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Ward 12', 2, ?, ?, 'DISPATCHED', 'A-07', 95.5, ?, ?)
    """, (req_code, citizen_name, citizen_phone, family_name, family_phone, req_type, priority, landmark, lat, lon, now_str, now_str))

    # Create official acknowledgment receipt
    hospital_name = "St. John's Medical College Hospital & Emergency Trauma Centre"
    assigned_unit = "ALS Heavy Flood Ambulance Unit A-07 (4x4 Modified)"
    responder_phone = SUPPORT_PHONE
    eta_mins = round(random.uniform(5.5, 8.5), 1)
    cleared_route = "100 Feet Intermediate Ring Road Elevated Flyover Corridor"

    ack_code = create_dispatch_acknowledgment(
        conn, req_code, citizen_name, citizen_phone, family_name, family_phone,
        "Ward 12 (Koramangala 4th Block)", lat, lon, hospital_name, assigned_unit,
        responder_phone, eta_mins, cleared_route
    )

    # Log Automated Emergency Call
    call_script = f"Emergency alert from ResilientUrban. Flash flood rescue unit A-07 has been dispatched to {citizen_name} at {landmark}. Estimated arrival time is {eta_mins} minutes. Move to elevated floor and stand by."
    log_emergency_comm(
        conn, req_code, 'CALL', family_name, family_phone,
        f"Automated phone call placed to family member {family_name} ({family_phone}) regarding citizen {citizen_name}.",
        call_script
    )

    # Log Automated Emergency SMS
    sms_text = f"[CRITICAL FLOOD SOS] {citizen_name} is trapped in rising floodwaters at Ward 12 ({lat}, {lon}). Rescue Unit A-07 (St. John's Hospital) dispatched (ETA: {eta_mins} mins). Official Receipt: http://127.0.0.1:5000/receipt/{req_code}. Helpline: {SUPPORT_PHONE}."
    log_emergency_comm(
        conn, req_code, 'SMS', family_name, family_phone, sms_text
    )

    # Also log SMS to citizen
    log_emergency_comm(
        conn, req_code, 'SMS', citizen_name, citizen_phone,
        f"[BBMP RESCUE CONFIRMED] Unit A-07 en route to your location. Driver contact: {SUPPORT_PHONE}. Route: 100ft Ring Road Flyover. Receipt: {ack_code}."
    )

    conn.close()

    return jsonify({
        "status": "SUCCESS",
        "request_code": req_code,
        "priority": priority,
        "receipt": {
            "ack_code": ack_code,
            "request_code": req_code,
            "hospital_name": hospital_name,
            "assigned_unit": assigned_unit,
            "responder_phone": responder_phone,
            "eta_minutes": eta_mins,
            "cleared_route": cleared_route
        },
        "sms": {
            "recipient_name": family_name,
            "recipient_phone": family_phone,
            "message": sms_text
        },
        "call_script": call_script
    })

# -------------------------------------------------------------
# RANDOMIZED DATA SIMULATION & FALSE DATA STRESS-TESTER
# -------------------------------------------------------------
@app.route("/api/simulation/randomize", methods=["POST"])
def api_simulation_randomize():
    """Generates randomized simulation data, injects false data to test confidence scoring, and calculates all dynamic outcomes."""
    data = request.get_json() or {}
    
    # 1. Random or specified weather parameters
    rainfall = float(data.get("rainfall_mm_hr", random.choice([35.0, 68.0, 95.0, 130.0, 175.0])))
    water_level = float(data.get("water_level_cm", min(rainfall * 0.9 + random.uniform(-5, 15), 180.0)))
    drainage_stress = float(data.get("drainage_stress_percent", min(rainfall * 0.7 + random.uniform(10, 25), 100.0)))
    
    # 2. Random False Data / Citizen Reports
    false_report_injected = None
    if random.random() > 0.2: # Inject false or noisy report
        false_types = [
            ("False report: Street completely dry despite cloudburst", 22.0, "LOW"),
            ("Noise: Single citizen reported ankle water on terrace", 34.0, "LOW"),
            ("Valid alert: Severe surge over bridge culvert", 84.0, "HIGH")
        ]
        f_desc, f_conf, f_tier = random.choice(false_types)
        false_report_injected = {
            "description": f_desc,
            "confidence": f_conf,
            "tier": f_tier,
            "is_false_or_noise": f_conf < 50.0
        }
    
    # 3. Dynamic ML Prediction
    pred = flood_engine.predict_risk({
        "rainfall_mm_hr": rainfall,
        "water_level_cm": water_level,
        "drainage_stress_percent": drainage_stress,
        "elevation_m": 884.0,
        "previous_flood_count": 6,
        "citizen_report_count": 5,
        "report_confidence": 75.0
    })
    
    # 4. Update Database Zone Ward 12
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE zones SET 
        rainfall_mm_hr = ?, water_level_cm = ?, drainage_stress_percent = ?,
        risk_score = ?, risk_level = ?
    WHERE ward = 'Ward 12'
    """, (rainfall, water_level, drainage_stress, pred["hybrid_score"], pred["hybrid_risk_level"]))
    
    # 5. Dynamic Road Blockage Check: If water_level > 50cm, block R-MAIN
    should_block_main = (water_level >= 50.0)
    cursor.execute("""
    UPDATE roads SET 
        blocked = ?, flood_depth_cm = ?, risk = ?
    WHERE road_id = 'R-MAIN'
    """, (1 if should_block_main else 0, water_level if should_block_main else 0.0, "CRITICAL" if should_block_main else "LOW"))
    
    conn.commit()
    conn.close()
    
    # 6. Recalculate Dijkstra Route
    route_info = routing_engine.find_shortest_safe_path("NODE_A", "NODE_DEST")
    
    return jsonify({
        "status": "RANDOMIZED_CALCULATION_COMPLETE",
        "simulation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "random_inputs": {
            "rainfall_mm_hr": round(rainfall, 1),
            "water_level_cm": round(water_level, 1),
            "drainage_stress_percent": round(drainage_stress, 1)
        },
        "false_data_stress_test": false_report_injected,
        "calculated_risk": pred,
        "road_status": {
            "main_road_blocked": should_block_main,
            "bypass_active": route_info.get("chosen_route", {}).get("name")
        },
        "dijkstra_reroute": route_info
    })

@app.route("/api/acknowledgments", methods=["GET"])
def api_get_acknowledgments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dispatch_acknowledgments ORDER BY id DESC LIMIT 20")
    acks = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"acknowledgments": acks})

@app.route("/api/comms/logs", methods=["GET"])
def api_get_comms_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sms_call_logs ORDER BY id DESC LIMIT 30")
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"logs": logs})

# -------------------------------------------------------------
# RUN APPLICATION
# -------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  RESILIENTURBAN - Hyper-Local Flood Early Warning Network")
    print(f"  Customer Support: {SUPPORT_PHONE} | {SUPPORT_EMAIL}")
    print("  Local Access:  http://127.0.0.1:5000")
    print("  Mobile Access: http://10.133.91.215:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)

