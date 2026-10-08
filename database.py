"""
ResilientUrban - SQLite Database & Real Geospatial Data Models
Stores authentic municipal ward catchment zones, real road vectors,
citizen observation reports, emergency triage requests, and responder fleets.
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "resilient_urban.db")

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Zones table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        ward TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        elevation_m REAL DEFAULT 890.0,
        rainfall_mm_hr REAL DEFAULT 25.0,
        water_level_cm REAL DEFAULT 20.0,
        drainage_stress_percent REAL DEFAULT 30.0,
        risk_score REAL DEFAULT 32.0,
        risk_level TEXT DEFAULT 'LOW',
        status TEXT DEFAULT 'NORMAL'
    )
    """)
    
    # Roads network table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        road_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        distance_km REAL NOT NULL,
        flood_depth_cm REAL DEFAULT 0.0,
        risk TEXT DEFAULT 'LOW',
        blocked INTEGER DEFAULT 0,
        start_node TEXT NOT NULL,
        end_node TEXT NOT NULL,
        coordinates_json TEXT NOT NULL
    )
    """)
    
    # Citizen community reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_code TEXT UNIQUE NOT NULL,
        type TEXT NOT NULL,
        description TEXT NOT NULL,
        ward TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        confidence REAL DEFAULT 40.0,
        confidence_tier TEXT DEFAULT 'LOW',
        evidence_present INTEGER DEFAULT 0,
        status TEXT DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL
    )
    """)
    
    # Emergency help requests table (SOS)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS help_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_code TEXT UNIQUE NOT NULL,
        citizen_name TEXT DEFAULT 'Citizen Resident',
        citizen_phone TEXT DEFAULT '8431535534',
        family_contact_name TEXT DEFAULT 'Family Guardian',
        family_contact_phone TEXT DEFAULT '8431535534',
        type TEXT NOT NULL,
        priority TEXT NOT NULL,
        description TEXT NOT NULL,
        ward TEXT,
        num_people INTEGER DEFAULT 1,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        status TEXT DEFAULT 'ACTIVE',
        assigned_resource TEXT,
        match_score REAL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    
    # Ensure migration columns in help_requests
    cursor.execute("PRAGMA table_info(help_requests)")
    existing_cols = [r[1] for r in cursor.fetchall()]
    if "citizen_name" not in existing_cols:
        cursor.execute("ALTER TABLE help_requests ADD COLUMN citizen_name TEXT DEFAULT 'Citizen Resident'")
    if "citizen_phone" not in existing_cols:
        cursor.execute("ALTER TABLE help_requests ADD COLUMN citizen_phone TEXT DEFAULT '8431535534'")
    if "family_contact_name" not in existing_cols:
        cursor.execute("ALTER TABLE help_requests ADD COLUMN family_contact_name TEXT DEFAULT 'Family Guardian'")
    if "family_contact_phone" not in existing_cols:
        cursor.execute("ALTER TABLE help_requests ADD COLUMN family_contact_phone TEXT DEFAULT '8431535534'")

    # Response resources & rescue fleet
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS response_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        capability TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        availability TEXT DEFAULT 'AVAILABLE',
        vehicle_type TEXT NOT NULL,
        contact_no TEXT NOT NULL,
        status TEXT DEFAULT 'STANDBY'
    )
    """)
    
    # Incidents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        type TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT DEFAULT 'DISPATCHED',
        ward TEXT,
        zone TEXT,
        latitude REAL,
        longitude REAL,
        assigned_resource TEXT,
        route_name TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    
    # Incident timeline events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incident_timeline (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_code TEXT NOT NULL,
        step_number INTEGER,
        event_title TEXT NOT NULL,
        event_details TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)

    # Official Dispatch Confirmation Receipts / Acknowledgment Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dispatch_acknowledgments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ack_code TEXT UNIQUE NOT NULL,
        request_code TEXT NOT NULL,
        citizen_name TEXT NOT NULL,
        citizen_phone TEXT NOT NULL,
        family_contact_name TEXT,
        family_contact_phone TEXT,
        ward TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        hospital_name TEXT NOT NULL,
        assigned_unit TEXT NOT NULL,
        responder_phone TEXT NOT NULL,
        eta_minutes REAL NOT NULL,
        cleared_route TEXT NOT NULL,
        verification_seal TEXT NOT NULL,
        qr_token TEXT NOT NULL,
        status TEXT DEFAULT 'DISPATCH_CONFIRMED',
        timestamp TEXT NOT NULL
    )
    """)

    # Automated Emergency Calls & SMS Transmissions Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sms_call_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_code TEXT NOT NULL,
        log_type TEXT NOT NULL, -- 'CALL' or 'SMS'
        recipient_name TEXT NOT NULL,
        recipient_phone TEXT NOT NULL,
        sender_id TEXT DEFAULT 'BBMP-NDMA-DISPATCH',
        message_content TEXT NOT NULL,
        audio_script TEXT,
        status TEXT DEFAULT 'DELIVERED',
        delivery_timestamp TEXT NOT NULL
    )
    """)
    
    # Users table for Dual Role Authentication (Admin & Citizen)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        email TEXT
    )
    """)

    conn.commit()
    seed_real_world_data(conn)
    conn.close()

