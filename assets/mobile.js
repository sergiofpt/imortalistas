(function () {
  var narrow = window.matchMedia('(max-width: 640px)').matches;
  var frame = document.querySelector('iframe.app');
  if (frame && frame.getAttribute('data-src') && !frame.getAttribute('src')) {
    var loadFrame = function () { frame.src = frame.getAttribute('data-src'); };
    if (narrow && 'IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        if (entries.some(function (e) { return e.isIntersecting; })) {
          loadFrame();
          io.disconnect();
        }
      }, { rootMargin: '160px' });
      io.observe(frame);
    } else {
      loadFrame();
    }
  }
  if (!narrow) return;
  var en = (document.documentElement.lang || '').toLowerCase().indexOf('en') === 0;
  function wrap(el) {
    if (!el || el.closest('details.mfilt')) return;
    var d = document.createElement('details');
    d.className = 'mfilt';
    var s = document.createElement('summary');
    s.textContent = en ? 'Filters' : 'Filtros';
    s.setAttribute('data-pt', 'Filtros');
    s.setAttribute('data-en', 'Filters');
    d.appendChild(s);
    el.parentNode.insertBefore(d, el);
    d.appendChild(el);
  }
  document.querySelectorAll('.filters').forEach(function (el) {
    if (!el.querySelector('select')) return;
    var search = el.querySelector('input[type="search"]');
    var count = el.querySelector('.count, .mut.small');
    if (search) {
      search.classList.add('msearch');
      el.parentNode.insertBefore(search, el);
    }
    if (count && count.parentNode === el) el.parentNode.insertBefore(count, el);
    if (el.querySelector('select, input[type="checkbox"]')) wrap(el);
  });
  document.querySelectorAll('.ctrl, .az').forEach(wrap);
  document.querySelectorAll('.pill-nav').forEach(function (el) {
    if (el.offsetHeight > 100) wrap(el);
  });
  document.querySelectorAll('table').forEach(function (t) {
    if (t.closest('.tw, .mtable, .chartwrap')) return;
    var parent = t.parentElement;
    if (!parent) return;
    if (t.scrollWidth > parent.clientWidth + 1) {
      var w = document.createElement('div');
      w.className = 'mtable';
      parent.insertBefore(w, t);
      w.appendChild(t);
    }
  });
})();
