/* ─── Chart.js global defaults ─── */
Chart.defaults.color = '#8BA3C0';
Chart.defaults.borderColor = 'rgba(255,255,255,0.07)';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 12;

const CYAN = '#00D4FF';
const VIOLET = '#8B5CF6';
const PINK = '#EC4899';
const GREEN = '#10B981';
const AMBER = '#F59E0B';

function rgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

/* ─── Revenue Line Chart ─── */
export function initRevenueChart() {
  const ctx = document.getElementById('revenue-chart');
  if (!ctx) return null;

  const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  const data = [62400, 74800, 68200, 91500, 83700, 98000];

  const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 220);
  gradient.addColorStop(0, rgba(CYAN, 0.28));
  gradient.addColorStop(1, rgba(CYAN, 0.01));

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Revenue ($)',
        data,
        borderColor: CYAN,
        borderWidth: 2.5,
        pointBackgroundColor: CYAN,
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: true,
        backgroundColor: gradient,
        tension: 0.42,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(8,14,28,0.95)',
          borderColor: 'rgba(0,212,255,0.25)',
          borderWidth: 1,
          padding: 12,
          titleFont: { weight: '700', size: 12 },
          bodyFont: { size: 13 },
          callbacks: {
            label: (ctx) => ` $${(ctx.raw / 1000).toFixed(1)}K`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { font: { size: 11 } },
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: {
            font: { size: 11 },
            callback: (v) => '$' + (v / 1000).toFixed(0) + 'K',
          },
        },
      },
    },
  });
}

/* ─── Category Doughnut Chart ─── */
export function initCategoryChart() {
  const ctx = document.getElementById('category-chart');
  if (!ctx) return null;

  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Electronics', 'Home & Living', 'Apparel', 'Other'],
      datasets: [{
        data: [34, 27, 22, 17],
        backgroundColor: [CYAN, VIOLET, PINK, AMBER],
        borderColor: 'rgba(8,14,28,0.9)',
        borderWidth: 3,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '68%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(8,14,28,0.95)',
          borderColor: 'rgba(0,212,255,0.25)',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${ctx.raw}%`,
          },
        },
      },
    },
  });
}

/* ─── Insight Charts ─── */
const insightDatasets = {
  sales: {
    type: 'bar',
    labels: ['Electronics', 'Home', 'Apparel', 'Sports', 'Books'],
    data: [142000, 98000, 84000, 67000, 37600],
    color: CYAN,
  },
  inventory: {
    type: 'bar',
    labels: ['P-001', 'P-012', 'P-034', 'P-067', 'P-089'],
    data: [0, 3, 12, 28, 41],
    color: AMBER,
  },
  marketing: {
    type: 'bar',
    labels: ['Search', 'Social', 'Email', 'Display', 'Referral'],
    data: [2.8, 1.4, 4.2, 0.9, 3.1],
    color: VIOLET,
  },
  support: {
    type: 'bar',
    labels: ['Delivery', 'Refund', 'Product', 'Account', 'Other'],
    data: [412, 287, 198, 134, 169],
    color: PINK,
  },
};

let insightChartInstance = null;

export function initInsightChart(tab = 'sales') {
  const ctx = document.getElementById('insight-chart');
  if (!ctx) return;

  if (insightChartInstance) {
    insightChartInstance.destroy();
    insightChartInstance = null;
  }

  const cfg = insightDatasets[tab] || insightDatasets.sales;

  const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 220);
  gradient.addColorStop(0, rgba(cfg.color, 0.55));
  gradient.addColorStop(1, rgba(cfg.color, 0.10));

  insightChartInstance = new Chart(ctx, {
    type: cfg.type,
    data: {
      labels: cfg.labels,
      datasets: [{
        data: cfg.data,
        backgroundColor: gradient,
        borderColor: cfg.color,
        borderWidth: 2,
        borderRadius: 6,
        borderSkipped: false,
        hoverBackgroundColor: cfg.color,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(8,14,28,0.95)',
          borderColor: rgba(cfg.color, 0.3),
          borderWidth: 1,
          padding: 12,
        },
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 11 } } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 11 } } },
      },
    },
  });
}