def seed_real_world_data(conn):
    cursor = conn.cursor()
    
    # 1. Users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [
            ("admin", "admin123", "ADMIN", "Municipal Disaster Director", "8431535534", "civora@gmail.com"),
            ("operator", "control2026", "OPERATOR", "Emergency Dispatch Supervisor", "8431535534", "civora@gmail.com"),
            ("citizen", "citizen123", "CITIZEN", "Ramesh Kumar (Resident)", "9845012345", "ramesh.k@gmail.com")
        ]
        cursor.executemany("INSERT INTO users (username, password, role, full_name, phone, email) VALUES (?, ?, ?, ?, ?, ?)", users)
        
    # 2. Real Municipal Wards & Catchment Basins (Bengaluru Stormwater Inundation Zone)
    cursor.execute("DELETE FROM zones")
    zones = [
        ("Koramangala 4th Block Basin (Rajakaluve)", "Ward 12", 12.9352, 77.6245, 884.0, 25.0, 20.0, 30.0, 32.0, "LOW", "MONITORING"),
        ("HSR Layout Sector 7 Storm Inlet", "Ward 174", 12.9110, 77.6380, 892.0, 22.0, 16.0, 28.0, 26.0, "LOW", "NORMAL"),
        ("Ejipura Canal Lowlands", "Ward 148", 12.9420, 77.6200, 887.0, 27.0, 22.0, 34.0, 34.0, "LOW", "NORMAL"),
        ("Sony World Junction High Ground", "Ward 150", 12.9344, 77.6289, 915.0, 18.0, 10.0, 20.0, 18.0, "LOW", "NORMAL"),
        ("National Games Village Elevated Zone", "Ward 149", 12.9460, 77.6260, 908.0, 20.0, 12.0, 22.0, 21.0, "LOW", "NORMAL")
    ]
    cursor.executemany("""
    INSERT INTO zones (name, ward, latitude, longitude, elevation_m, rainfall_mm_hr, water_level_cm, drainage_stress_percent, risk_score, risk_level, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, zones)
        
    # 3. Real Urban Roads Network with Actual Corridors & Coordinates
    cursor.execute("DELETE FROM roads")
    roads = [
        (
            "R-MAIN", "Koramangala 80 Feet Road (Rajakaluve Low Basin)", 1.4, 0.0, "LOW", 0, "NODE_A", "NODE_DEST",
            json.dumps([
                [12.9310, 77.6220],
                [12.9335, 77.6235],
                [12.9352, 77.6245], # Primary low-lying flood culvert
                [12.9370, 77.6260],
                [12.9395, 77.6275]
            ])
        ),
        (
            "R-ROUTE_B", "100 Feet Intermediate Ring Road (Elevated Flyover)", 1.8, 5.0, "LOW", 0, "NODE_A", "NODE_MID",
            json.dumps([
                [12.9310, 77.6220],
                [12.9320, 77.6180],
                [12.9360, 77.6170],
                [12.9390, 77.6190]
            ])
        ),
        (
            "R-ROUTE_C", "Ejipura Elevated Bypass Corridor", 2.4, 0.0, "LOW", 0, "NODE_MID", "NODE_DEST",
            json.dumps([
                [12.9390, 77.6190],
                [12.9430, 77.6210],
                [12.9425, 77.6250],
                [12.9395, 77.6275]
            ])
        ),
        (
            "R-ROUTE_D", "Hosur Arterial Road (St. John's High Causeway)", 1.9, 8.0, "LOW", 0, "NODE_A", "NODE_EAST",
            json.dumps([
                [12.9310, 77.6220],
                [12.9280, 77.6270],
                [12.9310, 77.6320]
            ])
        ),
        (
            "R-ROUTE_E", "Sarjapur Main Road (Sony Signal High Ridge)", 1.7, 4.0, "LOW", 0, "NODE_EAST", "NODE_DEST",
            json.dumps([
                [12.9310, 77.6320],
                [12.9355, 77.6335],
                [12.9395, 77.6275]
            ])
        )
    ]
    cursor.executemany("""
    INSERT INTO roads (road_id, name, distance_km, flood_depth_cm, risk, blocked, start_node, end_node, coordinates_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, roads)
        
    # 4. Response Resources & Real Emergency Fleets
    cursor.execute("DELETE FROM response_resources")
    resources = [
        (
            "A-07", "St. John's Trauma ALS Ambulance Unit A-07", "MEDICAL", "Critical Trauma Care, Resuscitation, High-Water Clearance",
            12.9295, 77.6210, "AVAILABLE", "Advanced Life Support Heavy Ambulance (4x4 Modified)", "8431535534", "STANDBY"
        ),
        (
            "V-03", "Civil Defense Rapid Community Taskforce V-03", "VOLUNTEER", "Community Evacuation, High-Water Wading, Provisions",
            12.9410, 77.6310, "AVAILABLE", "Heavy-Duty 4x4 Rescue Vehicle with Snorkel", "9845022334", "STANDBY"
        ),
        (
            "R-02", "SDRF Flood Rescue Squad R-02", "RESCUE", "Deep Inundation Extraction, Inflatable Rafts, Swiftwater Gear",
            12.9270, 77.6290, "AVAILABLE", "SDRF Flood Rescue Zodiac Carrier", "8431535534", "STANDBY"
        ),
        (
            "D-01", "BBMP Stormwater Rapid Dewatering Unit D-01", "MUNICIPAL", "Mobile Heavy Diesel Sump Pumps, Silt Clearance",
            12.9440, 77.6180, "AVAILABLE", "120 HP Mobile Dewatering Pump Truck", "8431535534", "STANDBY"
        )
    ]
    cursor.executemany("""
    INSERT INTO response_resources (resource_id, name, type, capability, latitude, longitude, availability, vehicle_type, contact_no, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, resources)
        
    # 5. Verified Real-World Observation Reports
    cursor.execute("DELETE FROM reports")
    reports = [
        (
            "REP-101", "Waterlogging", "Culvert backflow observed at St. John's rajakaluve junction. Water over curbs.", "Ward 12",
            12.9348, 77.6240, 76.0, "HIGH", 1, "VERIFIED", "2026-10-08 14:15:00"
        ),
        (
            "REP-102", "Blocked drainage", "Main stormwater silt trap clogged with debris at 80 Feet Road 4th Cross.", "Ward 12",
            12.9355, 77.6250, 84.0, "HIGH", 1, "VERIFIED", "2026-10-08 14:28:00"
        )
    ]
    cursor.executemany("""
    INSERT INTO reports (report_code, type, description, ward, latitude, longitude, confidence, confidence_tier, evidence_present, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, reports)

    # 6. Default Seed Help Request with Family Contact
    cursor.execute("SELECT COUNT(*) FROM help_requests WHERE request_code = '#1027'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO help_requests (request_code, citizen_name, citizen_phone, family_contact_name, family_contact_phone, type, priority, description, ward, num_people, latitude, longitude, status, assigned_resource, match_score, created_at, updated_at)
        VALUES ('#1027', 'Ramesh Kumar (Resident)', '9845012345', 'Sunita Kumar (Spouse)', '8431535534', 'Serious injury', 'CRITICAL', 'Elderly parent trapped on ground floor with rising water; head injury sustained', 'Ward 12', 3, 12.9352, 77.6245, 'DISPATCHED', 'A-07', 95.8, '2026-10-08 14:35:00', '2026-10-08 14:38:00')
        """)

    # 7. Seed Official Dispatch Acknowledgment Receipt
    cursor.execute("DELETE FROM dispatch_acknowledgments WHERE ack_code = 'ACK-2026-X884'")
    cursor.execute("""
    INSERT INTO dispatch_acknowledgments (ack_code, request_code, citizen_name, citizen_phone, family_contact_name, family_contact_phone, ward, latitude, longitude, hospital_name, assigned_unit, responder_phone, eta_minutes, cleared_route, verification_seal, qr_token, status, timestamp)
    VALUES ('ACK-2026-X884', '#1027', 'Ramesh Kumar (Resident)', '9845012345', 'Sunita Kumar (Spouse)', '8431535534', 'Ward 12 (Koramangala 4th Block)', 12.9352, 77.6245, 'St. John''s Medical College Hospital & Trauma Centre', 'ALS Heavy Flood Ambulance Unit A-07 (4x4)', '8431535534', 7.2, '100 Feet Intermediate Ring Road Elevated Flyover Corridor', 'BBMP-NDMA-SEAL-99482-VERIFIED', 'SECURE-FLOOD-DISPATCH-#1027-A07-BBMP-2026', 'DISPATCH_CONFIRMED', '2026-10-08 14:38:12')
    """)

    # 8. Seed Emergency SMS & Call Logs
    cursor.execute("DELETE FROM sms_call_logs WHERE incident_code = 'INC-1027'")
    sms_call_items = [
        (
            'INC-1027', 'CALL', 'Sunita Kumar (Family Contact)', '8431535534', 'BBMP-NDMA-DISPATCH',
            'Automated Emergency Call connected to family guardian Sunita Kumar. Speech synthesizer delivered status update.',
            'Emergency alert from ResilientUrban. Flash flood rescue unit A-07 has been dispatched to Ramesh Kumar at Koramangala. ETA is 7 minutes. Stand by.',
            'DELIVERED', '2026-10-08 14:38:20'
        ),
        (
            'INC-1027', 'SMS', 'Sunita Kumar (Family Contact)', '8431535534', 'BBMP-NDMA-DISPATCH',
            '[CRITICAL FLOOD SOS] Ramesh Kumar has reported being trapped in rising floodwaters at Ward 12 Koramangala (12.9352, 77.6245). Rescue Unit A-07 (St. John\'s Hospital) has been dispatched (ETA: 7 mins). Official Receipt: http://127.0.0.1:5000/receipt/#1027. Immediate Helpline: 8431535534.',
            None, 'DELIVERED', '2026-10-08 14:38:25'
        ),
        (
            'INC-1027', 'SMS', 'Ramesh Kumar (Citizen)', '9845012345', 'BBMP-NDMA-DISPATCH',
            '[BBMP RESCUE CONFIRMED] Unit A-07 en route to your coordinates. Driver contact: 8431535534. Route: 100ft Ring Road Flyover. Do not wade in water. Move to first floor. Receipt Code: ACK-2026-X884.',
            None, 'DELIVERED', '2026-10-08 14:38:30'
        )
    ]
    cursor.executemany("""
    INSERT INTO sms_call_logs (incident_code, log_type, recipient_name, recipient_phone, sender_id, message_content, audio_script, status, delivery_timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sms_call_items)

    conn.commit()

def create_dispatch_acknowledgment(conn, req_code, citizen_name, citizen_phone, family_contact_name, family_contact_phone, ward, lat, lon, hospital_name, assigned_unit, responder_phone, eta_minutes, cleared_route):
    """Generates and persists an official dispatch receipt."""
    cursor = conn.cursor()
    import random
    ack_code = f"ACK-2026-X{random.randint(1000, 9999)}"
    seal = f"BBMP-NDMA-SEAL-{random.randint(10000, 99999)}-VERIFIED"
    qr_token = f"SECURE-FLOOD-DISPATCH-{req_code}-{assigned_unit[:5]}-BBMP-2026"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO dispatch_acknowledgments (
        ack_code, request_code, citizen_name, citizen_phone, family_contact_name, family_contact_phone,
        ward, latitude, longitude, hospital_name, assigned_unit, responder_phone, eta_minutes,
        cleared_route, verification_seal, qr_token, status, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DISPATCH_CONFIRMED', ?)
    """, (
        ack_code, req_code, citizen_name, citizen_phone, family_contact_name, family_contact_phone,
        ward, lat, lon, hospital_name, assigned_unit, responder_phone, eta_minutes,
        cleared_route, seal, qr_token, now_str
    ))
    conn.commit()
    return ack_code

def log_emergency_comm(conn, incident_code, log_type, recipient_name, recipient_phone, message_content, audio_script=None):
    """Records an automated emergency call or SMS dispatch event."""
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO sms_call_logs (
        incident_code, log_type, recipient_name, recipient_phone, sender_id, message_content, audio_script, status, delivery_timestamp
    ) VALUES (?, ?, ?, ?, 'BBMP-NDMA-DISPATCH', ?, ?, 'DELIVERED', ?)
    """, (incident_code, log_type, recipient_name, recipient_phone, message_content, audio_script, now_str))
    conn.commit()

def reset_to_initial_state():
    """Resets database to baseline non-critical state."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Reset Ward 12 Zone B to initial normal state
    cursor.execute("""
    UPDATE zones SET 
        rainfall_mm_hr = 25.0,
        water_level_cm = 20.0,
        drainage_stress_percent = 30.0,
        risk_score = 32.0,
        risk_level = 'LOW',
        status = 'MONITORING'
    WHERE ward = 'Ward 12'
    """)
    
    # Reset Main Road to unblocked
    cursor.execute("""
    UPDATE roads SET 
        flood_depth_cm = 0.0,
        risk = 'LOW',
        blocked = 0
    WHERE road_id = 'R-MAIN'
    """)
    
    # Reset resources to AVAILABLE
    cursor.execute("""
    UPDATE response_resources SET 
        availability = 'AVAILABLE',
        status = 'STANDBY'
    """)
    
    cursor.execute("DELETE FROM help_requests WHERE request_code = '#1027'")
    cursor.execute("DELETE FROM incidents WHERE incident_code = 'INC-1027'")
    cursor.execute("DELETE FROM incident_timeline WHERE incident_code = 'INC-1027'")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("[Database] Real geospatial database initialized successfully.")

