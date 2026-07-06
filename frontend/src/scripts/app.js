import { insightContent } from './data.js';
import { initNetworkCanvas } from './network-canvas.js';
import { initRouter } from './router.js';
import { initRevenueChart, initCategoryChart, initInsightChart } from './charts.js';

/* ═══════════════════════════════════════════════════════════════
   TOAST SYSTEM
   ═══════════════════════════════════════════════════════════════ */
const toastIcons = {
  success: 'check-circle',
  error: 'x-circle',
  info: 'info',
  warning: 'alert-triangle',
};

export function toast(type, message, duration = 3800) {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `
    <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      ${getIconPath(toastIcons[type] || 'info')}
    </svg>
    <span>${message}</span>
  `;
  container.appendChild(el);

  const removeToast = () => {
    el.classList.add('out');
    el.addEventListener('animationend', () => el.remove(), { once: true });
  };

  setTimeout(removeToast, duration);
  el.addEventListener('click', removeToast);
}

function getIconPath(name) {
  const paths = {
    'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    'x-circle': '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
    'info': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
    'alert-triangle': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  };
  return paths[name] || paths['info'];
}

/* ═══════════════════════════════════════════════════════════════
   COUNT-UP ANIMATION
   ═══════════════════════════════════════════════════════════════ */
function animateCount(el) {
  const target = parseFloat(el.dataset.count);
  const prefix = el.dataset.prefix || '';
  const suffix = el.dataset.suffix || '';
  const duration = 1200;
  const start = performance.now();

  const inner = el.querySelector('small');
  const innerHTML = inner ? inner.outerHTML : '';

  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const value = Math.floor(ease * target);
    const formatted = value >= 1000
      ? (value / 1000).toFixed(value % 1000 === 0 ? 0 : 1)
      : value.toString();
    el.textContent = `${prefix}${formatted}${suffix}`;
    if (inner) el.insertAdjacentHTML('beforeend', innerHTML);
    if (progress < 1) requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
}

/* ═══════════════════════════════════════════════════════════════
   LOGIN
   ═══════════════════════════════════════════════════════════════ */
function initLogin() {
  const screen = document.getElementById('login-screen');
  const app = document.getElementById('app');
  const form = document.getElementById('login-form');
  const btn = document.getElementById('login-submit');
  const togglePwd = document.getElementById('toggle-password');
  const pwdInput = document.getElementById('login-password');

  initNetworkCanvas('#login-canvas');

  togglePwd?.addEventListener('click', () => {
    const isText = pwdInput.type === 'text';
    pwdInput.type = isText ? 'password' : 'text';
  });

  form?.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const role = document.getElementById('login-role').value;

    if (!email) {
      toast('error', 'Please enter your email address.');
      return;
    }

    btn.classList.add('loading');
    btn.querySelector('span').textContent = 'Signing in…';

    setTimeout(() => {
      screen.classList.add('hidden');
      app.removeAttribute('hidden');

      const name = email.split('@')[0];
      const displayName = name.charAt(0).toUpperCase() + name.slice(1) + ' User';
      document.getElementById('user-name').textContent = displayName;
      document.getElementById('user-role-badge').textContent = role.charAt(0).toUpperCase() + role.slice(1);
      document.getElementById('user-avatar').textContent = name.charAt(0).toUpperCase();

      initApp();
      toast('success', `Welcome back, ${displayName}!`);
    }, 900);
  });
}

/* ═══════════════════════════════════════════════════════════════
   MAIN APP INIT
   ═══════════════════════════════════════════════════════════════ */
function initApp() {
  initRouter();
  initNetworkCanvas('#agent-canvas');
  initRevenueChart();
  initCategoryChart();
  initInsightChart('sales');

  document.querySelectorAll('.metric-value[data-count]').forEach((el) => {
    animateCount(el);
  });

  initSidebar();
  initTopbar();
  initUpload();
  initCopilot();
  initInsights();
  initReports();
  initAdmin();

  lucide?.createIcons();
}

/* ─── Sidebar ─── */
function initSidebar() {
  const toggle = document.getElementById('sidebar-toggle');
  const shell = document.querySelector('.app-shell');
  const sidebar = document.getElementById('sidebar');
  const mobileMenu = document.getElementById('mobile-menu');

  toggle?.addEventListener('click', () => {
    shell.classList.toggle('collapsed');
  });

  mobileMenu?.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 900 && !sidebar.contains(e.target) && !mobileMenu?.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });

  document.getElementById('logout-btn')?.addEventListener('click', () => {
    const screen = document.getElementById('login-screen');
    const app = document.getElementById('app');
    screen.classList.remove('hidden');
    app.setAttribute('hidden', '');
    const btn = document.getElementById('login-submit');
    btn.classList.remove('loading');
    btn.querySelector('span').textContent = 'Sign In';
    toast('info', 'You have been signed out.');
  });
}

