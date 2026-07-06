export function initRouter() {
  const pages = [...document.querySelectorAll('.page')];
  const navItems = [...document.querySelectorAll('.nav-item')];
  const pageTitle = document.querySelector('#page-title');

  function showPage(pageId) {
    pages.forEach((page) => {
      page.classList.remove('active');
    });
    navItems.forEach((item) => item.classList.remove('active'));

    const active = document.getElementById(pageId);
    if (active) {
      active.classList.add('active');
      pageTitle.textContent = active.dataset.title || 'AI Decision Copilot';
    }

    navItems.forEach((item) => {
      if (item.dataset.page === pageId) item.classList.add('active');
    });

    window.location.hash = pageId;

    /* close mobile sidebar on navigate */
    document.getElementById('sidebar')?.classList.remove('open');
  }

  navItems.forEach((item) => {
    item.addEventListener('click', () => showPage(item.dataset.page));
  });

  document.querySelectorAll('[data-page-link]').forEach((el) => {
    el.addEventListener('click', () => showPage(el.dataset.pageLink));
  });

  const hash = window.location.hash.replace('#', '');
  const initial = document.getElementById(hash) ? hash : 'dashboard';
  showPage(initial);
}
