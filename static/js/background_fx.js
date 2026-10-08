/**
 * ResilientUrban - 3D Digital Rain & Hydrological Depth Particles
 * Interactive Canvas Background simulating stormwater dynamics with 3D perspective.
 */

(function () {
  const canvas = document.getElementById("canvas-fx");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  window.addEventListener("resize", () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  // 3D Particles simulating rain & flood depth layers
  const PARTICLE_COUNT = 140;
  const particles = [];

  class DepthParticle {
    constructor() {
      this.reset();
    }

    reset() {
      // 3D coordinate space (-width/2 to width/2, etc.)
      this.x = (Math.random() - 0.5) * width * 1.5;
      this.y = -Math.random() * height;
      this.z = Math.random() * 1000 + 100; // Depth coordinate
      this.speed = Math.random() * 6 + 4;
      this.length = Math.random() * 18 + 12;
      this.alpha = Math.random() * 0.4 + 0.1;
      this.color = Math.random() > 0.85 ? "#00e5ff" : "#1e88e5";
    }

    update(rainIntensityMultiplier = 1.0) {
      this.y += this.speed * (1000 / this.z) * rainIntensityMultiplier;
      // Slight wind drift
      this.x += 0.8 * (1000 / this.z);

      if (this.y > height * 1.2) {
        this.reset();
        this.y = -50;
      }
    }

    draw() {
      // 3D perspective projection
      const fov = 450;
      const scale = fov / (fov + this.z);
      const projX = width / 2 + this.x * scale;
      const projY = height / 2 + this.y * scale;

      if (projX < 0 || projX > width || projY < 0 || projY > height) return;

      const projectedLength = this.length * scale * 2;

      ctx.beginPath();
      ctx.moveTo(projX, projY);
      ctx.lineTo(projX - 1.2 * scale, projY + projectedLength);
      ctx.strokeStyle = this.color;
      ctx.globalAlpha = this.alpha * scale * 1.8;
      ctx.lineWidth = Math.max(1, 1.8 * scale);
      ctx.stroke();
    }
  }

  // Floating ambient neon nodes
  const nodes = [];
  for (let i = 0; i < 24; i++) {
    nodes.push({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      radius: Math.random() * 2 + 1,
      color: Math.random() > 0.7 ? "rgba(0, 229, 255, 0.4)" : "rgba(41, 121, 255, 0.25)"
    });
  }

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new DepthParticle());
  }

  let stormMultiplier = 1.0;

  window.setRainIntensity = function (intensity) {
    stormMultiplier = Math.max(0.6, Math.min(3.0, intensity));
  };

  function animate() {
    ctx.clearRect(0, 0, width, height);

    // Subtle dark cyber gradient overlay
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, "rgba(8, 13, 26, 0.4)");
    grad.addColorStop(1, "rgba(5, 8, 18, 0.7)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);

    // Draw ambient mesh nodes & interconnecting lines
    ctx.lineWidth = 0.5;
    for (let i = 0; i < nodes.length; i++) {
      const n1 = nodes[i];
      n1.x += n1.vx;
      n1.y += n1.vy;
      if (n1.x < 0 || n1.x > width) n1.vx *= -1;
      if (n1.y < 0 || n1.y > height) n1.vy *= -1;

      ctx.beginPath();
      ctx.arc(n1.x, n1.y, n1.radius, 0, Math.PI * 2);
      ctx.fillStyle = n1.color;
      ctx.fill();

      for (let j = i + 1; j < nodes.length; j++) {
        const n2 = nodes[j];
        const dx = n1.x - n2.x;
        const dy = n1.y - n2.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 140) {
          ctx.beginPath();
          ctx.moveTo(n1.x, n1.y);
          ctx.lineTo(n2.x, n2.y);
          ctx.strokeStyle = `rgba(0, 229, 255, ${0.12 * (1 - dist / 140)})`;
          ctx.stroke();
        }
      }
    }

    // Draw 3D Rain particles
    for (let i = 0; i < particles.length; i++) {
      particles[i].update(stormMultiplier);
      particles[i].draw();
    }

    requestAnimationFrame(animate);
  }

  animate();
})();