/* ─── Topbar ─── */
function initTopbar() {
  document.getElementById('theme-toggle')?.addEventListener('click', () => {
    document.body.classList.toggle('focus');
  });
}

/* ─── Upload ─── */
function initUpload() {
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');
  const list = document.getElementById('file-list');

  zone?.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });

  zone?.addEventListener('dragleave', () => zone.classList.remove('drag-over'));

  zone?.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    handleFiles([...e.dataTransfer.files]);
  });

  input?.addEventListener('change', () => {
    handleFiles([...input.files]);
  });

  function handleFiles(files) {
    if (!files.length) return;
    files.forEach((file) => {
      const ext = file.name.split('.').pop().toLowerCase();
      const isXlsx = ext === 'xlsx' || ext === 'xls';
      const quality = Math.floor(75 + Math.random() * 22);
      const rows = Math.floor(100 + Math.random() * 8000);
      const cols = Math.floor(5 + Math.random() * 12);

      const card = document.createElement('article');
      card.className = 'file-card';
      card.innerHTML = `
        <div class="file-icon ${isXlsx ? 'xlsx' : 'csv'}">
          <i data-lucide="file-spreadsheet"></i>
        </div>
        <div class="file-info">
          <strong>${file.name}</strong>
          <span>${rows.toLocaleString()} rows · ${cols} columns · ${(file.size / 1024).toFixed(0)} KB</span>
        </div>
        <div class="file-status">
          <span class="badge-ok"><i data-lucide="check-circle"></i> Ready</span>
          <div class="quality-bar"><div style="width:0%"></div></div>
          <small>Quality ${quality}%</small>
        </div>
      `;
      list.appendChild(card);
      setTimeout(() => {
        card.querySelector('.quality-bar div').style.width = `${quality}%`;
      }, 100);
    });
    lucide?.createIcons();
    toast('success', `${files.length} file${files.length > 1 ? 's' : ''} uploaded successfully.`);
  }

  document.getElementById('profile-all-btn')?.addEventListener('click', () => {
    toast('info', 'Profiling all datasets… This may take a moment.');
    setTimeout(() => toast('success', 'All datasets profiled. Ready for analysis.'), 2200);
  });

  document.getElementById('clear-files-btn')?.addEventListener('click', () => {
    list.innerHTML = '';
    toast('info', 'File list cleared.');
  });
}

/* ─── Copilot ─── */
function initCopilot() {
  const runBtn = document.getElementById('run-analysis');
  const stateEl = document.getElementById('analysis-state');
  const steps = [...document.querySelectorAll('.timeline-item')];
  const resultPanel = document.getElementById('result-panel');
  const chatHistory = document.getElementById('chat-history');
  const statusPill = document.getElementById('copilot-status');
  const answerBody = document.getElementById('answer-body');

  document.querySelectorAll('.suggestion-chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.getElementById('question').value = btn.textContent.trim();
      document.getElementById('question').focus();
    });
  });

  document.getElementById('question')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      runBtn?.click();
    }
  });

  runBtn?.addEventListener('click', () => {
    const q = document.getElementById('question').value.trim();
    if (!q) { toast('warning', 'Please enter a business question first.'); return; }

    const emptyState = chatHistory.querySelector('.chat-empty');
    if (emptyState) emptyState.remove();

    const userMsg = document.createElement('div');
    userMsg.className = 'chat-msg user';
    userMsg.textContent = q;
    chatHistory.appendChild(userMsg);

    const typing = document.createElement('div');
    typing.className = 'chat-typing';
    typing.innerHTML = '<span></span><span></span><span></span>';
    chatHistory.appendChild(typing);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    resultPanel.classList.remove('visible');
    steps.forEach((s) => {
      s.classList.remove('active', 'done');
      s.querySelector('.tl-time').textContent = '';
    });

    stateEl.textContent = 'Running';
    stateEl.className = 'run-badge running';
    statusPill.className = 'status-pill running';
    statusPill.innerHTML = '<span class="status-pulse"></span> Analyzing…';

    document.getElementById('question').value = '';

    const timings = [0.3, 0.6, 1.2, 0.9, 1.1, 2.1, 1.4];
    let cumulative = 0;

    steps.forEach((step, i) => {
      const delay = 600 * (i + 1);
      cumulative += timings[i] || 0.8;
      setTimeout(() => {
        if (i > 0) steps[i - 1].classList.remove('active');
        step.classList.add('active');

        setTimeout(() => {
          step.classList.remove('active');
          step.classList.add('done');
          step.querySelector('.tl-time').textContent = `Done · ${(timings[i] || 0.8).toFixed(1)}s`;
          lucide?.createIcons();

          if (i === steps.length - 1) {
            typing.remove();

            const aiMsg = document.createElement('div');
            aiMsg.className = 'chat-msg ai';
            aiMsg.textContent = 'Analysis complete. Revenue softness is linked to inventory stockouts, lower marketing ROI, and delivery friction. See the full report below.';
            chatHistory.appendChild(aiMsg);
            chatHistory.scrollTop = chatHistory.scrollHeight;

            stateEl.textContent = 'Complete';
            stateEl.className = 'run-badge complete';
            statusPill.className = 'status-pill ready';
            statusPill.innerHTML = '<span class="status-pulse"></span> Ready';
            resultPanel.classList.add('visible');

            animateCauseBars();
            toast('success', 'Agent analysis complete. 3 root causes identified.');
          }
        }, 480);
      }, delay);
    });
  });

  document.getElementById('approve-report-btn')?.addEventListener('click', () => {
    toast('success', 'Report approved and queued for distribution.');
  });
}

