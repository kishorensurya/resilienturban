/**
 * ResilientUrban - 18-Step Dynamic Flood Simulation Controller
 * Orchestrates the full hackathon MVP demo scenario with automated playback,
 * manual step-by-step triggers, visual timelines, and map synchronization.
 */

window.SimulationController = (function () {
  let isRunning = false;
  let timerId = null;
  let currentStep = 0;
  const TOTAL_STEPS = 18;
  const STEP_DELAY_MS = 2800; // 2.8 seconds between steps during auto-run

  const STEP_TITLES = [
    "Baseline Normal State",
    "Step 1: Heavy Rainfall Begins",
    "Step 2: Rainfall Intensity Increases",
    "Step 3: Water Level Rises Rapidly",
    "Step 4: Drainage Stress Spikes to 71%",
    "Step 5: Flood Risk Transitions (32 -> 51 -> 69 -> 87)",
    "Step 6: Ward 12 / Zone B Becomes CRITICAL",
    "Step 7: Main Road Flooded & Blocked (75 cm)",
    "Step 8: Map Visualizer Marks Main Road Unsafe",
    "Step 9: Lower-Risk Alternative Route Calculated",
    "Step 10: Flood Consequence: Citizen Seriously Injured",
    "Step 11: Emergency Help Request #1027 Created",
    "Step 12: Medical Unit A-07 Matched (Score 94%)",
    "Step 13: Lower-Risk Response Route Locked",
    "Step 14: Dispatch Simulation Starts",
    "Step 15: Unit A-07 Status: EN ROUTE",
    "Step 16: Municipality Dashboard Synchronized",
    "Step 17: Unit A-07 ARRIVED On-Scene",
    "Step 18: Emergency Incident Fully RESOLVED"
  ];

  function init() {
    updateUI(0, "System ready in baseline conditions. Click 'RUN FULL FLOOD DEMO' to start.");
    checkStatus();
  }

  async function checkStatus() {
    try {
      const res = await fetch("/api/simulation/status");
      const data = await res.json();
      currentStep = data.current_step || 0;
      updateUI(currentStep, currentStep > 0 ? STEP_TITLES[currentStep] : "System ready.");
    } catch (e) {
      console.warn("Simulation status check error:", e);
    }
  }

  async function executeStep(stepNum) {
    try {
      const res = await fetch("/api/simulation/step", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step: stepNum })
      });
      const data = await res.json();
      currentStep = data.step;
      const meta = data.meta || {};

      updateUI(currentStep, meta.desc || STEP_TITLES[currentStep]);

      // Sound feedback (subtle synthesis beep)
      playAudioCue(currentStep);

      // Trigger global state refresh across dashboards & maps
      if (window.App && window.App.refreshData) {
        await window.App.refreshData();
      }

      // Special action hooks for specific steps
      if (currentStep === 7 || currentStep === 8) {
        if (window.ResilientMap) {
          window.ResilientMap.focusOnLocation(12.9352, 77.6245, 16);
        }
      } else if (currentStep === 9 || currentStep === 13) {
        // Fetch and show alternative route
        try {
          const routeRes = await fetch("/api/route");
          const routeData = await routeRes.json();
          if (window.ResilientMap) {
            window.ResilientMap.highlightAlternativeRoute(routeData);
          }
        } catch (re) {
          console.error("Route fetch error:", re);
        }
      } else if (currentStep === 10 || currentStep === 11) {
        // Switch view or alert on SOS
        showSimulationNotification("🚨 CRITICAL SOS #1027", "Serious Injury reported at Ward 12 flood basin!");
      } else if (currentStep === 12) {
        showSimulationNotification("🚑 RESOURCE MATCHED", "Medical Response Unit A-07 matched with 94.2% score.");
      } else if (currentStep === 18) {
        showSimulationNotification("✅ INCIDENT RESOLVED", "Medical extraction completed. Ward 12 stable.");
        stopAutoRun();
      }

      return data;
    } catch (e) {
      console.error("Execute step failed:", e);
      stopAutoRun();
    }
  }

  function startAutoRun() {
    if (isRunning) {
      stopAutoRun();
      return;
    }

    if (currentStep >= TOTAL_STEPS) {
      resetSimulation().then(() => {
        startAutoRun();
      });
      return;
    }

    isRunning = true;
    const btn = document.getElementById("btn-run-demo");
    if (btn) {
      btn.innerHTML = `<span>⏸️</span> PAUSE SIMULATION`;
      btn.classList.add("running");
    }

    // Step immediately or wait interval
    nextStep();

    timerId = setInterval(() => {
      if (!isRunning) return;
      if (currentStep >= TOTAL_STEPS) {
        stopAutoRun();
        return;
      }
      nextStep();
    }, STEP_DELAY_MS);
  }

  function stopAutoRun() {
    isRunning = false;
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
    const btn = document.getElementById("btn-run-demo");
    if (btn) {
      btn.innerHTML = `<span>⚡</span> RUN FULL FLOOD DEMO`;
      btn.classList.remove("running");
    }
  }

  async function nextStep() {
    if (currentStep < TOTAL_STEPS) {
      await executeStep(currentStep + 1);
    }
  }

  async function prevStep() {
    if (currentStep > 1) {
      await executeStep(currentStep - 1);
    } else {
      await resetSimulation();
    }
  }

  async function resetSimulation() {
    stopAutoRun();
    try {
      const res = await fetch("/api/simulation/reset", { method: "POST" });
      currentStep = 0;
      updateUI(0, "Simulation reset to baseline. Rainfall: 25 mm/h, Water: 20 cm, Main Road Clear.");
      if (window.App && window.App.refreshData) {
        await window.App.refreshData();
      }
    } catch (e) {
      console.error("Reset failed:", e);
    }
  }

  function updateUI(step, narrative) {
    const percent = Math.round((step / TOTAL_STEPS) * 100);

    const fillEl = document.getElementById("demo-timeline-fill");
    if (fillEl) fillEl.style.width = `${percent}%`;

    const labelEl = document.getElementById("demo-step-label");
    if (labelEl) {
      labelEl.textContent = step === 0 ? "BASELINE READY (0/18)" : `DEMO STEP ${step} / 18`;
    }

    const narrativeEl = document.getElementById("demo-step-narrative");
    if (narrativeEl) {
      narrativeEl.textContent = narrative || STEP_TITLES[step] || "";
    }

    // Update rain intensity on canvas based on step
    if (window.setRainIntensity) {
      if (step === 0) window.setRainIntensity(0.8);
      else if (step < 3) window.setRainIntensity(1.4);
      else if (step < 7) window.setRainIntensity(2.2);
      else window.setRainIntensity(2.8);
    }
  }

  function playAudioCue(step) {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();

      osc.type = step >= 7 && step <= 14 ? "sawtooth" : "sine";
      osc.frequency.setValueAtTime(step >= 7 ? 660 : 440, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.04, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.18);

      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.18);
    } catch (e) {
      // AudioContext policy suppression gracefully handled
    }
  }

  function showSimulationNotification(title, msg) {
    const banner = document.getElementById("alert-banner-text");
    if (banner) {
      banner.innerHTML = `<strong>${title}:</strong> ${msg}`;
    }
  }

  return {
    init,
    startAutoRun,
    stopAutoRun,
    nextStep,
    prevStep,
    resetSimulation,
    executeStep,
    getCurrentStep: () => currentStep
  };
})();
