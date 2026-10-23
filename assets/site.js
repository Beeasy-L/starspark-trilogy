(function () {
  'use strict';

  var starfield = document.getElementById('starfield');
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  function makeStars() {
    if (!starfield) return;

    var layers = Array.prototype.slice.call(
      starfield.querySelectorAll('.starfield__layer')
    );
    if (!layers.length) return;

    var mobile = window.matchMedia('(max-width: 768px)').matches;
    var count = mobile ? 38 : 50;
    var farCount = Math.round(count * 0.54);
    var midCount = Math.round(count * 0.32);
    var fragment = document.createDocumentFragment();
    var glintSlots = new Set([5, 13, 21, 31, 41]);

    for (var i = 0; i < count; i += 1) {
      var star = document.createElement('span');
      var isFar = i < farCount;
      var isMid = !isFar && i < farCount + midCount;
      var layer = isFar ? 0 : isMid ? 1 : 2;
      var size = isFar
        ? 0.9 + Math.random() * 1
        : isMid
          ? 1.4 + Math.random() * 1.1
          : 2 + Math.random() * 1.3;
      var opacity = isFar
        ? 0.38 + Math.random() * 0.28
        : isMid
          ? 0.58 + Math.random() * 0.25
          : 0.82 + Math.random() * 0.18;

      star.className = 'star star--' + (isFar ? 'far' : isMid ? 'mid' : 'near');
      if (glintSlots.has(i)) star.className += ' star--glint';

      star.style.setProperty('--x', (2 + Math.random() * 96).toFixed(2) + '%');
      star.style.setProperty('--y', (2 + Math.random() * 96).toFixed(2) + '%');
      star.style.setProperty('--size', size.toFixed(2) + 'px');
      star.style.setProperty('--star-opacity', opacity.toFixed(2));
      star.style.setProperty('--star-color', isFar ? '#9fb2d8' : '#eef3ff');
      star.style.setProperty('--duration', (4.4 + Math.random() * 5.6).toFixed(2) + 's');
      star.style.setProperty('--delay', (-Math.random() * 9).toFixed(2) + 's');
      fragment.appendChild(star);
    }

    layers.forEach(function (layer) {
      layer.replaceChildren();
    });

    var generatedStars = fragment.querySelectorAll('.star');
    for (var j = 0; j < count; j += 1) {
      var isFarStar = j < farCount;
      var isMidStar = !isFarStar && j < farCount + midCount;
      var targetLayer = isFarStar ? 0 : isMidStar ? 1 : 2;
      if (generatedStars[j]) layers[targetLayer].appendChild(generatedStars[j]);
    }
  }

  function initParallax() {
    if (!starfield || reduceMotion.matches) return;
    if (!window.matchMedia('(pointer: fine)').matches) return;

    var layers = Array.prototype.slice.call(
      starfield.querySelectorAll('.starfield__layer')
    );
    var depths = [10, 22, 40];
    var targetX = 0;
    var targetY = 0;
    var currentX = 0;
    var currentY = 0;
    var frame = 0;

    function render() {
      currentX += (targetX - currentX) * 0.075;
      currentY += (targetY - currentY) * 0.075;

      layers.forEach(function (layer, index) {
        var depth = depths[index] || 8;
        layer.style.transform =
          'translate3d(' +
          (currentX * depth).toFixed(2) +
          'px,' +
          (currentY * depth).toFixed(2) +
          'px,0)';
      });

      if (
        Math.abs(targetX - currentX) > 0.001 ||
        Math.abs(targetY - currentY) > 0.001
      ) {
        frame = window.requestAnimationFrame(render);
      } else {
        frame = 0;
      }
    }

    function start() {
      if (!frame) frame = window.requestAnimationFrame(render);
    }

    window.addEventListener(
      'pointermove',
      function (event) {
        targetX = (event.clientX / Math.max(window.innerWidth, 1) - 0.5) * 2;
        targetY = (event.clientY / Math.max(window.innerHeight, 1) - 0.5) * 2;
        start();
      },
      { passive: true }
    );

    window.addEventListener(
      'blur',
      function () {
        targetX = 0;
        targetY = 0;
        start();
      },
      { passive: true }
    );
  }

  function makeMeteors() {
    if (!starfield || reduceMotion.matches) return;

    var mobile = window.matchMedia('(max-width: 768px)').matches;
    var count = mobile ? 10 : 11;

    starfield.querySelectorAll('.meteor').forEach(function (meteor) {
      meteor.remove();
    });

    for (var i = 0; i < count; i += 1) {
      var meteor = document.createElement('span');
      var length = mobile
        ? 82 + Math.random() * 74
        : 105 + Math.random() * 88;
      var duration = 6.2 + Math.random() * 4.8;

      meteor.className = i % 4 === 3 ? 'meteor meteor--soft' : 'meteor';
      meteor.style.setProperty(
        '--meteor-x',
        (mobile ? 48 : 58) + Math.random() * 57 + '%'
      );
      meteor.style.setProperty(
        '--meteor-y',
        (3 + Math.random() * 48).toFixed(2) + '%'
      );
      meteor.style.setProperty('--meteor-length', length.toFixed(1) + 'px');
      meteor.style.setProperty('--meteor-duration', duration.toFixed(2) + 's');
      meteor.style.setProperty(
        '--meteor-delay',
        (-Math.random() * duration).toFixed(2) + 's'
      );
      meteor.style.setProperty(
        '--meteor-angle',
        (-31 + Math.random() * 10).toFixed(1) + 'deg'
      );
      meteor.style.setProperty(
        '--meteor-move-x',
        (-(length * 3.8 + 170)).toFixed(1) + 'px'
      );
      meteor.style.setProperty(
        '--meteor-move-y',
        (length * 2.1).toFixed(1) + 'px'
      );
      starfield.appendChild(meteor);
    }
  }

  function createBgmToggle(target) {
    var toggle = document.createElement('button');
    toggle.className = 'bgm-toggle';
    toggle.type = 'button';
    toggle.setAttribute('aria-pressed', 'false');
    toggle.setAttribute('aria-label', '播放背景音乐《小星星》');
    toggle.innerHTML =
      '<span class="bgm-toggle__note" aria-hidden="true">♪</span>' +
      '<span class="bgm-toggle__label">音乐已暂停</span>';
    target.appendChild(toggle);
    return toggle;
  }

  var BGM_STORAGE_KEY = 'starfire:bgm:v2';
  var BGM_STATE_MAX_AGE = 6 * 60 * 60 * 1000;

  // 解析 data-bgm-src：可以是单个 URL 字符串，也可以是 JSON 数组 [{src, label}]
  function parsePlaylist(raw) {
    if (!raw) return [];
    var trimmed = raw.trim();
    if (trimmed.charAt(0) === '[') {
      try { return JSON.parse(trimmed); } catch (e) { return []; }
    }
    // 向后兼容：旧格式是逗号分隔的 URL 字符串，取第一个
    var sources = trimmed.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    return sources.map(function (src) {
      var name = src.replace(/^.*[\\/]/, '').replace(/\.[^.]+$/, '');
      if (name === 'xiaoxingxing') name = '小星星';
      else if (name === 'moon') name = '月亮代表我的心';
      return { src: src, label: name };
    });
  }

  function readBgmState() {
    try {
      var raw = window.sessionStorage.getItem(BGM_STORAGE_KEY);
      if (!raw) return null;
      var state = JSON.parse(raw);
      if (!state || typeof state.t !== 'number' || !isFinite(state.t)) return null;
      if (Date.now() - (state.at || 0) > BGM_STATE_MAX_AGE) return null;
      return state;
    } catch (error) {
      return null;
    }
  }

  function writeBgmState(state) {
    try {
      window.sessionStorage.setItem(BGM_STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
      // Private modes can reject storage; playback keeps working without it.
    }
  }

  function initBackgroundMusic() {
    if (window.parent !== window) return null;

    var playlist = parsePlaylist(document.body.getAttribute('data-bgm-src'));
    if (!playlist.length) return null;

    var audio = document.getElementById('site-bgm');
    if (!audio) {
      audio = document.createElement('audio');
      audio.className = 'site-audio';
      audio.id = 'site-bgm';
      audio.preload = 'auto';
      document.body.appendChild(audio);
    }

    var toggle = document.getElementById('bgm-toggle') || createBgmToggle(document.body);
    var toggles = [];
    var stored = readBgmState();
    var userPaused = stored ? !!stored.pausedByUser : false;
    var resumeAt = stored && typeof stored.t === 'number' ? stored.t : 0;
    var trackIndex = (stored && typeof stored.trackIndex === 'number' && stored.trackIndex >= 0 && stored.trackIndex < playlist.length) ? stored.trackIndex : 0;
    var lastSavedAt = -1;
    var nudgeTimer = 0;
    var nudgeUntil = 0;

    function currentTrack() { return playlist[trackIndex]; }

    // 切换到指定曲目并等待 canplay 后 seek
    function loadTrack(index, seekTo) {
      trackIndex = (index + playlist.length) % playlist.length;
      var t = playlist[trackIndex];
      if (audio.src && audio.src.endsWith && audio.src.indexOf(t.src) >= 0) {
        // 已经在同一首，只 seek
        try { if (isFinite(seekTo)) audio.currentTime = seekTo; } catch (e) {}
        return;
      }
      var wasPlaying = !audio.paused;
      audio.src = t.src;
      audio.load();
      if (isFinite(seekTo) && seekTo > 0) {
        var onReady = function () {
          try { audio.currentTime = seekTo; } catch (e) {}
        };
        audio.addEventListener('loadedmetadata', onReady, { once: true });
        if (audio.readyState >= 1) onReady();
      }
      if (wasPlaying && !userPaused) playMusic();
    }

    // 记住播放进度：进入二级页面（或刷新）后从原处接着放，而不是从头开始。
    function applyStoredTime() {
      if (!resumeAt) return;
      loadTrack(trackIndex, resumeAt);
      resumeAt = 0;
    }

    function persistState() {
      writeBgmState({
        t: audio.currentTime || 0,
        trackIndex: trackIndex,
        playing: !audio.paused,
        pausedByUser: userPaused,
        at: Date.now()
      });
    }

    // 页面/浮层切换时浏览器可能强制暂停媒体，这里短暂重试，恢复出声。
    function nudgeResume(duration) {
      nudgeUntil = Date.now() + (duration || 2500);
      if (nudgeTimer) return;
      nudgeTimer = window.setInterval(function () {
        if (userPaused || !audio.paused || Date.now() > nudgeUntil) {
          window.clearInterval(nudgeTimer);
          nudgeTimer = 0;
          return;
        }
        playMusic();
      }, 180);
    }

    function setPlaying(isPlaying) {
      var label = isPlaying ? currentTrack().label : '音乐已暂停';
      toggles.forEach(function (button) {
        var labelEl = button.querySelector('.bgm-toggle__label');
        button.setAttribute('aria-pressed', String(isPlaying));
        button.setAttribute(
          'aria-label',
          isPlaying ? '暂停背景音乐《' + currentTrack().label + '》' : '播放背景音乐《' + currentTrack().label + '》'
        );
        if (labelEl) labelEl.textContent = label;
      });
    }

    function playNextTrack() {
      trackIndex = (trackIndex + 1) % playlist.length;
      loadTrack(trackIndex, 0);
      persistState();
      playMusic();
    }

    function registerToggle(button) {
      if (!button || toggles.indexOf(button) !== -1) return;
      toggles.push(button);
      button.addEventListener('click', toggleMusic);
      setPlaying(!audio.paused);
    }

    function playMusic() {
      if (userPaused) return Promise.resolve(false);

      var attempt = audio.play();
      if (!attempt || typeof attempt.then !== 'function') {
        setPlaying(!audio.paused);
        return Promise.resolve(!audio.paused);
      }

      return attempt.then(
        function () {
          setPlaying(true);
          return true;
        },
        function () {
          setPlaying(false);
          return false;
        }
      );
    }

    function toggleMusic() {
      if (audio.paused) {
        userPaused = false;
        playMusic();
      } else {
        userPaused = true;
        audio.pause();
      }
      persistState();
    }

    function removeUnlockListeners() {
      document.removeEventListener('pointerdown', unlockMusic);
      document.removeEventListener('keydown', unlockMusic);
    }

    function unlockMusic(event) {
      var clickedToggle = toggles.some(function (button) {
        return event && button.contains(event.target);
      });
      if (clickedToggle) return;
      if (userPaused || !audio.paused) {
        removeUnlockListeners();
        return;
      }
      playMusic().then(function (started) {
        if (started) removeUnlockListeners();
      });
    }

    // 初始加载第一首
    loadTrack(trackIndex, 0);
    audio.addEventListener('loadedmetadata', applyStoredTime, { once: true });
    if (audio.readyState >= 1) applyStoredTime();

    // 一曲播完自动切下一首（不再单曲循环）
    audio.addEventListener('ended', function () {
      persistState();
      playNextTrack();
    });

    audio.addEventListener('play', function () {
      setPlaying(true);
      persistState();
    });
    audio.addEventListener('pause', function () {
      setPlaying(false);
      persistState();
      // 浏览器在切换文档/打开浮层时可能强制暂停，非用户操作则尝试续播。
      if (!userPaused) nudgeResume(2600);
    });
    audio.addEventListener('timeupdate', function () {
      if (Math.abs(audio.currentTime - lastSavedAt) < 1) return;
      lastSavedAt = audio.currentTime;
      persistState();
    });
    window.addEventListener('pagehide', persistState);
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') persistState();
    });

    registerToggle(toggle);
    document.addEventListener('pointerdown', unlockMusic, { passive: true });
    document.addEventListener('keydown', unlockMusic);

    if (!userPaused) {
      playMusic();
      if (stored && stored.playing) nudgeResume(2200);
    } else {
      setPlaying(false);
    }

    return {
      addToggle: registerToggle,
      isPlaying: function () {
        return !audio.paused;
      },
      keepPlaying: function () {
        if (!userPaused) nudgeResume(2600);
      },
      switchToTrack: function (index) {
        if (index >= 0 && index < playlist.length && index !== trackIndex) {
          loadTrack(index, 0);
          if (!userPaused) playMusic();
        }
      }
    };
  }

  function initEmbeddedPage() {
    if (window.parent === window) return;

    document
      .querySelectorAll('a.back-btn[href$="index.html"]')
      .forEach(function (link) {
        link.addEventListener('click', function (event) {
          event.preventDefault();
          window.parent.postMessage({ type: 'starfire-detail-close' }, '*');
        });
      });
  }

  function initDetailOverlay(music) {
    if (
      window.parent !== window ||
      !music ||
      document.body.getAttribute('data-page') !== 'home'
    ) {
      return;
    }

    var detailLinks = document.querySelectorAll('.cards a.link.go[href^="projects/"]');
    if (!detailLinks.length) return;

    var overlay = document.createElement('div');
    var toolbar = document.createElement('div');
    var frame = document.createElement('iframe');
    var closeButton = document.createElement('button');
    var musicButton = createBgmToggle(toolbar);
    var activeLink = null;

    overlay.className = 'detail-overlay';
    overlay.hidden = true;
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', '项目详情');

    toolbar.className = 'detail-overlay__toolbar';
    closeButton.className = 'detail-overlay__close';
    closeButton.type = 'button';
    closeButton.setAttribute('aria-label', '关闭项目详情');
    closeButton.textContent = '×';
    toolbar.appendChild(closeButton);

    frame.className = 'detail-overlay__frame';

    function hideDetail() {
      if (overlay.hidden) return;
      overlay.hidden = true;
      document.body.classList.remove('detail-open');
      frame.removeAttribute('src');
      if (activeLink) activeLink.focus();
    }

    function closeDetail() {
      if (overlay.hidden) return;
      hideDetail();
      if (window.history.state && window.history.state.starfireDetail) {
        window.history.back();
      }
    }

    function openDetail(link) {
      var cardTitle = link.closest('.card');
      cardTitle = cardTitle && cardTitle.querySelector('h3');
      activeLink = link;
      frame.title = (cardTitle ? cardTitle.textContent : '项目') + '详情';
      frame.src = link.href;
      overlay.hidden = false;
      document.body.classList.add('detail-open');
      closeButton.focus();
      if (music.keepPlaying) music.keepPlaying();

      try {
        window.history.pushState(
          { starfireDetail: true },
          '',
          '#detail/' + link.getAttribute('href').split('/').pop().replace('.html', '')
        );
      } catch (error) {
        // The overlay still works when a browser restricts file URL history.
      }
    }

    detailLinks.forEach(function (link) {
      link.addEventListener('click', function (event) {
        if (
          event.defaultPrevented ||
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        ) {
          return;
        }
        event.preventDefault();
        openDetail(link);
      });
    });

    overlay.appendChild(frame);
    overlay.appendChild(toolbar);
    document.body.appendChild(overlay);
    music.addToggle(musicButton);

    closeButton.addEventListener('click', closeDetail);
    window.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !overlay.hidden) closeDetail();
    });
    window.addEventListener('popstate', function () {
      if (
        !overlay.hidden &&
        !(window.history.state && window.history.state.starfireDetail)
      ) {
        hideDetail();
      }
    });
    window.addEventListener('message', function (event) {
      if (
        event.source === frame.contentWindow &&
        event.data &&
        event.data.type === 'starfire-detail-close'
      ) {
        closeDetail();
      }
    });
  }

  makeStars();
  makeMeteors();
  initParallax();
  initEmbeddedPage();
  var music = initBackgroundMusic();
  initDetailOverlay(music);

  // 滚到「给未来的自己」时切到月亮代表我的心，滚走切回小星星
  (function () {
    if (!music || !music.switchToTrack) return;
    var epilogue = document.querySelector('.epilogue');
    if (!epilogue) return;

    var wasVisible = false;
    var observer = new IntersectionObserver(function (entries) {
      var visible = entries[entries.length - 1].isIntersecting;
      if (visible === wasVisible) return;
      wasVisible = visible;
      music.switchToTrack(visible ? 1 : 0);
    }, { threshold: [0, 0.25] });

    observer.observe(epilogue);
  })();
})();