function animateCauseBars() {
  document.querySelectorAll('.cause-bar div').forEach((bar) => {
    const target = bar.parentElement.nextElementSibling?.textContent || bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = bar.closest('.cause-item')?.querySelector('.cause-score')?.textContent || bar.style.width; }, 50);
  });
}

/* ─── Insights ─── */
function initInsights() {
  const tabMap = {
    sales: { title: 'Sales Performance', sub: 'Revenue by product category', confidence: 'Confidence 87%' },
    inventory: { title: 'Inventory Exposure', sub: 'Units in stock by SKU', confidence: 'Confidence 91%' },
    marketing: { title: 'Campaign ROI', sub: 'Return on ad spend by channel', confidence: 'Confidence 79%' },
    support: { title: 'Support Volume', sub: 'Ticket count by issue type', confidence: 'Confidence 84%' },
  };

  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((t) => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');

      const key = tab.dataset.tab;
      const cfg = tabMap[key] || tabMap.sales;
      document.getElementById('insight-title').textContent = cfg.title;
      document.getElementById('insight-sub').textContent = cfg.sub;
      document.getElementById('insight-confidence').textContent = cfg.confidence;
      document.getElementById('insight-copy').textContent = insightContent[key]?.copy || '';
      initInsightChart(key);
    });
  });
}

/* ─── Reports ─── */
function initReports() {
  document.getElementById('download-report-btn')?.addEventListener('click', () => {
    toast('info', 'Generating PDF report… Download will start shortly.');
    setTimeout(() => toast('success', 'Revenue_Drop_Analysis_Jun2026.pdf ready to download.'), 1800);
  });

  document.getElementById('approve-send-btn')?.addEventListener('click', () => {
    toast('success', 'Report approved. Email draft created — pending human review.');
  });

  document.getElementById('new-report-btn')?.addEventListener('click', () => {
    document.querySelector('[data-page="copilot"]')?.click();
    toast('info', 'Navigated to Ask Copilot to start a new analysis.');
  });

  document.querySelectorAll('.table-btn').forEach((btn) => {
    btn.addEventListener('click', () => toast('info', 'Preparing report download…'));
  });
}

/* ─── Admin ─── */
function initAdmin() {
  document.querySelectorAll('.toggle').forEach((toggle) => {
    toggle.addEventListener('click', () => {
      toggle.classList.toggle('on');
      const state = toggle.classList.contains('on') ? 'enabled' : 'disabled';
      const label = toggle.closest('.security-item')?.querySelector('strong')?.textContent || 'Control';
      toast(toggle.classList.contains('on') ? 'success' : 'warning', `${label} ${state}.`);
    });
  });
}

/* ─── Range chips on dashboard ─── */
function initRangeChips() {
  document.querySelectorAll('.chip[data-range]').forEach((chip) => {
    chip.addEventListener('click', () => {
      chip.closest('.panel-actions')?.querySelectorAll('.chip').forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
    });
  });
}

/* ═══════════════════════════════════════════════════════════════
   BOOT
   ═══════════════════════════════════════════════════════════════ */
initLogin();

document.addEventListener('DOMContentLoaded', () => {
  initRangeChips();
  lucide?.createIcons();
});
