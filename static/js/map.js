/**
 * ResilientUrban - GIS & Interactive Leaflet 3D Styled Map Module
 * Visualizes flood zones, road blockages, lower-risk alternative routes,
 * citizen reports, and emergency medical response units.
 */

window.ResilientMap = (function () {
  let map = null;
  let zonesLayerGroup = null;
  let roadsLayerGroup = null;
  let routePathLayer = null;
  let reportsLayerGroup = null;
  let resourcesLayerGroup = null;
  let incidentsLayerGroup = null;
  let userMarker = null;

  // Custom SVG Markers
  function createPulseIcon(color, emoji = "⚠️", isCritical = false) {
    const pulseClass = isCritical ? "pulse-ring critical" : "pulse-ring";
    return L.divIcon({
      className: "custom-map-icon",
      html: `
        <div style="position: relative; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">
          <div style="position: absolute; width: 32px; height: 32px; border-radius: 50%; background: ${color}; opacity: 0.25; animation: ping 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
          <div style="width: 28px; height: 28px; border-radius: 50%; background: rgba(10, 16, 30, 0.9); border: 2px solid ${color}; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 12px ${color}; font-size: 14px;">
            ${emoji}
          </div>
        </div>
      `,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
      popupAnchor: [0, -18]
    });
  }

  function initMap() {
    if (map) return;

    // Center on Ward 12 (Koramangala Basin)
    map = L.map("map", {
      center: [12.9365, 77.6255],
      zoom: 15,
      zoomControl: true
    });

    // 100% Free OpenStreetMap Standard Tiles — Zero API Keys Required
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    zonesLayerGroup = L.layerGroup().addTo(map);
    roadsLayerGroup = L.layerGroup().addTo(map);
    reportsLayerGroup = L.layerGroup().addTo(map);
    resourcesLayerGroup = L.layerGroup().addTo(map);
    incidentsLayerGroup = L.layerGroup().addTo(map);

    // Initial default catchment station location marker
    setUserLocation(12.9352, 77.6245, "Koramangala 4th Block Basin (Monitoring Station)");
  }

  function locateUserDevice() {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          setUserLocation(lat, lon, "Your Detected GPS Location");
          if (map) map.flyTo([lat, lon], 16);
        },
        (err) => {
          alert("Location note: Device GPS access was not granted. Using default municipal monitoring station (Koramangala Basin).");
        },
        { timeout: 7000 }
      );
    } else {
      alert("Geolocation is not supported by your browser. Using municipal basin coordinates.");
    }
  }

  function setUserLocation(lat, lon, label) {
    if (!map) return;
    if (userMarker) map.removeLayer(userMarker);

    const userIcon = L.divIcon({
      className: "user-loc-icon",
      html: `
        <div style="position: relative; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;">
          <div style="position: absolute; width: 30px; height: 30px; border-radius: 50%; background: #00e5ff; opacity: 0.3; animation: ping 2s infinite;"></div>
          <div style="width: 24px; height: 24px; border-radius: 50%; background: #00e5ff; border: 3px solid #fff; box-shadow: 0 0 16px #00e5ff; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #000; font-weight: bold;">
            📍
          </div>
        </div>
      `,
      iconSize: [34, 34],
      iconAnchor: [17, 17]
    });

    userMarker = L.marker([lat, lon], { icon: userIcon }).addTo(map);
    userMarker.bindPopup(`
      <div style="color: #000; font-family: sans-serif;">
        <strong>User Location</strong><br>
        <span>${label}</span><br>
        <small style="color: #666;">Lat: ${lat.toFixed(4)}, Lon: ${lon.toFixed(4)}</small>
      </div>
    `);
  }

  function getRiskColor(level) {
    switch (level) {
      case "CRITICAL": return "#ff1744";
      case "HIGH": return "#ff9100";
      case "MODERATE": return "#ffab00";
      case "LOW":
      default: return "#00e676";
    }
  }

  function renderZones(zones) {
    if (!map || !zonesLayerGroup) return;
    zonesLayerGroup.clearLayers();

    zones.forEach((z) => {
      const color = getRiskColor(z.risk_level);
      const isCritical = z.risk_level === "CRITICAL";

      // Circular flood risk catchment
      const circle = L.circle([z.latitude, z.longitude], {
        radius: isCritical ? 380 : 320,
        color: color,
        fillColor: color,
        fillOpacity: isCritical ? 0.32 : 0.16,
        weight: isCritical ? 3 : 1.5,
        dashArray: isCritical ? "4, 6" : null
      });

      circle.bindPopup(`
        <div style="color: #fff; background: rgba(14,22,41,0.95); padding: 10px; border-radius: 8px; border: 1px solid ${color}; min-width: 200px;">
          <h4 style="margin: 0 0 4px; color: ${color}; font-family: 'Rajdhani', sans-serif; font-size: 16px;">${z.ward} - ${z.name}</h4>
          <p style="margin: 2px 0; font-size: 12px; color: #ccc;">Status: <strong>${z.status}</strong></p>
          <p style="margin: 2px 0; font-size: 12px; color: #ccc;">Risk Score: <strong>${z.risk_score}% (${z.risk_level})</strong></p>
          <hr style="border-color: rgba(255,255,255,0.1); margin: 6px 0;">
          <div style="font-size: 11px; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
            <span>Rain: <strong>${z.rainfall_mm_hr} mm/h</strong></span>
            <span>Water: <strong>${z.water_level_cm} cm</strong></span>
            <span>Drainage: <strong>${z.drainage_stress_percent}%</strong></span>
            <span>Elevation: <strong>${z.elevation_m}m</strong></span>
          </div>
        </div>
      `, { className: "dark-popup" });

      zonesLayerGroup.addLayer(circle);
    });
  }

  function renderRoads(roads) {
    if (!map || !roadsLayerGroup) return;
    roadsLayerGroup.clearLayers();

    roads.forEach((r) => {
      if (!r.coordinates || r.coordinates.length < 2) return;

      const isBlocked = r.blocked === 1;
      const roadColor = isBlocked ? "#ff1744" : "#455a64";
      const weight = isBlocked ? 7 : 4;
      const opacity = isBlocked ? 0.9 : 0.6;

      const polyline = L.polyline(r.coordinates, {
        color: roadColor,
        weight: weight,
        opacity: opacity,
        dashArray: isBlocked ? "6, 8" : null
      });

      polyline.bindPopup(`
        <div style="color: #fff; background: rgba(14,22,41,0.95); padding: 10px; border-radius: 8px; border: 1px solid ${roadColor};">
          <h4 style="margin: 0 0 4px; color: ${roadColor}; font-size: 14px;">${r.name}</h4>
          <p style="margin: 2px 0; font-size: 12px;">Distance: ${r.distance_km} km</p>
          <p style="margin: 2px 0; font-size: 12px;">Flood Depth: <strong>${r.flood_depth_cm} cm</strong></p>
          <p style="margin: 2px 0; font-size: 12px;">Condition: <strong>${isBlocked ? "🚨 BLOCKED / IMPASSABLE" : "✅ CLEAR / PASSABLE"}</strong></p>
          <button onclick="window.toggleRoadBlock('${r.road_id}', ${!isBlocked})" 
                  style="margin-top: 8px; padding: 4px 10px; background: ${isBlocked ? '#00e676' : '#ff1744'}; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 11px;">
            ${isBlocked ? "Unblock Road" : "Mark as Blocked"}
          </button>
        </div>
      `, { className: "dark-popup" });

      roadsLayerGroup.addLayer(polyline);

      // Add a barrier icon marker at midpoint if blocked
      if (isBlocked) {
        const midIdx = Math.floor(r.coordinates.length / 2);
        const midPoint = r.coordinates[midIdx];
        const barrierIcon = createPulseIcon("#ff1744", "🚫", true);
        const marker = L.marker(midPoint, { icon: barrierIcon });
        marker.bindPopup(`<strong style="color: #ff1744;">ROAD BLOCKED: ${r.name}</strong><br>Water Depth: ${r.flood_depth_cm} cm.`);
        roadsLayerGroup.addLayer(marker);
      }
    });
  }

  function highlightAlternativeRoute(routeData) {
    if (!map) return;
    if (routePathLayer) map.removeLayer(routePathLayer);

    if (!routeData || !routeData.waypoints || routeData.waypoints.length === 0) return;

    // Glowing cyan / neon polyline with animated styling
    routePathLayer = L.polyline(routeData.waypoints, {
      color: "#00e5ff",
      weight: 6,
      opacity: 0.95,
      lineCap: "round",
      dashArray: "10, 8",
      className: "animated-route-line"
    }).addTo(map);

    routePathLayer.bindPopup(`
      <div style="color: #fff; background: rgba(10,18,36,0.95); padding: 10px; border-radius: 8px; border: 1px solid #00e5ff; min-width: 220px;">
        <h4 style="margin: 0 0 4px; color: #00e5ff; font-family: 'Orbitron', sans-serif; font-size: 13px;">${routeData.route_label}</h4>
        <p style="margin: 2px 0; font-size: 12px; color: #ccc;">Total Distance: <strong>${routeData.total_distance_km} km</strong></p>
        <p style="margin: 2px 0; font-size: 12px; color: #ccc;">Est. Travel Time: <strong>~${routeData.estimated_travel_time_min} mins</strong></p>
        <p style="margin: 2px 0; font-size: 12px; color: #ccc;">Route Risk: <strong style="color: #00e676;">${routeData.route_risk_level}</strong></p>
        <div style="margin-top: 6px; font-size: 10px; color: #ffab00; background: rgba(255,171,0,0.1); padding: 4px; border-radius: 4px;">
          ${routeData.comparison_note}
        </div>
        <p style="font-size: 9px; color: #888; margin-top: 6px;">${routeData.disclaimer}</p>
      </div>
    `, { className: "dark-popup" }).openPopup();

    map.fitBounds(routePathLayer.getBounds(), { padding: [50, 50] });
  }

  function renderReports(reports) {
    if (!map || !reportsLayerGroup) return;
    reportsLayerGroup.clearLayers();

    reports.forEach((rep) => {
      const icon = createPulseIcon("#ffab00", "📢");
      const marker = L.marker([rep.latitude, rep.longitude], { icon: icon });
      marker.bindPopup(`
        <div style="color: #fff; background: rgba(14,22,41,0.95); padding: 10px; border-radius: 8px; border: 1px solid #ffab00; min-width: 200px;">
          <h4 style="margin: 0 0 4px; color: #ffab00; font-size: 14px;">${rep.type} (${rep.report_code})</h4>
          <p style="margin: 2px 0; font-size: 12px; color: #ccc;">${rep.description}</p>
          <div style="margin-top: 6px; display: flex; justify-content: space-between; font-size: 11px;">
            <span>Confidence: <strong style="color: #00e5ff;">${rep.confidence}% (${rep.confidence_tier})</strong></span>
            <span>Evidence: <strong>${rep.evidence_present ? "📷 Yes" : "No"}</strong></span>
          </div>
          <small style="color: #777; display: block; margin-top: 4px;">${rep.created_at}</small>
        </div>
      `, { className: "dark-popup" });
      reportsLayerGroup.addLayer(marker);
    });
  }

  function renderResources(resources) {
    if (!map || !resourcesLayerGroup) return;
    resourcesLayerGroup.clearLayers();

    resources.forEach((res) => {
      const isAvailable = res.availability === "AVAILABLE";
      const iconColor = res.type === "MEDICAL" ? "#2979ff" : (res.type === "RESCUE" ? "#ff9100" : "#00e676");
      const emoji = res.type === "MEDICAL" ? "🚑" : (res.type === "RESCUE" ? "🚤" : "🚙");

      const icon = createPulseIcon(iconColor, emoji, res.status === "EN ROUTE");
      const marker = L.marker([res.latitude, res.longitude], { icon: icon });
      marker.bindPopup(`
        <div style="color: #fff; background: rgba(14,22,41,0.95); padding: 10px; border-radius: 8px; border: 1px solid ${iconColor}; min-width: 220px;">
          <h4 style="margin: 0 0 4px; color: ${iconColor}; font-size: 14px;">${res.name} (${res.resource_id})</h4>
          <p style="margin: 2px 0; font-size: 12px; color: #ccc;">Type: <strong>${res.type}</strong></p>
          <p style="margin: 2px 0; font-size: 12px; color: #ccc;">Capability: <em>${res.capability}</em></p>
          <p style="margin: 2px 0; font-size: 12px; color: #ccc;">Vehicle: ${res.vehicle_type}</p>
          <p style="margin: 2px 0; font-size: 12px;">Status: <strong style="color: ${isAvailable ? '#00e676' : '#ff1744'};">${res.availability} (${res.status})</strong></p>
          <p style="margin: 2px 0; font-size: 11px; color: #aaa;">Helpline/Dispatch: <strong>${res.contact_no}</strong></p>
        </div>
      `, { className: "dark-popup" });
      resourcesLayerGroup.addLayer(marker);
    });
  }

  function renderIncidents(incidents) {
    if (!map || !incidentsLayerGroup) return;
    incidentsLayerGroup.clearLayers();

    incidents.forEach((inc) => {
      if (!inc.latitude || !inc.longitude) return;
      const isCritical = inc.priority === "CRITICAL";
      const isResolved = inc.status === "RESOLVED";
      const color = isResolved ? "#00e676" : (isCritical ? "#ff1744" : "#ff9100");
      const emoji = isResolved ? "✅" : (isCritical ? "🚨" : "⚠️");

      const icon = createPulseIcon(color, emoji, !isResolved && isCritical);
      const marker = L.marker([inc.latitude, inc.longitude], { icon: icon });
      marker.bindPopup(`
        <div style="color: #fff; background: rgba(14,22,41,0.95); padding: 10px; border-radius: 8px; border: 1px solid ${color}; min-width: 220px;">
          <h4 style="margin: 0 0 4px; color: ${color}; font-size: 14px;">${inc.incident_code}: ${inc.title}</h4>
          <p style="margin: 2px 0; font-size: 12px; color: #ccc;">Priority: <strong>${inc.priority}</strong></p>
          <p style="margin: 2px 0; font-size: 12px; color: #ccc;">Status: <strong style="color: ${color};">${inc.status}</strong></p>
          ${inc.assigned_resource ? `<p style="margin: 2px 0; font-size: 12px; color: #00e5ff;">Assigned: ${inc.assigned_resource}</p>` : ""}
          ${inc.route_name ? `<p style="margin: 2px 0; font-size: 11px; color: #aaa;">Route: ${inc.route_name}</p>` : ""}
        </div>
      `, { className: "dark-popup" });
      incidentsLayerGroup.addLayer(marker);
    });
  }

  function focusOnLocation(lat, lon, zoom = 16) {
    if (map) {
      map.flyTo([lat, lon], zoom, { duration: 1.2 });
    }
  }

  return {
    initMap,
    renderZones,
    renderRoads,
    renderReports,
    renderResources,
    renderIncidents,
    highlightAlternativeRoute,
    focusOnLocation,
    setUserLocation,
    locateUserDevice
  };
})();
