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

  makeStars();
  makeMeteors();
  initParallax();
})();
