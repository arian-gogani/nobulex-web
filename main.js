/* Nobulex - main.js */

(function () {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* --- Hero video --- */
  const heroVideo = document.querySelector('.hero__video');
  if (heroVideo && !prefersReducedMotion) {
    heroVideo.play().catch(() => {});
    document.addEventListener('click', () => heroVideo.play().catch(() => {}), { once: true });
  }

  /* --- Section rail (active chapter on long landing) --- */
  const rail = document.querySelector('.section-rail');
  if (rail) {
    const links = rail.querySelectorAll('.section-rail__link');
    const sections = [...links]
      .map((a) => document.getElementById((a.getAttribute('href') || '').replace('#', '')))
      .filter(Boolean);
    if (sections.length) {
      const observer = new IntersectionObserver(
        (entries) => {
          const intersecting = entries
            .filter((e) => e.isIntersecting)
            .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
          const hit = intersecting[0];
          if (!hit) return;
          const id = hit.target.id;
          links.forEach((a) => {
            const active = a.getAttribute('href') === `#${id}`;
            a.classList.toggle('is-active', active);
            if (active) a.setAttribute('aria-current', 'true');
            else a.removeAttribute('aria-current');
          });
        },
        { rootMargin: '-42% 0px -42% 0px', threshold: [0, 0.08, 0.2] }
      );
      sections.forEach((s) => observer.observe(s));
    }
  }

  /* --- Hamburger menu --- */
  const navToggle = document.querySelector('.nav-toggle');
  const navClose = document.querySelector('.nav-close');
  const headerNav = document.querySelector('.header__nav');
  const navOverlay = document.getElementById('nav-overlay');
  function closeNav() {
    if (navToggle) navToggle.setAttribute('aria-expanded', 'false');
    if (headerNav) headerNav.classList.remove('is-open');
    if (navOverlay) navOverlay.classList.remove('is-visible');
    document.body.style.overflow = '';
  }
  if (navToggle && headerNav) {
    navToggle.addEventListener('click', () => {
      const expanded = navToggle.getAttribute('aria-expanded') === 'true';
      navToggle.setAttribute('aria-expanded', !expanded);
      headerNav.classList.toggle('is-open');
      if (navOverlay) navOverlay.classList.toggle('is-visible', !expanded);
      document.body.style.overflow = expanded ? '' : 'hidden';
    });
    if (navClose) navClose.addEventListener('click', closeNav);
    if (navOverlay) navOverlay.addEventListener('click', closeNav);
    headerNav.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', closeNav);
    });
  }

  /* --- Copy buttons --- */
  function showCopied(btn, label = 'Copied!') {
    const prev = btn.textContent;
    btn.textContent = label;
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = prev;
      btn.classList.remove('copied');
    }, 2000);
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    ta.style.top = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand('copy');
      return Promise.resolve();
    } catch (e) {
      return Promise.reject(e);
    } finally {
      document.body.removeChild(ta);
    }
  }

  document.querySelectorAll('.code-block__copy').forEach((btn) => {
    btn.addEventListener('click', () => {
      const block = btn.closest('.code-block');
      const activePanel = block?.querySelector('.code-block__panel--active');
      const code = (activePanel || block)?.querySelector('pre code');
      const text = (code ? (code.textContent || code.innerText) : '').trim();
      copyToClipboard(text).then(() => showCopied(btn, 'Copied!')).catch(() => showCopied(btn, 'Select & copy'));
    });
  });

  document.querySelectorAll('.npm-copy').forEach((btn) => {
    btn.addEventListener('click', () => {
      const text = (btn.getAttribute('data-copy') || btn.textContent || '').trim();
      if (text) copyToClipboard(text).then(() => showCopied(btn, 'Copied!')).catch(() => showCopied(btn, 'Select & copy'));
    });
  });

  /* --- Scroll progress bar (hidden on small viewports via CSS) --- */
  const scrollBar = document.querySelector('.scroll-bar');
  if (scrollBar) {
    const scrollBarMq = window.matchMedia('(min-width: 769px)');
    function updateScrollBar() {
      if (!scrollBarMq.matches) return;
      const h = document.documentElement.scrollHeight - window.innerHeight;
      const pct = h > 0 ? window.scrollY / h : 0;
      scrollBar.style.transform = `scaleX(${pct})`;
    }
    scrollBarMq.addEventListener('change', updateScrollBar);
    window.addEventListener('scroll', updateScrollBar, { passive: true });
    updateScrollBar();
  }

  /* --- Scroll reveal --- */
  if (!prefersReducedMotion) {
    const reveal = document.querySelectorAll('[data-reveal]');
    function markVisible(el) {
      el.classList.add('visible');
      io.unobserve(el);
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (!e.isIntersecting) return;
          markVisible(e.target);
        });
      },
      { threshold: 0.12, rootMargin: '0px' }
    );
    reveal.forEach((el) => io.observe(el));
    requestAnimationFrame(() => {
      reveal.forEach((el) => {
        if (el.classList.contains('visible')) return;
        const r = el.getBoundingClientRect();
        const vh = window.innerHeight;
        if (r.top < vh && r.bottom > 0) markVisible(el);
      });
    });
  }

  /* --- Header depth on scroll --- */
  const headerEl = document.querySelector('.header');
  if (headerEl && !prefersReducedMotion) {
    let ticking = false;
    function updateHeader() {
      ticking = false;
      headerEl.classList.toggle('header--scrolled', window.scrollY > 32);
    }
    function onScrollHeader() {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(updateHeader);
      }
    }
    window.addEventListener('scroll', onScrollHeader, { passive: true });
    updateHeader();
  } else if (headerEl) {
    headerEl.classList.toggle('header--scrolled', window.scrollY > 32);
  }

  /* --- Hero word split animation --- */
  if (!prefersReducedMotion) {
    document.querySelectorAll('[data-split="words"]').forEach((line) => {
      const text = line.textContent;
      const words = text.split(/\s+/).filter(Boolean);
      line.innerHTML = words
        .map((w) => `<span class="word"><span class="word-inner">${w}</span></span>`)
        .join(' ');
    });
  }

})();
