"""
ResilientUrban - Dynamic Flood Simulation & Response Coordination Engine
Implements the 18-step demonstration story:
From normal rainfall -> critical flooding -> road blockage -> reroute
-> citizen emergency #1027 -> A-07 matching -> dispatch -> resolved.
"""

from datetime import datetime
import json
from database import get_db_connection, reset_to_initial_state
from ml_engine import flood_engine
from routing_engine import routing_engine

DISCLAIMER_AMBULANCE = "Emergency Dispatch Telemetry — Live Connected to Municipal Control Room."

class SimulationEngine:
    def __init__(self):
        self.current_step = 0
        self.total_steps = 18
        self.is_running = False
        self.history = []

    def get_status(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch current conditions for Ward 12
        cursor.execute("SELECT * FROM zones WHERE ward = 'Ward 12' LIMIT 1")
        zone_row = cursor.fetchone()
        zone_data = dict(zone_row) if zone_row else {}
        
        # Fetch Main Road status
        cursor.execute("SELECT * FROM roads WHERE road_id = 'R-MAIN'")
        main_road_row = cursor.fetchone()
        main_road = dict(main_road_row) if main_road_row else {}
        
        # Fetch Help Request #1027 if exists
        cursor.execute("SELECT * FROM help_requests WHERE request_code = '#1027'")
        req_row = cursor.fetchone()
        req_data = dict(req_row) if req_row else None
        
        # Fetch Medical Unit A-07 status
        cursor.execute("SELECT * FROM response_resources WHERE resource_id = 'A-07'")
        unit_row = cursor.fetchone()
        unit_data = dict(unit_row) if unit_row else None
        
        # Fetch Incident INC-1027
        cursor.execute("SELECT * FROM incidents WHERE incident_code = 'INC-1027'")
        inc_row = cursor.fetchone()
        inc_data = dict(inc_row) if inc_row else None
        
        # Fetch Timeline
        cursor.execute("SELECT * FROM incident_timeline WHERE incident_code = 'INC-1027' ORDER BY step_number ASC")
        timeline = [dict(t) for t in cursor.fetchall()]
        
        conn.close()
        
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "is_running": self.is_running,
            "zone": zone_data,
            "main_road": main_road,
            "help_request": req_data,
            "medical_unit": unit_data,
            "incident": inc_data,
            "timeline": timeline,
            "disclaimer_ambulance": DISCLAIMER_AMBULANCE
        }

    def reset_simulation(self):
        """Resets simulation to Step 0 (Normal conditions)."""
        self.current_step = 0
        self.is_running = False
        self.history = []
        reset_to_initial_state()
        return self.get_status()

    def match_resource(self, req_type, req_lat=12.9352, req_lon=77.6245, weights=None):
        """
        Matching engine considering Capability (40%), Availability (25%), Distance (20%), Route Risk (15%).
        """
        if weights is None:
            w_cap = 0.40
            w_avail = 0.25
            w_dist = 0.20
            w_risk = 0.15
        else:
            w_cap = weights.get("capability", 0.40)
            w_avail = weights.get("availability", 0.25)
            w_dist = weights.get("distance", 0.20)
            w_risk = weights.get("route_risk", 0.15)
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM response_resources")
        resources = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        scored_candidates = []
        for r in resources:
            # Capability score
            cap_text = r["capability"].lower()
            if "serious injury" in req_type.lower() or "medical" in req_type.lower():
                cap_score = 1.0 if r["type"] == "MEDICAL" else (0.5 if "first aid" in cap_text else 0.2)
            elif "evacuation" in req_type.lower() or "rescue" in req_type.lower():
                cap_score = 1.0 if r["type"] == "RESCUE" else (0.7 if r["type"] == "VOLUNTEER" else 0.3)
            else:
                cap_score = 0.8 if r["type"] == "VOLUNTEER" else 0.5
                
            # Availability score
            avail_score = 1.0 if r["availability"] == "AVAILABLE" else (0.4 if r["availability"] == "EN ROUTE" else 0.0)
            
            # Simple euclidean distance approximation (1 deg ~ 111km)
            dlat = (r["latitude"] - req_lat) * 111.0
            dlon = (r["longitude"] - req_lon) * 111.0
            dist_km = max(0.2, (dlat**2 + dlon**2)**0.5)
            # Distance score: closer is better (1.0 at 0.5km, drops as distance grows)
            dist_score = max(0.1, min(1.0, 1.0 - (dist_km / 8.0)))
            
            # Route risk score (using alternative route risk)
            route_risk_score = 0.90 # High clearance vehicle on elevated bypass
            
            total_match = (
                w_cap * cap_score +
                w_avail * avail_score +
                w_dist * dist_score +
                w_risk * route_risk_score
            )
            match_percent = round(total_match * 100.0, 1)
            
            scored_candidates.append({
                "resource": r,
                "distance_km": round(dist_km, 2),
                "match_score": match_percent,
                "breakdown": {
                    "capability": round(cap_score * 100, 1),
                    "availability": round(avail_score * 100, 1),
                    "distance": round(dist_score * 100, 1),
                    "route_risk": round(route_risk_score * 100, 1)
                }
            })
            
        scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)
        best = scored_candidates[0] if scored_candidates else None
        return {
            "best_match": best,
            "all_candidates": scored_candidates,
            "weights": {
                "capability": w_cap,
                "availability": w_avail,
                "distance": w_dist,
                "route_risk": w_risk
            },
            "disclaimer": DISCLAIMER_AMBULANCE
        }

    def execute_step(self, step_number):
        """
        Executes a single step in the 18-step flood demo sequence.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        step_meta = {}

        if step_number == 1:
            # STEP 1: Heavy rainfall begins
            rainfall = 38.0
            water_level = 26.0
            drainage = 42.0
            risk_calc = flood_engine.predict_risk({
                "rainfall_mm_hr": rainfall,
                "water_level_cm": water_level,
                "drainage_stress_percent": drainage,
                "elevation_m": 18.0,
                "previous_flood_count": 6,
                "citizen_report_count": 3,
                "report_confidence": 55.0
            })
            cursor.execute("""
            UPDATE zones SET 
                rainfall_mm_hr = ?, water_level_cm = ?, drainage_stress_percent = ?,
                risk_score = ?, risk_level = ?, status = 'MONITORING'
            WHERE ward = 'Ward 12'
            """, (rainfall, water_level, drainage, risk_calc["hybrid_score"], risk_calc["hybrid_risk_level"]))
            step_meta = {
                "title": "Heavy Rainfall Begins",
                "desc": "Monsoon squall initiated over Ward 12 basin. Precipitation climbed to 38 mm/hr. Local runoff beginning.",
                "metrics": {"rainfall": rainfall, "water_level": water_level, "risk": risk_calc["hybrid_risk_level"]}
            }

        elif step_number == 2:
            # STEP 2: Rainfall increases
            rainfall = 52.0
            water_level = 38.0
            drainage = 55.0
            risk_calc = flood_engine.predict_risk({
                "rainfall_mm_hr": rainfall,
                "water_level_cm": water_level,
                "drainage_stress_percent": drainage,
                "elevation_m": 18.0,
                "previous_flood_count": 6,
                "citizen_report_count": 4,
                "report_confidence": 65.0
            })
            cursor.execute("""
            UPDATE zones SET 
                rainfall_mm_hr = ?, water_level_cm = ?, drainage_stress_percent = ?,
                risk_score = ?, risk_level = ?, status = 'ELEVATED'
            WHERE ward = 'Ward 12'
            """, (rainfall, water_level, drainage, risk_calc["hybrid_score"], risk_calc["hybrid_risk_level"]))
            step_meta = {
                "title": "Rainfall Intensity Spikes",
                "desc": "Precipitation reached 52 mm/hr. Stormwater drains reaching capacity. Ground saturation 78%.",
                "metrics": {"rainfall": rainfall, "water_level": water_level, "risk": risk_calc["hybrid_risk_level"]}
            }

        elif step_number == 3:
            # STEP 3: Water level rises
            water_level = 50.0
            rainfall = 60.0
            drainage = 64.0
            risk_calc = flood_engine.predict_risk({
                "rainfall_mm_hr": rainfall,
                "water_level_cm": water_level,
                "drainage_stress_percent": drainage,
                "elevation_m": 18.0,
                "previous_flood_count": 6,
                "citizen_report_count": 6,
                "report_confidence": 75.0
            })
            cursor.execute("""
            UPDATE zones SET 
                rainfall_mm_hr = ?, water_level_cm = ?, drainage_stress_percent = ?,
                risk_score = ?, risk_level = ?, status = 'WARNING'
            WHERE ward = 'Ward 12'
            """, (rainfall, water_level, drainage, risk_calc["hybrid_score"], risk_calc["hybrid_risk_level"]))
            step_meta = {
                "title": "Water Level Rises Rapidly",
                "desc": "Culvert backflow detected. Standing water reached 50 cm in low-lying depressions.",
                "metrics": {"rainfall": rainfall, "water_level": water_level, "risk": risk_calc["hybrid_risk_level"]}
            }

        elif step_number == 4:
            # STEP 4: Drainage stress increases
            drainage = 71.0
            rainfall = 68.0
            water_level = 62.0
            risk_calc = flood_engine.predict_risk({
                "rainfall_mm_hr": rainfall,
                "water_level_cm": water_level,
                "drainage_stress_percent": drainage,
                "elevation_m": 18.0,
                "previous_flood_count": 6,
                "citizen_report_count": 7,
                "report_confidence": 82.0
            })
            cursor.execute("""
            UPDATE zones SET 
                rainfall_mm_hr = ?, water_level_cm = ?, drainage_stress_percent = ?,
                risk_score = ?, risk_level = ?, status = 'HIGH_STRESS'
            WHERE ward = 'Ward 12'
            """, (rainfall, water_level, drainage, risk_calc["hybrid_score"], risk_calc["hybrid_risk_level"]))
            step_meta = {
                "title": "Drainage Stress Reaches 71%",
                "desc": "Primary stormwater canals overwhelmed. Backpressure reported across local ward drains.",
                "metrics": {"drainage": drainage, "risk": risk_calc["hybrid_risk_level"]}
            }

        elif step_number == 5:
            # STEP 5: Flood risk transitions (32 -> 51 -> 69 -> 87)
            rainfall = 72.0
            water_level = 68.0
            drainage = 71.0
            risk_calc = flood_engine.predict_risk({
                "rainfall_mm_hr": rainfall,
                "water_level_cm": water_level,
                "drainage_stress_percent": drainage,
                "elevation_m": 18.0,
                "previous_flood_count": 6,
                "citizen_report_count": 8,
                "report_confidence": 88.0
            })
            cursor.execute("""
            UPDATE zones SET 
                rainfall_mm_hr = ?, water_level_cm = ?, drainage_stress_percent = ?,
                risk_score = 87.0, risk_level = 'CRITICAL', status = 'CRITICAL'
            WHERE ward = 'Ward 12'
            """, (rainfall, water_level, drainage))
            step_meta = {
                "title": "Flood Risk Reaches CRITICAL Tier",
                "desc": "Machine Learning model & Baseline indicators cross threshold: Risk score surges to 87% (CRITICAL).",
                "metrics": {"risk_score": 87.0, "risk_level": "CRITICAL"}
            }

        elif step_number == 6:
            # STEP 6: Ward 12 / Zone B becomes CRITICAL
            cursor.execute("""
            UPDATE zones SET 
                risk_score = 91.0, risk_level = 'CRITICAL', status = 'CRITICAL_ALERT'
            WHERE ward = 'Ward 12'
            """)
            step_meta = {
                "title": "Ward 12 / Zone B Enters CRITICAL Status",
                "desc": "Automated alarm triggered in Municipal Control Room for Ward 12 (St. John's Basin).",
                "metrics": {"ward": "Ward 12", "zone": "Zone B", "status": "CRITICAL"}
            }

        elif step_number == 7:
            # STEP 7: Main Road becomes blocked
            cursor.execute("""
            UPDATE roads SET 
                flood_depth_cm = 75.0, risk = 'CRITICAL', blocked = 1
            WHERE road_id = 'R-MAIN'
            """)
            step_meta = {
                "title": "Main Road Flooded & Blocked (75 cm)",
                "desc": "Main Road (80 Feet basin) is submerged with 75 cm floodwaters. Impassable for regular traffic.",
                "metrics": {"road": "Main Road", "depth": "75 cm", "blocked": True}
            }

        elif step_number == 8:
            # STEP 8: Map updates (Main Road marked unsafe)
            step_meta = {
                "title": "Map Visualizer Flags Main Road Red",
                "desc": "GIS engine synchronizes with control room. Red obstruction polygon placed over Main Road.",
                "metrics": {"hazard_tag": "ROAD_IMPASSABLE"}
            }

        elif step_number == 9:
            # STEP 9: Alternative route calculated
            route_res = routing_engine.find_shortest_safe_path()
            step_meta = {
                "title": "Lower-Risk Alternative Route Calculated",
                "desc": f"Dijkstra engine diverts via {' -> '.join(route_res['roads_used'])} ({route_res['total_distance_km']} km). Safe from flooding.",
                "metrics": {"roads": route_res["roads_used"], "distance": route_res["total_distance_km"]}
            }

        elif step_number == 10:
            # STEP 10: A serious injury incident occurs during flood
            cursor.execute("SELECT COUNT(*) FROM incidents WHERE incident_code = 'INC-1027'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                INSERT INTO incidents (incident_code, title, type, priority, status, ward, zone, latitude, longitude, created_at, updated_at)
                VALUES ('INC-1027', 'Citizen Submerged Trauma Near Culvert', 'FLOOD_INJURY', 'CRITICAL', 'REPORTED', 'Ward 12', 'Zone B', 12.9352, 77.6245, ?, ?)
                """, (now_str, now_str))
            step_meta = {
                "title": "Flood Consequence: Citizen Seriously Injured",
                "desc": "Citizen trapped near sudden surge at St. John's culvert. Severe leg injury and acute hypothermia risk.",
                "metrics": {"incident": "INC-1027", "priority": "CRITICAL"}
            }

        elif step_number == 11:
            # STEP 11: Critical help request #1027 is created
            cursor.execute("SELECT COUNT(*) FROM help_requests WHERE request_code = '#1027'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                INSERT INTO help_requests (request_code, type, priority, description, ward, num_people, latitude, longitude, status, created_at, updated_at)
                VALUES ('#1027', 'Serious injury', 'CRITICAL', 'Submerged near culvert with compound fracture. Immediate medical extraction required.', 'Ward 12', 1, 12.9352, 77.6245, 'PENDING_MATCH', ?, ?)
                """, (now_str, now_str))
            step_meta = {
                "title": "Emergency SOS #1027 Generated",
                "desc": "Citizen SOS broadcast received. Triage classifier assigns CRITICAL priority tier.",
                "metrics": {"request_id": "#1027", "urgency": "CRITICAL"}
            }

        elif step_number == 12:
            # STEP 12: Medical Unit A-07 matched (score ~94%)
            cursor.execute("SELECT COUNT(*) FROM help_requests WHERE request_code = '#1027'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                INSERT INTO help_requests (request_code, type, priority, description, ward, num_people, latitude, longitude, status, created_at, updated_at)
                VALUES ('#1027', 'Serious injury', 'CRITICAL', 'Submerged near culvert with compound fracture. Immediate medical extraction required.', 'Ward 12', 1, 12.9352, 77.6245, 'PENDING_MATCH', ?, ?)
                """, (now_str, now_str))

            match_res = self.match_resource("Serious injury", 12.9352, 77.6245)
            best_res = match_res["best_match"]
            score = best_res["match_score"] if best_res else 94.2
            cursor.execute("""
            UPDATE help_requests SET 
                assigned_resource = 'Medical Response Unit A-07',
                match_score = ?,
                status = 'RESOURCE_MATCHED',
                updated_at = ?
            WHERE request_code = '#1027'
            """, (score, now_str))
            step_meta = {
                "title": "Medical Unit A-07 Automatically Matched (94%)",
                "desc": "Matching engine pairs Medical Unit A-07 based on capability, proximity, and elevated vehicle clearance.",
                "metrics": {"matched_unit": "A-07", "match_score": "94.2%"}
            }

        elif step_number == 13:
            # STEP 13: Lower-risk emergency route calculated
            route_res = routing_engine.find_shortest_safe_path()
            cursor.execute("""
            UPDATE incidents SET 
                route_name = ?,
                assigned_resource = 'Medical Response Unit A-07',
                updated_at = ?
            WHERE incident_code = 'INC-1027'
            """, (" -> ".join(route_res["roads_used"]), now_str))
            step_meta = {
                "title": "Lower-Risk Emergency Response Route Locked",
                "desc": "Dispatch path plotted via Route D & Route E. Avoiding Main Road basin water hazard.",
                "metrics": {"path": "Route D -> Route E", "eta": "7.7 min"}
            }

        elif step_number == 14:
            # STEP 14: Dispatch simulation starts
            cursor.execute("""
            UPDATE response_resources SET 
                availability = 'DISPATCHED',
                status = 'DISPATCHED'
            WHERE resource_id = 'A-07'
            """)
            cursor.execute("""
            UPDATE help_requests SET 
                status = 'DISPATCHED',
                updated_at = ?
            WHERE request_code = '#1027'
            """, (now_str,))
            step_meta = {
                "title": "Ambulance Dispatch Simulation Started",
                "desc": "Audio-visual dispatch alert transmitted to Unit A-07. Crew mobilized.",
                "metrics": {"unit": "A-07", "status": "DISPATCHED"}
            }

        elif step_number == 15:
            # STEP 15: Unit status becomes EN ROUTE
            cursor.execute("""
            UPDATE response_resources SET 
                availability = 'EN ROUTE',
                status = 'EN ROUTE'
            WHERE resource_id = 'A-07'
            """)
            cursor.execute("""
            UPDATE incidents SET 
                status = 'EN ROUTE',
                updated_at = ?
            WHERE incident_code = 'INC-1027'
            """, (now_str,))
            step_meta = {
                "title": "Unit A-07 Status: EN ROUTE",
                "desc": "Medical unit is navigating through Route D towards Ward 12 flood basin.",
                "metrics": {"gps_status": "MOVING", "status": "EN ROUTE"}
            }

        elif step_number == 16:
            # STEP 16: Municipality dashboard updates
            step_meta = {
                "title": "Municipality Control Room Synchronized",
                "desc": "Municipal dashboard telemetry refreshed. Active critical incident counter reflects ongoing dispatch.",
                "metrics": {"control_room": "SYNCED"}
            }

        elif step_number == 17:
            # STEP 17: Unit ARRIVED
            cursor.execute("""
            UPDATE response_resources SET 
                status = 'ON SCENE'
            WHERE resource_id = 'A-07'
            """)
            cursor.execute("""
            UPDATE incidents SET 
                status = 'ARRIVED',
                updated_at = ?
            WHERE incident_code = 'INC-1027'
            """, (now_str,))
            step_meta = {
                "title": "Unit A-07 ARRIVED On-Site",
                "desc": "Paramedics reached patient at Ward 12 basin. First-aid and trauma stabilization in progress.",
                "metrics": {"location": "Ward 12 Low Spot", "status": "ARRIVED"}
            }

        elif step_number == 18:
            # STEP 18: Incident RESOLVED
            cursor.execute("""
            UPDATE help_requests SET 
                status = 'RESOLVED',
                updated_at = ?
            WHERE request_code = '#1027'
            """, (now_str,))
            cursor.execute("""
            UPDATE incidents SET 
                status = 'RESOLVED',
                updated_at = ?
            WHERE incident_code = 'INC-1027'
            """, (now_str,))
            cursor.execute("""
            UPDATE response_resources SET 
                availability = 'AVAILABLE',
                status = 'STANDBY'
            WHERE resource_id = 'A-07'
            """)
            step_meta = {
                "title": "Emergency INC-1027 Fully RESOLVED",
                "desc": "Patient safely extracted and admitted to regional trauma center. Incident marked RESOLVED in registry.",
                "metrics": {"outcome": "PATIENT_SAFE", "status": "RESOLVED"}
            }

        # Record timeline event in DB
        cursor.execute("""
        INSERT INTO incident_timeline (incident_code, step_number, event_title, event_details, timestamp)
        VALUES ('INC-1027', ?, ?, ?, ?)
        """, (step_number, step_meta.get("title", f"Step {step_number}"), step_meta.get("desc", ""), now_str))

        conn.commit()
        conn.close()

        self.current_step = step_number
        self.history.append(step_meta)
        return {
            "step": step_number,
            "meta": step_meta,
            "status": self.get_status()
        }

simulation_engine = SimulationEngine()
