export function initNetworkCanvas(selector) {
  const canvas = document.querySelector(selector);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let particles = [];
  let animFrame;

  const COLORS = {
    line: [
      [0, 212, 255],   /* cyan */
      [139, 92, 246],  /* violet */
      [236, 72, 153],  /* pink */
    ],
  };

  function pickColor(a, b) {
    const idx = Math.floor((a.colorIdx + b.colorIdx) / 2) % COLORS.line.length;
    return COLORS.line[idx];
  }

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);

    const count = Math.max(32, Math.floor(rect.width / 24));
    particles = Array.from({ length: count }, (_, i) => ({
      x: Math.random() * rect.width,
      y: Math.random() * rect.height,
      vx: (Math.random() - 0.5) * 0.38,
      vy: (Math.random() - 0.5) * 0.38,
      r: 1.2 + Math.random() * 2.0,
      colorIdx: i % COLORS.line.length,
      opacity: 0.4 + Math.random() * 0.6,
    }));
  }

  function drawNetwork() {
    const rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);

    particles.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > rect.width) p.vx *= -1;
      if (p.y < 0 || p.y > rect.height) p.vy *= -1;
    });

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i];
        const b = particles[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const maxDist = 110;

        if (dist < maxDist) {
          const alpha = 0.18 * (1 - dist / maxDist);
          const [r, g, bl] = pickColor(a, b);
          ctx.strokeStyle = `rgba(${r},${g},${bl},${alpha})`;
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    particles.forEach((p) => {
      const [r, g, b] = COLORS.line[p.colorIdx];
      ctx.fillStyle = `rgba(${r},${g},${b},${p.opacity})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    });

    animFrame = requestAnimationFrame(drawNetwork);
  }

  const observer = new ResizeObserver(resizeCanvas);
  observer.observe(canvas.parentElement || document.body);
  resizeCanvas();
  drawNetwork();

  return () => {
    cancelAnimationFrame(animFrame);
    observer.disconnect();
  };
}
