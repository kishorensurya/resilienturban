/**
 * ResilientUrban - Main Frontend Application State Manager
 * Centralizes state, synchronizes map, dashboard, forms, and control room.
 */

window.App = (function () {
  let state = {
    hazard: "urban_flood",
    rainfall: 25,
    waterLevel: 20,
    drainageStress: 30,
    riskScore: 32,
    riskLevel: "LOW",
    kpis: {},
    zones: [],
    roads: [],
    reports: [],
    helpRequests: [],
    resources: [],
    incidents: [],
    timeline: []
  };

  async function init() {
    setupNavigation();
    setupEventHandlers();

    // Initialize Map
    if (window.ResilientMap) {
      window.ResilientMap.initMap();
    }

    // Initialize Analytics
    if (window.AnalyticsEngine) {
      window.AnalyticsEngine.init();
    }

    // Initialize Simulation
    if (window.SimulationController) {
      window.SimulationController.init();
    }

    // Fetch Central Data
    await refreshData();

    // Register PWA Service Worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }

    // Auto-refresh interval (every 6 seconds if not in active manual interaction)
    setInterval(() => {
      refreshData(false);
    }, 6000);
  }

  function setupNavigation() {
    const navButtons = document.querySelectorAll(".nav-btn");
    navButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetViewId = btn.getAttribute("data-view");
        switchView(targetViewId, btn);
      });
    });
  }

  function switchView(viewId, activeBtn = null) {
    // Hide all view sections
    document.querySelectorAll(".view-section").forEach((sec) => {
      sec.classList.remove("active");
    });

    // Deactivate all nav buttons
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      btn.classList.remove("active");
    });

    const targetSection = document.getElementById(viewId);
    if (targetSection) {
      targetSection.classList.add("active");
    }

    if (activeBtn) {
      activeBtn.classList.add("active");
    } else {
      const matchBtn = document.querySelector(`.nav-btn[data-view="${viewId}"]`);
      if (matchBtn) matchBtn.classList.add("active");
    }

    // If switching to Map or Dashboard view, invalidate Leaflet map size to ensure perfect tiles
    if (viewId === "view-dashboard" || viewId === "view-map") {
      setTimeout(() => {
        if (window.ResilientMap && window.ResilientMap.map) {
          window.ResilientMap.map.invalidateSize();
        }
      }, 150);
    }
  }

  async function refreshData(showLoader = false) {
    try {
      const res = await fetch("/api/dashboard");
      const data = await res.json();
      state = data;

      updateKPICards(state.kpis);
      updateCurrentConditionsBanner(state.current_conditions, state.primary_location);
      updateTimeline(state.timeline);
      updateIncidentTables(state.incidents, state.help_requests);
      updateRoadsList(state.roads);
      updateResourcesList(state.resources);
      updateAcknowledgmentsFeed();
      updateTelephonyFeed();

      // Synchronize Leaflet GIS map layers
      if (window.ResilientMap) {
        window.ResilientMap.renderZones(state.zones);
        window.ResilientMap.renderRoads(state.roads);
        window.ResilientMap.renderReports(state.reports);
        window.ResilientMap.renderResources(state.resources);
        window.ResilientMap.renderIncidents(state.incidents);
      }

      // Render Risk Trend chart
      if (window.AnalyticsEngine) {
        window.AnalyticsEngine.renderRiskTrend(state.risk_trend);
      }
    } catch (e) {
      console.warn("Error refreshing dashboard state:", e);
    }
  }

  function updateKPICards(kpis = {}) {
    setElText("kpi-active-flood-zones", kpis.active_flood_zones ?? 1);
    setElText("kpi-critical-zones", kpis.critical_zones ?? 1);
    setElText("kpi-blocked-roads", kpis.blocked_roads ?? 0);
    setElText("kpi-active-help-requests", kpis.active_help_requests ?? 1);
    setElText("kpi-critical-requests", kpis.critical_requests ?? 1);
    setElText("kpi-available-resources", kpis.available_resources ?? 4);
    setElText("kpi-verified-reports", kpis.verified_reports ?? 2);
    setElText("kpi-active-medical-units", kpis.active_medical_units ?? 1);
  }

  function updateCurrentConditionsBanner(cond = {}, loc = {}) {
    const risk = cond.risk_level || "LOW";
    const banner = document.getElementById("master-alert-banner");
    if (banner) {
      banner.className = `alert-banner ${risk.toLowerCase()}`;
    }

    setElText("banner-risk-level", `${risk} FLOOD RISK`);
    setElText("banner-ward-name", `${loc.ward || "Ward 12"} (${loc.zone || "Zone B"})`);
    setElText("banner-rain-val", `${cond.rainfall_mm_hr || 25} mm/h`);
    setElText("banner-water-val", `${cond.water_level_cm || 20} cm`);
    setElText("banner-drain-val", `${cond.drainage_stress_percent || 30}%`);
    setElText("banner-score-val", `${cond.risk_score || 32}%`);
  }

  function updateTimeline(timeline = []) {
    const container = document.getElementById("timeline-feed-list");
    if (!container) return;

    if (!timeline || timeline.length === 0) {
      container.innerHTML = `<p style="color: var(--text-dim); font-size: 11px; text-align: center; padding: 10px;">No critical incident transitions logged yet.</p>`;
      return;
    }

    let html = "";
    // Display in chronological order or reverse
    const reversed = [...timeline].reverse();
    reversed.forEach((item) => {
      const isCrit = item.event_title.includes("CRITICAL") || item.event_title.includes("Blocked") || item.event_title.includes("SOS");
      html += `
        <div class="timeline-item ${isCrit ? "critical" : ""}">
          <div class="timeline-header">
            <span class="timeline-title">${item.event_title}</span>
            <span class="timeline-time">${item.timestamp.split(" ")[1] || ""}</span>
          </div>
          <div class="timeline-desc">${item.event_details}</div>
        </div>
      `;
    });
    container.innerHTML = html;
  }

  function updateIncidentTables(incidents = [], requests = []) {
    // Control Room Incidents List
    const incListEl = document.getElementById("control-room-incidents");
    if (incListEl) {
      if (incidents.length === 0) {
        incListEl.innerHTML = `<p style="color: #666; font-size: 12px;">No active emergency incidents.</p>`;
      } else {
        let html = "";
        incidents.forEach((inc) => {
          const isCrit = inc.priority === "CRITICAL";
          html += `
            <div class="incident-card ${isCrit ? "critical" : ""}">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <h4 style="font-family: var(--font-tech); font-size: 14px; color: #fff;">${inc.incident_code}: ${inc.title}</h4>
                <span class="badge-tag ${inc.priority.toLowerCase()}">${inc.priority}</span>
              </div>
              <p style="font-size: 12px; color: var(--text-muted); margin: 3px 0;">Location: <strong>${inc.ward || "Ward 12"} (${inc.zone || "Zone B"})</strong></p>
              <p style="font-size: 12px; color: var(--text-muted); margin: 3px 0;">Status: <strong style="color: ${inc.status === 'RESOLVED' ? '#00e676' : '#ff1744'};">${inc.status}</strong></p>
              ${inc.assigned_resource ? `<p style="font-size: 12px; color: var(--neon-cyan); margin: 3px 0;">Unit: <strong>${inc.assigned_resource}</strong></p>` : ""}
              ${inc.route_name ? `<p style="font-size: 11px; color: #aaa; margin: 3px 0;">Route: ${inc.route_name}</p>` : ""}
              <div style="display: flex; gap: 8px; margin-top: 8px;">
                <button onclick="window.dispatchResourceModal('${inc.incident_code}')" class="btn-secondary" style="font-size: 11px; padding: 4px 10px;">Dispatch Override</button>
              </div>
            </div>
          `;
        });
        incListEl.innerHTML = html;
      }
    }

    // Help Requests Table
    const reqListEl = document.getElementById("help-requests-feed");
    if (reqListEl) {
      if (requests.length === 0) {
        reqListEl.innerHTML = `<p style="color: #666; font-size: 12px;">No help requests registered.</p>`;
      } else {
        let html = "";
        requests.forEach((req) => {
          html += `
            <div class="incident-card ${req.priority === 'CRITICAL' ? 'critical' : ''}">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-weight: 700; color: #fff; font-family: var(--font-tech);">${req.request_code} - ${req.type}</span>
                <span class="badge-tag ${req.priority.toLowerCase()}">${req.priority}</span>
              </div>
              <p style="font-size: 12px; color: var(--text-muted);">${req.description}</p>
              <div style="display: flex; justify-content: space-between; font-size: 11px; margin-top: 6px; color: #aaa;">
                <span>People: <strong>${req.num_people}</strong></span>
                <span>Status: <strong style="color: ${req.status === 'RESOLVED' ? '#00e676' : '#00e5ff'};">${req.status}</strong></span>
                ${req.assigned_resource ? `<span>Unit: <strong>${req.assigned_resource}</strong></span>` : ''}
              </div>
            </div>
          `;
        });
        reqListEl.innerHTML = html;
      }
    }
  }

  function updateRoadsList(roads = []) {
    const roadListEl = document.getElementById("roads-status-list");
    if (!roadListEl) return;

    let html = "";
    roads.forEach((r) => {
      const isBlocked = r.blocked === 1;
      html += `
        <div class="road-item ${isBlocked ? 'blocked' : ''}">
          <div class="road-meta">
            <h4>${r.name}</h4>
            <p>Dist: ${r.distance_km} km | Flood: <strong>${r.flood_depth_cm} cm</strong> | Risk: <strong style="color: ${isBlocked ? '#ff1744' : '#00e676'};">${r.risk}</strong></p>
          </div>
          <button onclick="window.toggleRoadBlock('${r.road_id}', ${!isBlocked})" 
                  class="btn-toggle-block ${isBlocked ? 'blocked' : 'unblocked'}">
            ${isBlocked ? "🚨 BLOCKED (Click to Unblock)" : "✅ PASSABLE (Click to Block)"}
          </button>
        </div>
      `;
    });
    roadListEl.innerHTML = html;
  }

  function updateResourcesList(resources = []) {
    const fleetEl = document.getElementById("fleet-resources-list");
    if (!fleetEl) return;

    let html = "";
    resources.forEach((res) => {
      const isAvailable = res.availability === "AVAILABLE";
      html += `
        <div class="incident-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <span style="font-weight: 700; color: #fff; font-family: var(--font-tech);">${res.name} (${res.resource_id})</span>
            <span class="badge-tag ${isAvailable ? 'low' : 'critical'}">${res.availability}</span>
          </div>
          <p style="font-size: 12px; color: var(--text-muted); margin: 2px 0;">Capability: <strong>${res.capability}</strong></p>
          <p style="font-size: 12px; color: var(--text-muted); margin: 2px 0;">Vehicle: ${res.vehicle_type}</p>
          <div style="display: flex; justify-content: space-between; font-size: 11px; margin-top: 6px;">
            <span>Contact/Dispatch: <strong style="color: var(--neon-amber);">${res.contact_no}</strong></span>
            <span>Status: <strong>${res.status}</strong></span>
          </div>
        </div>
      `;
    });
    fleetEl.innerHTML = html;
  }

  function setupEventHandlers() {
    // Road blockage handler attached to window
    window.toggleRoadBlock = async function (roadId, blocked) {
      try {
        await fetch("/api/roads/block", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ road_id: roadId, blocked: blocked })
        });
        await refreshData();
        // If blocked, automatically trigger route recalculation
        const routeRes = await fetch("/api/route");
        const routeData = await routeRes.json();
        if (window.ResilientMap) {
          window.ResilientMap.highlightAlternativeRoute(routeData);
        }
      } catch (e) {
        console.error("Toggle road block error:", e);
      }
    };

    // Calculate Route Button
    const btnCalcRoute = document.getElementById("btn-calc-route");
    if (btnCalcRoute) {
      btnCalcRoute.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/route");
          const route = await res.json();
          const displayEl = document.getElementById("route-result-display");
          if (displayEl) {
            displayEl.innerHTML = `
              <h4 style="color: #00e5ff; font-family: var(--font-display); font-size: 14px; margin-bottom: 6px;">${route.route_label}</h4>
              <p style="font-size: 12px; margin: 3px 0;">Corridor: <strong>${route.roads_used ? route.roads_used.join(" -> ") : "N/A"}</strong></p>
              <p style="font-size: 12px; margin: 3px 0;">Total Distance: <strong>${route.total_distance_km} km</strong> (~${route.estimated_travel_time_min} mins)</p>
              <p style="font-size: 12px; margin: 3px 0;">Route Risk: <strong style="color: #00e676;">${route.route_risk_level}</strong></p>
              <div style="margin-top: 6px; font-size: 11px; color: #ffab00; background: rgba(255,171,0,0.1); padding: 6px; border-radius: 4px;">
                ${route.comparison_note}
              </div>
              <p style="font-size: 9px; color: #888; margin-top: 6px;">${route.disclaimer}</p>
            `;
          }
          if (window.ResilientMap) {
            window.ResilientMap.highlightAlternativeRoute(route);
          }
        } catch (e) {
          console.error("Calculate route failed:", e);
        }
      });
    }

    // Citizen Community Report Form
    const reportForm = document.getElementById("form-citizen-report");
    if (reportForm) {
      reportForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const repType = document.getElementById("rep-type").value;
        const repDesc = document.getElementById("rep-desc").value;
        const repWard = document.getElementById("rep-ward").value;
        const repEvidence = document.getElementById("rep-evidence").checked;

        try {
          const res = await fetch("/api/reports", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              type: repType,
              description: repDesc,
              ward: repWard,
              evidence: repEvidence,
              latitude: 12.9352 + (Math.random() - 0.5) * 0.005,
              longitude: 77.6245 + (Math.random() - 0.5) * 0.005
            })
          });
          const result = await res.json();
          alert(`Report registered successfully!\nReport ID: ${result.report_code}\nConfidence Score: ${result.confidence}% (${result.tier})\n${result.formula_explanation}`);
          reportForm.reset();
          await refreshData();
        } catch (err) {
          alert("Error submitting report: " + err.message);
        }
      });
    }

    // Help / SOS Request Form
    const sosForm = document.getElementById("form-sos-request");
    if (sosForm) {
      sosForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const sosType = document.getElementById("sos-type").value;
        const sosPeople = parseInt(document.getElementById("sos-people").value) || 1;
        const sosDesc = document.getElementById("sos-desc").value;
        const sosWard = document.getElementById("sos-ward").value;

        try {
          const res = await fetch("/api/help-requests", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              type: sosType,
              num_people: sosPeople,
              description: sosDesc,
              ward: sosWard,
              latitude: 12.9352,
              longitude: 77.6245
            })
          });
          const result = await res.json();
          alert(`SOS Request Registered!\nRequest Code: ${result.request_code}\nPriority Classified: ${result.priority}\nDispatch team alerted in Municipal Control Room.`);
          sosForm.reset();
          await refreshData();
        } catch (err) {
          alert("Error submitting SOS: " + err.message);
        }
      });
    }

    // Resource Match Tester
    const btnTestMatch = document.getElementById("btn-test-match");
    if (btnTestMatch) {
      btnTestMatch.addEventListener("click", async () => {
        const reqType = document.getElementById("match-req-type").value;
        const wCap = parseFloat(document.getElementById("match-w-cap").value) / 100;
        const wAvail = parseFloat(document.getElementById("match-w-avail").value) / 100;
        const wDist = parseFloat(document.getElementById("match-w-dist").value) / 100;
        const wRisk = parseFloat(document.getElementById("match-w-risk").value) / 100;

        try {
          const res = await fetch("/api/match-resource", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              type: reqType,
              weights: {
                capability: wCap,
                availability: wAvail,
                distance: wDist,
                route_risk: wRisk
              }
            })
          });
          const result = await res.json();
          const matchEl = document.getElementById("match-result-box");
          if (matchEl && result.best_match) {
            const b = result.best_match;
            matchEl.innerHTML = `
              <div style="background: rgba(0, 229, 255, 0.08); border: 1px solid var(--neon-cyan); border-radius: 8px; padding: 12px;">
                <h4 style="color: var(--neon-cyan); margin: 0 0 6px;">TOP MATCH: ${b.resource.name} (${b.resource.resource_id})</h4>
                <p style="font-size: 13px; margin: 3px 0;">Match Score: <strong style="color: #00e676; font-size: 16px;">${b.match_score}%</strong></p>
                <p style="font-size: 12px; margin: 3px 0;">Distance: <strong>${b.distance_km} km</strong> | Vehicle: ${b.resource.vehicle_type}</p>
                <hr style="border-color: rgba(255,255,255,0.1); margin: 6px 0;">
                <div style="font-size: 11px; display: grid; grid-template-columns: 1fr 1fr; gap: 4px; color: #aaa;">
                  <span>Capability: ${b.breakdown.capability}%</span>
                  <span>Availability: ${b.breakdown.availability}%</span>
                  <span>Proximity: ${b.breakdown.distance}%</span>
                  <span>Route Safety: ${b.breakdown.route_risk}%</span>
                </div>
                <small style="color: #888; display: block; margin-top: 6px;">${result.disclaimer}</small>
              </div>
            `;
          }
        } catch (e) {
          console.error("Match tester error:", e);
        }
      });
    }

    // Live Weather Telemetry Sync Button
    const btnSyncWeather = document.getElementById("btn-sync-live-weather");
    const selectCity = document.getElementById("select-city");
    if (btnSyncWeather && selectCity) {
      btnSyncWeather.addEventListener("click", async () => {
        btnSyncWeather.innerHTML = `<span>⏳</span> Fetching Live Telemetry...`;
        btnSyncWeather.disabled = true;
        try {
          const res = await fetch("/api/weather/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ city: selectCity.value })
          });
          const data = await res.json();
          if (data.status === "SYNCED" && data.weather) {
            const w = data.weather;
            const tempEl = document.getElementById("telemetry-temp");
            const precipEl = document.getElementById("telemetry-precip");
            const humEl = document.getElementById("telemetry-humidity");
            const pressEl = document.getElementById("telemetry-pressure");
            const windEl = document.getElementById("telemetry-wind");
            if (tempEl) tempEl.textContent = `${w.temperature_c}°C`;
            if (precipEl) precipEl.textContent = `${w.rain_mm_hr} mm/h`;
            if (humEl) humEl.textContent = `${w.relative_humidity_percent}%`;
            if (pressEl) pressEl.textContent = `${w.surface_pressure_hpa} hPa`;
            if (windEl) windEl.textContent = `${w.wind_speed_kmh} km/h`;
            await refreshData();
          }
        } catch (we) {
          console.error("Live weather sync error:", we);
        } finally {
          btnSyncWeather.innerHTML = `<span>🔄</span> Sync Live Weather Telemetry`;
          btnSyncWeather.disabled = false;
        }
      });
    }

    // Simulation auto-run button
    const btnRunDemo = document.getElementById("btn-run-demo");
    if (btnRunDemo) {
      btnRunDemo.addEventListener("click", () => {
        window.SimulationController.startAutoRun();
      });
    }

    // Simulation step forward button
    const btnNextStep = document.getElementById("btn-next-step");
    if (btnNextStep) {
      btnNextStep.addEventListener("click", () => {
        window.SimulationController.nextStep();
      });
    }

    // Simulation reset button
    const btnResetDemo = document.getElementById("btn-reset-demo");
    if (btnResetDemo) {
      btnResetDemo.addEventListener("click", () => {
        window.SimulationController.resetSimulation();
      });
    }
  }

  async function updateAcknowledgmentsFeed() {
    const el = document.getElementById("acknowledgments-feed");
    if (!el) return;
    try {
      const res = await fetch("/api/acknowledgments");
      const data = await res.json();
      const acks = data.acknowledgments || [];
      if (acks.length === 0) {
        el.innerHTML = `<p style="color:var(--text-dim); font-size:11px;">No confirmed dispatch receipts yet.</p>`;
        return;
      }
      let html = "";
      acks.forEach(a => {
        html += `
          <div style="background:rgba(0,0,0,0.35); border:1px solid #1e293b; border-left:3px solid #00e676; border-radius:6px; padding:8px 10px; font-size:11px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">
              <strong style="color:var(--neon-cyan); font-family:var(--font-tech);">${a.ack_code} (${a.request_code})</strong>
              <span style="color:#00e676; font-size:10px; font-weight:bold;">${a.status}</span>
            </div>
            <div style="color:#fff; font-weight:600;">Citizen: ${a.citizen_name} &bull; Ward: ${a.ward}</div>
            <div style="color:var(--text-dim); margin:2px 0;">Unit: <strong>${a.assigned_unit}</strong> &bull; ETA: <strong>${a.eta_minutes} mins</strong></div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
              <span style="color:#888; font-size:10px;">${a.timestamp}</span>
              <a href="/receipt/${a.request_code}" target="_blank" style="background:#0284c7; color:#fff; padding:3px 8px; border-radius:4px; text-decoration:none; font-size:10px; font-weight:bold;">
                🖨️ View & Print Receipt
              </a>
            </div>
          </div>
        `;
      });
      el.innerHTML = html;
    } catch (e) {
      console.warn("Error updating acknowledgments feed:", e);
    }
  }

  async function updateTelephonyFeed() {
    const el = document.getElementById("telephony-feed");
    if (!el) return;
    try {
      const res = await fetch("/api/comms/logs");
      const data = await res.json();
      const logs = data.logs || [];
      if (logs.length === 0) {
        el.innerHTML = `<p style="color:var(--text-dim); font-size:11px;">No outgoing calls or SMS records logged.</p>`;
        return;
      }
      let html = "";
      logs.forEach(l => {
        const isCall = l.log_type === "CALL";
        html += `
          <div style="background:rgba(0,0,0,0.35); border:1px solid #1e293b; border-left:3px solid ${isCall ? '#ffab00' : '#00e5ff'}; border-radius:6px; padding:8px 10px; font-size:11px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">
              <span style="font-weight:bold; color:${isCall ? '#ffab00' : '#00e5ff'};">${isCall ? '📞 EMERGENCY CALL' : '💬 SMS TRANSMISSION'}</span>
              <span style="color:#888; font-size:10px;">${l.delivery_timestamp.split(' ')[1] || ''}</span>
            </div>
            <div style="color:#fff;">Recipient: <strong>${l.recipient_name} (${l.recipient_phone})</strong></div>
            <div style="color:var(--text-dim); margin-top:3px; line-height:1.3; font-style:italic;">"${l.message_content}"</div>
          </div>
        `;
      });
      el.innerHTML = html;
    } catch (e) {
      console.warn("Error updating telephony feed:", e);
    }
  }

  window.triggerRandomStressTest = async function(isFalseReport) {
    const btnResults = document.getElementById("random-stress-results");
    if (btnResults) {
      btnResults.style.display = "block";
      btnResults.innerHTML = `<span style="color:var(--neon-cyan);">⏳ Running Monte Carlo Stochastic Inundation & Recalculating All Parameters...</span>`;
    }

    const rSlider = document.getElementById("rand-rain-slider");
    const dSlider = document.getElementById("rand-depth-slider");
    const drSlider = document.getElementById("rand-drain-slider");

    let rain = rSlider ? parseFloat(rSlider.value) : 85;
    let depth = dSlider ? parseFloat(dSlider.value) : 75;
    let drain = drSlider ? parseFloat(drSlider.value) : 80;

    if (!isFalseReport) {
      rain = Math.round(25 + Math.random() * 155);
      depth = Math.round(rain * 0.9 + (Math.random() * 20 - 10));
      drain = Math.min(100, Math.round(rain * 0.7 + 20));

      if (rSlider) { rSlider.value = rain; document.getElementById('rand-rain-val').textContent = rain + ' mm/h'; }
      if (dSlider) { dSlider.value = depth; document.getElementById('rand-depth-val').textContent = depth + ' cm'; }
      if (drSlider) { drSlider.value = drain; document.getElementById('rand-drain-val').textContent = drain + '%'; }
    }

    try {
      const res = await fetch("/api/simulation/randomize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rainfall_mm_hr: rain,
          water_level_cm: depth,
          drainage_stress_percent: drain
        })
      });
      const data = await res.json();

      const clockEl = document.getElementById("sim-clock-display");
      if (clockEl) {
        clockEl.textContent = `SIM CLOCK: ${data.simulation_time.split(" ")[1]}`;
      }

      if (btnResults) {
        let falseHtml = "";
        if (data.false_data_stress_test) {
          const f = data.false_data_stress_test;
          falseHtml = `
            <div style="margin-top:8px; padding:6px; background:${f.is_false_or_noise ? 'rgba(239,68,68,0.15)' : 'rgba(0,230,118,0.15)'}; border-left:3px solid ${f.is_false_or_noise ? '#ff1744' : '#00e676'}; border-radius:4px;">
              <strong>${f.is_false_or_noise ? '🚫 FILTERED FALSE DATA / SPAM REPORT:' : '✅ VERIFIED OBSERVATION:'}</strong> ${f.description}<br>
              Confidence Score: <strong>${f.confidence}% (${f.tier})</strong> &bull; ${f.is_false_or_noise ? 'Flagged as low-confidence noise (<50%) and withheld from triggering municipal dispatch.' : 'Cross-validated against hydraulic telemetry.'}
            </div>
          `;
        }

        btnResults.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <strong style="color:#00e5ff;">🎲 STOCHASTIC SIMULATION RESULTS (${data.simulation_time})</strong>
            <span class="badge-tag ${data.calculated_risk.hybrid_risk_level.toLowerCase()}">${data.calculated_risk.hybrid_risk_level} RISK</span>
          </div>
          <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; margin-bottom:8px;">
            <div>Rain: <strong>${data.random_inputs.rainfall_mm_hr} mm/h</strong></div>
            <div>Water: <strong>${data.random_inputs.water_level_cm} cm</strong></div>
            <div>Drainage: <strong>${data.random_inputs.drainage_stress_percent}%</strong></div>
            <div>RF Prob: <strong>${Math.round(data.calculated_risk.random_forest_risk_probability * 100)}%</strong></div>
          </div>
          <div style="color:#ffab00;">
            Road Network Status: <strong>${data.road_status.main_road_blocked ? '🚨 Koramangala 80ft Low Basin Road Submerged & Blocked!' : '✅ Roads Passable'}</strong>
          </div>
          <div style="color:#00e676; margin-top:3px;">
            Dijkstra Safe Bypass: <strong>${data.dijkstra_reroute.chosen_route ? data.dijkstra_reroute.chosen_route.name : 'Direct High Causeway'}</strong>
          </div>
          ${falseHtml}
        `;
      }

      await refreshData();
    } catch (e) {
      console.error("Random stress test error:", e);
      if (btnResults) {
        btnResults.innerHTML = `<span style="color:#ff1744;">Error running randomized stress test: ${e.message}</span>`;
      }
    }
  };

  function setElText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  return {
    init,
    refreshData,
    switchView
  };
})();

// Global PWA Mobile Install Handler
let deferredPwaPrompt = null;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPwaPrompt = e;
  const btn = document.getElementById("pwa-install-btn");
  if (btn) btn.style.boxShadow = "0 0 20px rgba(14,165,233,0.8)";
});

window.triggerPwaInstall = function() {
  if (deferredPwaPrompt) {
    deferredPwaPrompt.prompt();
    deferredPwaPrompt.userChoice.then((choiceResult) => {
      deferredPwaPrompt = null;
    });
  } else {
    alert("To install directly onto your Android device without any APK errors:\n\n1. Open this page in Google Chrome on your phone:\n   http://10.133.91.215:5000/citizen\n\n2. Tap Chrome's menu (⋮) in the top-right corner.\n3. Tap 'Install app' (or 'Add to Home screen').\n\nAndroid will immediately install the official ResilientUrban WebAPK directly to your app drawer!");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  window.App.init();
});

