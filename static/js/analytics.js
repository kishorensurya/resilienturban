/**
 * ResilientUrban - Machine Learning & Hydrological Analytics Visualizer
 * Renders Random Forest feature importance, confusion matrix,
 * configurable baseline weight sliders, and risk progression curves.
 */

window.AnalyticsEngine = (function () {
  let mlMetrics = null;

  async function loadMetrics() {
    try {
      const res = await fetch("/api/ml/metrics");
      mlMetrics = await res.json();
      renderEvaluation();
      renderFeatureImportance();
    } catch (e) {
      console.warn("Could not load ML metrics:", e);
    }
  }

  function renderEvaluation() {
    if (!mlMetrics) return;

    const metrics = mlMetrics.metrics || {};
    const accEl = document.getElementById("metric-accuracy");
    const precEl = document.getElementById("metric-precision");
    const recEl = document.getElementById("metric-recall");

    if (accEl) accEl.textContent = `${(metrics.accuracy * 100).toFixed(1)}%`;
    if (precEl) precEl.textContent = `${(metrics.precision * 100).toFixed(1)}%`;
    if (recEl) recEl.textContent = `${(metrics.recall * 100).toFixed(1)}%`;

    // Confusion Matrix: [[TN, FP], [FN, TP]]
    const cm = metrics.confusion_matrix || [[0, 0], [0, 0]];
    const cmEl = document.getElementById("confusion-matrix-body");
    if (cmEl) {
      cmEl.innerHTML = `
        <tr>
          <td><strong>Actual No Flood</strong></td>
          <td class="cm-highlight">${cm[0][0]} (True Neg)</td>
          <td>${cm[0][1]} (False Pos)</td>
        </tr>
        <tr>
          <td><strong>Actual Flood</strong></td>
          <td>${cm[1][0]} (False Neg)</td>
          <td class="cm-highlight">${cm[1][1]} (True Pos)</td>
        </tr>
      `;
    }
  }

  function renderFeatureImportance() {
    if (!mlMetrics || !mlMetrics.feature_importance) return;
    const container = document.getElementById("feature-importance-list");
    if (!container) return;

    const importances = mlMetrics.feature_importance;
    const maxVal = Math.max(...Object.values(importances));

    let html = "";
    for (const [feat, val] of Object.entries(importances)) {
      const percent = Math.round((val / maxVal) * 100);
      const cleanName = feat.replace(/_/g, " ").toUpperCase();
      html += `
        <div class="feature-bar-row">
          <div class="feature-bar-meta">
            <span>${cleanName}</span>
            <span style="color: var(--neon-cyan); font-weight: 700;">${(val * 100).toFixed(1)}%</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill" style="width: ${percent}%;"></div>
          </div>
        </div>
      `;
    }
    container.innerHTML = html;
  }

  // Interactive Live Baseline Risk Calculator with Slider Weights
  async function recalculateCustomRisk() {
    const rain = parseFloat(document.getElementById("slider-rain")?.value || 72);
    const water = parseFloat(document.getElementById("slider-water")?.value || 68);
    const drain = parseFloat(document.getElementById("slider-drain")?.value || 71);
    const conf = parseFloat(document.getElementById("slider-conf")?.value || 88);

    const wRain = parseFloat(document.getElementById("weight-rain")?.value || 35) / 100;
    const wWater = parseFloat(document.getElementById("weight-water")?.value || 30) / 100;
    const wDrain = parseFloat(document.getElementById("weight-drain")?.value || 20) / 100;
    const wConf = parseFloat(document.getElementById("weight-conf")?.value || 15) / 100;

    // Display current slider values in UI
    const vRain = document.getElementById("val-rain");
    const vWater = document.getElementById("val-water");
    const vDrain = document.getElementById("val-drain");
    const vConf = document.getElementById("val-conf");

    if (vRain) vRain.textContent = `${rain} mm/h`;
    if (vWater) vWater.textContent = `${water} cm`;
    if (vDrain) vDrain.textContent = `${drain}%`;
    if (vConf) vConf.textContent = `${conf}%`;

    try {
      const res = await fetch("/api/risk/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rainfall_mm_hr: rain,
          water_level_cm: water,
          drainage_stress_percent: drain,
          report_confidence: conf,
          weights: {
            rainfall: wRain,
            water_level: wWater,
            drainage_stress: wDrain,
            citizen_reports: wConf
          }
        })
      });
      const data = await res.json();

      // Update comparison pillars
      const mlProbEl = document.getElementById("analytics-ml-prob");
      const mlBadgeEl = document.getElementById("analytics-ml-badge");
      const baseScoreEl = document.getElementById("analytics-base-score");
      const baseBadgeEl = document.getElementById("analytics-base-badge");
      const hybridScoreEl = document.getElementById("analytics-hybrid-score");

      if (mlProbEl) mlProbEl.textContent = `${data.ml_probability_percent}%`;
      if (mlBadgeEl) {
        mlBadgeEl.textContent = data.ml_risk_level;
        mlBadgeEl.className = `pillar-badge ${data.ml_risk_level.toLowerCase()}`;
      }

      const baseScore = data.custom_baseline ? data.custom_baseline.score : data.baseline_score;
      const baseLevel = data.custom_baseline ? data.custom_baseline.level : data.baseline_risk_level;

      if (baseScoreEl) baseScoreEl.textContent = `${baseScore}%`;
      if (baseBadgeEl) {
        baseBadgeEl.textContent = baseLevel;
        baseBadgeEl.className = `pillar-badge ${baseLevel.toLowerCase()}`;
      }

      if (hybridScoreEl) hybridScoreEl.textContent = `${data.hybrid_score}% (${data.hybrid_risk_level})`;
    } catch (e) {
      console.warn("Error recalculating risk:", e);
    }
  }

  function renderRiskTrend(trendPoints) {
    const trendContainer = document.getElementById("risk-trend-chart");
    if (!trendContainer) return;

    if (!trendPoints || trendPoints.length === 0) {
      trendPoints = [
        { label: "T-30m", score: 32, level: "LOW" },
        { label: "T-15m", score: 51, level: "MODERATE" },
        { label: "T-5m", score: 69, level: "HIGH" },
        { label: "Current", score: 87, level: "CRITICAL" }
      ];
    }

    let barsHtml = "";
    trendPoints.forEach((pt) => {
      const color = pt.level === "CRITICAL" ? "var(--neon-crimson)" : (pt.level === "HIGH" ? "var(--neon-orange)" : (pt.level === "MODERATE" ? "var(--neon-amber)" : "var(--neon-emerald)"));
      barsHtml += `
        <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px;">
          <span style="font-size: 11px; font-weight: 700; color: ${color}; font-family: var(--font-display);">${pt.score}%</span>
          <div style="width: 100%; height: 80px; background: rgba(255,255,255,0.05); border-radius: 4px; display: flex; align-items: flex-end; padding: 2px;">
            <div style="width: 100%; height: ${pt.score}%; background: ${color}; border-radius: 3px; box-shadow: 0 0 10px ${color}; transition: height 0.4s ease;"></div>
          </div>
          <span style="font-size: 10px; color: var(--text-muted); font-family: var(--font-tech);">${pt.label}</span>
          <span style="font-size: 9px; color: ${color}; font-weight: bold;">${pt.level}</span>
        </div>
      `;
    });

    trendContainer.innerHTML = barsHtml;
  }

  return {
    init: loadMetrics,
    recalculateCustomRisk,
    renderRiskTrend
  };
})();
