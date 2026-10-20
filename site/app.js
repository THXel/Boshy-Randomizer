(() => {
  'use strict';
  document.documentElement.classList.add('enhanced');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const hero = document.querySelector('.hero-video');
  const toggle = document.querySelector('.media-toggle');
  const play = video => { const attempt = video.play(); if (attempt) attempt.catch(() => {}); };
  const updateToggle = () => {
    toggle.textContent = hero.paused ? toggle.dataset.play : toggle.dataset.pause;
    toggle.setAttribute('aria-label', toggle.textContent);
  };
  hero.addEventListener('play', updateToggle);
  hero.addEventListener('pause', updateToggle);
  toggle.addEventListener('click', () => hero.paused ? play(hero) : hero.pause());
  if (!reducedMotion.matches) play(hero);
  updateToggle();

  const dialog = document.querySelector('.gallery-dialog');
  const links = [...document.querySelectorAll('[data-gallery-index]')];
  const fullImage = dialog.querySelector('img');
  const fullVideo = dialog.querySelector('video');
  const caption = dialog.querySelector('#gallery-caption');
  let index = 0;
  let opener = null;
  function showMedia(next) {
    index = (next + links.length) % links.length;
    const link = links[index];
    fullVideo.pause();
    fullVideo.removeAttribute('src');
    fullVideo.replaceChildren();
    fullVideo.load();
    fullImage.hidden = Boolean(link.dataset.video);
    fullVideo.hidden = !link.dataset.video;
    caption.textContent = link.dataset.caption;
    dialog.querySelector('#gallery-count').textContent = `${index + 1} / ${links.length}`;
    if (link.dataset.video) {
      fullVideo.muted = link.dataset.audio !== 'true';
      fullVideo.poster = link.dataset.poster;
      for (const [src, type] of [[link.dataset.webm, 'video/webm'], [link.dataset.video, 'video/mp4']]) {
        if (!src) continue;
        const source = document.createElement('source');
        source.src = src; source.type = type; fullVideo.append(source);
      }
      fullVideo.load();
      if (!reducedMotion.matches) play(fullVideo);
    } else {
      fullImage.src = link.href;
      fullImage.alt = link.dataset.caption;
    }
  }
  links.forEach((link, next) => link.addEventListener('click', event => {
    if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || !dialog.showModal) return;
    event.preventDefault();
    opener = link;
    hero.pause();
    dialog.showModal();
    document.documentElement.classList.add('gallery-open');
    showMedia(next);
    dialog.querySelector('[data-gallery-close]').focus();
  }));
  dialog.querySelector('[data-gallery-close]').addEventListener('click', () => dialog.close());
  dialog.querySelector('[data-gallery-prev]').addEventListener('click', () => showMedia(index - 1));
  dialog.querySelector('[data-gallery-next]').addEventListener('click', () => showMedia(index + 1));
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
  dialog.addEventListener('keydown', event => {
    if (event.target === fullVideo) return;
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      showMedia(index + (event.key === 'ArrowLeft' ? -1 : 1));
    }
  });
  dialog.addEventListener('close', () => {
    fullVideo.pause();
    fullVideo.removeAttribute('src');
    fullVideo.replaceChildren();
    fullVideo.load();
    document.documentElement.classList.remove('gallery-open');
    if (opener) opener.focus();
  });
  const pauseAll = () => { hero.pause(); fullVideo.pause(); };
  document.addEventListener('visibilitychange', () => { if (document.hidden) pauseAll(); });
  reducedMotion.addEventListener('change', () => { if (reducedMotion.matches) pauseAll(); });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(entries => { if (!entries[0].isIntersecting) hero.pause(); }, {threshold: 0}).observe(hero);
  }
  const copy = document.querySelector('#copy-report');
  const template = document.querySelector('#report-template');
  const status = document.querySelector('#copy-status');
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(template.value);
      status.textContent = copy.dataset.success;
    } catch (_) {
      template.focus();
      template.select();
      status.textContent = copy.dataset.fallback;
    }
  });
})();
