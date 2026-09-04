/* Geometry harvester — the export path's measuring instrument.
 *
 * The HTML deck is the single source of truth for how a slide looks. Rather than re-implement
 * that look in a second language (the `.pptx` renderer used to be a 1143-line prose spec
 * restating every rule in EMU units), the exporters *measure the real render*: Chrome lays the
 * deck out, this script walks the laid-out DOM, and `export_pptx.py` rebuilds what it reports as
 * native shapes. No layout rule lives in two places, because there is only one layout engine.
 *
 * Runs only under `?export=…`, and only inside Reveal's print view — there every slide is laid
 * out at the deck's full 1280x720 at once, whereas the normal view keeps all but the current
 * slide at `display:none`, which measures as zero. So it rides `?print-pdf`, and
 * `_PDF_AUTOPRINT` stands down for the same query so the harvest never opens a print dialog.
 *
 * Output is a JSON display list parked in a JSON script block with id `deck-harvest`, which is
 * how it survives `chrome --headless --dump-dom` — no CDP client, no new Python dependency.
 * `data-harvest-ready` on <html> is the completion signal; the exporter checks the attribute
 * rather than guessing a wait time, so a partial harvest fails loudly instead of shipping.
 *
 * TWO THINGS ARE LOAD-BEARING, both learned the hard way:
 *
 * 1. TIMING. `fitAll()` sizes each slide by binary search and publishes the result as
 *    `transform: scale()`; Reveal re-lays the whole deck when it builds the print view and only
 *    then fires `pdf-ready`. This listens for `pdf-ready` too, registered *after* the init
 *    script's own listener so it runs once the re-fit is done. Measuring earlier reports pre-fit
 *    geometry — wrong on exactly the slides that needed fitting most.
 *
 * 2. NO CLOSING SCRIPT TAG MAY APPEAR IN THIS FILE, comments included. An inline script block
 *    ends at the first one in its text, and the browser then reports a syntax error on the
 *    leftover markup while this whole file silently never parses — no error, no harvest, no
 *    clue. `html_style.py` escapes the sequence defensively when it inlines this; do not rely
 *    on that alone.
 */
(function () {
  if (!/[?&]export=/.test(location.search)) return;

  /* ---- colour ------------------------------------------------------------------------- */
  // One 1x1 canvas normalizes every colour syntax the deck can produce — rgb(), rgba(),
  // color(srgb …), color-mix() (theme.css uses it for `.conccol.em`), currentColor — into plain
  // 8-bit RGBA. Without this the emitter would need a CSS colour parser.
  var _cc = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  var _colorCache = {};
  function color(v) {
    if (!v) return null;
    if (_colorCache[v] !== undefined) return _colorCache[v];
    var out = null;
    try {
      _cc.clearRect(0, 0, 1, 1);
      _cc.fillStyle = '#000';
      _cc.fillStyle = v;
      _cc.fillRect(0, 0, 1, 1);
      var d = _cc.getImageData(0, 0, 1, 1).data;
      out = {r: d[0], g: d[1], b: d[2], a: Math.round(d[3] / 255 * 1000) / 1000};
    } catch (e) { out = null; }
    _colorCache[v] = out;
    return out;
  }
  function opaque(c) { return c && c.a > 0.004; }

  /* ---- geometry ---------------------------------------------------------------------- */
  function px(v) { return Math.round((v + Number.EPSILON) * 100) / 100; }

  // `getBoundingClientRect` is post-transform, so rects need no correction. `getComputedStyle`
  // font-size is NOT: a 24px font inside a 0.62 scale paints at 14.9px. Accumulate the ancestor
  // scale so the emitter can multiply. (The reference deck scales down to 0.62 in the wild.)
  function accScale(el) {
    var s = 1, n = el;
    while (n && n.nodeType === 1) {
      var t = getComputedStyle(n).transform;
      if (t && t !== 'none') {
        var m = t.match(/matrix\(([^)]+)\)/);
        if (m) {
          var p = m[1].split(',');
          // Magnitude of the first column, not its `a` term: `.mylab` is rotated 180deg, where
          // `a` is -1 and a signed read would hand the exporter negative type sizes.
          var a = parseFloat(p[0]) || 0, b = parseFloat(p[1]) || 0;
          var f = Math.sqrt(a * a + b * b);
          if (f > 0.001) s *= f;
        }
      }
      n = n.parentElement;
    }
    return s;
  }

  function rect(r, ox, oy) {
    return {x: px(r.x - ox), y: px(r.y - oy), w: px(r.width), h: px(r.height)};
  }
  function intersect(a, b) {
    if (!b) return a;
    var x = Math.max(a.x, b.x), y = Math.max(a.y, b.y);
    var r = Math.min(a.x + a.w, b.x + b.w), d = Math.min(a.y + a.h, b.y + b.h);
    return {x: px(x), y: px(y), w: px(Math.max(0, r - x)), h: px(Math.max(0, d - y))};
  }

  /* ---- text ---------------------------------------------------------------------------- */
  var INLINE = {B:1,I:1,EM:1,STRONG:1,CODE:1,A:1,SPAN:1,BR:1,S:1,DEL:1,STRIKE:1,SUP:1,SUB:1,
                SMALL:1,U:1,MARK:1,ABBR:1,TIME:1,VAR:1,KBD:1,SAMP:1,Q:1,CITE:1,DFN:1,INS:1};

  function inlineOnly(el) {
    for (var i = 0; i < el.children.length; i++) {
      var c = el.children[i];
      if (!INLINE[c.tagName]) return false;
      var ccs = getComputedStyle(c);
      // An inline tag that paints (a `code` chip has a background) is a box in its own right.
      if (opaque(color(ccs.backgroundColor)) || parseFloat(ccs.borderLeftWidth)) return false;
    }
    return true;
  }

  // Chrome does not apply text-transform to textContent, so uppercase labels (.pill, .cblang,
  // .mxlab, .quiz-lab, .steyebrow …) would export in mixed case. Apply it here and emit the
  // RENDERED string — the harvest reports what the eye sees, everywhere.
  function transform(s, tt) {
    if (tt === 'uppercase') return s.toUpperCase();
    if (tt === 'lowercase') return s.toLowerCase();
    if (tt === 'capitalize') return s.replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    return s;
  }

  function marks(cs, inherited) {
    var w = parseInt(cs.fontWeight, 10) || 400;
    var deco = cs.textDecorationLine || cs.textDecoration || '';
    var fam = (cs.fontFamily || '').split(',')[0].replace(/["']/g, '').trim();
    return {
      b: w >= 600, i: cs.fontStyle === 'italic',
      u: deco.indexOf('underline') >= 0,
      s: deco.indexOf('line-through') >= 0,
      fam: fam,
      px: px(parseFloat(cs.fontSize) || 0),
      spc: px(parseFloat(cs.letterSpacing) || 0),
      col: color(cs.color),
      op: parseFloat(cs.opacity),
      tt: cs.textTransform,
      href: (inherited && inherited.href) || null
    };
  }

  /* Flatten an inline-only element into styled runs. This is what keeps a code panel readable:
   * every highlight.js token is a span with its own colour, and a flat textContent would throw
   * all of them away. */
  function runsOf(el, inh, out) {
    for (var i = 0; i < el.childNodes.length; i++) {
      var n = el.childNodes[i];
      if (n.nodeType === 3) {
        if (n.nodeValue) out.push({s: transform(n.nodeValue, inh.tt), m: inh});
        continue;
      }
      if (n.nodeType !== 1) continue;
      if (n.tagName === 'BR') { out.push({s: '\n', m: inh, br: true}); continue; }
      var cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      var m = marks(cs, inh);
      if (n.tagName === 'A' && n.getAttribute('href')) m.href = n.getAttribute('href');
      else m.href = inh.href;
      // Marks are inherited, not reset: <b><i>x</i></b> must keep both.
      m.b = m.b || inh.b; m.i = m.i || inh.i; m.u = m.u || inh.u; m.s = m.s || inh.s;
      runsOf(n, m, out);
    }
    return out;
  }

  // Visual line count, from the real line boxes. A block that renders on ONE line cannot
  // re-break in PowerPoint, so the emitter turns wrapping off for it — which is most of the
  // tightly-fitted type in the deck (titles, pills, stat numbers) and exactly where a re-wrap
  // would do visible damage. Multi-line prose keeps wrapping, and stays natural to edit.
  function lineCount(el) {
    try {
      var rg = document.createRange();
      rg.selectNodeContents(el);
      var rs = rg.getClientRects(), tops = {}, n = 0;
      for (var i = 0; i < rs.length; i++) {
        if (rs[i].width < 0.5 && rs[i].height < 0.5) continue;
        var k = Math.round(rs[i].top);
        if (!tops[k]) { tops[k] = 1; n++; }
      }
      return n || 1;
    } catch (e) { return 1; }
  }

  /* ---- pseudo-elements ------------------------------------------------------------------ */
  /* ::before/::after are load-bearing here: the quiz option letters (A/B/C/D) and its answer
   * tick, the three dot-bullet styles, and the section-divider accent rule. They are invisible
   * to a DOM walk, so they are reconstructed from computed style. Position comes from the box
   * model rather than a selector table, so a new pseudo in theme.css is picked up for free;
   * anything whose geometry can't be derived is reported in the slide's warnings instead of
   * silently vanishing. */
  function pseudo(el, which, ox, oy, clip, out) {
    var cs;
    try { cs = getComputedStyle(el, which); } catch (e) { return; }
    if (!cs) return;
    var content = cs.content;
    if (!content || content === 'none' || content === 'normal') return;
    if (cs.display === 'none' || cs.visibility === 'hidden') return;

    var pr = el.getBoundingClientRect();
    var pcs = getComputedStyle(el);
    var w = parseFloat(cs.width) || 0, h = parseFloat(cs.height) || 0;
    var fs = parseFloat(cs.fontSize) || 0;

    // Resolve the rendered string. Chrome leaves `counter(...)` unresolved in computed style,
    // so derive it from the element's position among its siblings — which is what the counter
    // is counting (theme.css `.quiz-opts li::before` → A, B, C, D).
    var text = '';
    if (/counter\(/.test(content)) {
      var idx = 0, sib = el.parentElement ? el.parentElement.children : [];
      for (var i = 0; i < sib.length; i++) { if (sib[i] === el) break; if (sib[i].tagName === el.tagName) idx++; }
      text = /upper-alpha/.test(content) ? String.fromCharCode(65 + idx)
           : /lower-alpha/.test(content) ? String.fromCharCode(97 + idx)
           : String(idx + 1);
    } else {
      var q = content.match(/^"(.*)"$/) || content.match(/^'(.*)'$/);
      text = q ? q[1] : (content === 'counter' ? '' : '');
    }
    if (!w && text) w = fs * (text.length * 0.62 + 0.2);
    if (!h && text) h = fs * 1.2;
    if (w < 0.5 || h < 0.5) return;

    var x, y, pos = cs.position;
    if (pos === 'absolute' || pos === 'fixed') {
      // Offsets resolve against the padding box (theme.css uses left/top on relative parents).
      x = pr.x + (parseFloat(cs.left) || 0);
      y = pr.y + (parseFloat(cs.top) || 0);
    } else if (cs.display === 'block' || cs.display === 'flow-root') {
      // In-flow block generated after the content: it occupies the bottom of the parent box.
      x = pr.x + (parseFloat(pcs.paddingLeft) || 0) + (parseFloat(cs.marginLeft) || 0);
      y = pr.bottom - (parseFloat(pcs.paddingBottom) || 0) - h - (parseFloat(cs.marginBottom) || 0);
    } else if (which === '::before') {
      x = pr.x + (parseFloat(pcs.paddingLeft) || 0);
      y = pr.y + (pr.height - h) / 2;
    } else {
      // `margin-left:auto` pushes a trailing flex item to the far edge (the quiz tick).
      x = pr.right - (parseFloat(pcs.paddingRight) || 0) - w;
      y = pr.y + (pr.height - h) / 2;
    }

    var rc = intersect({x: px(x - ox), y: px(y - oy), w: px(w), h: px(h)}, clip);
    if (rc.w < 0.5 || rc.h < 0.5) return;

    var bg = color(cs.backgroundColor);
    var radius = radii(cs);
    if (opaque(bg) || radius.some(function (v) { return v > 0; })) {
      out.push({k: 'box', tag: which, cls: (el.getAttribute('class') || '') + which,
                x: rc.x, y: rc.y, w: rc.w, h: rc.h, fill: opaque(bg) ? bg : null,
                radius: radius, borders: borders(cs), shadow: null, op: parseFloat(cs.opacity)});
    }
    if (text) {
      var m = marks(cs, null);
      out.push({k: 'text', tag: which, cls: (el.getAttribute('class') || '') + which,
                x: rc.x, y: rc.y, w: rc.w, h: rc.h,
                fs: m.px, lh: cs.lineHeight === 'normal' ? null : px(parseFloat(cs.lineHeight) || 0),
                align: 'center', pre: false, vertical: false,
                lines: 1, wrap: false, slack: 0, sc: px(accScale(el)),
                paras: [[{s: transform(text, cs.textTransform), m: m}]]});
    }
  }

  /* ---- boxes ---------------------------------------------------------------------------- */
  function radii(cs) {
    return [parseFloat(cs.borderTopLeftRadius) || 0, parseFloat(cs.borderTopRightRadius) || 0,
            parseFloat(cs.borderBottomRightRadius) || 0, parseFloat(cs.borderBottomLeftRadius) || 0];
  }
  // Per side, on purpose: the deck's dominant motif is a left- or top-accent band with no other
  // border (.highlight, .fpoint, .quiz-ans, .timeline, .conccol, .mcell). Reporting one uniform
  // border would draw three edges that aren't there.
  function borders(cs) {
    var S = ['Top', 'Right', 'Bottom', 'Left'], out = {}, any = false;
    for (var i = 0; i < 4; i++) {
      var w = parseFloat(cs['border' + S[i] + 'Width']) || 0;
      var st = cs['border' + S[i] + 'Style'];
      var c = color(cs['border' + S[i] + 'Color']);
      if (w > 0 && st && st !== 'none' && st !== 'hidden' && opaque(c)) {
        out[S[i].toLowerCase()] = {w: px(w), c: c, s: st}; any = true;
      } else out[S[i].toLowerCase()] = null;
    }
    return any ? out : null;
  }
  function shadow(cs) {
    var s = cs.boxShadow;
    if (!s || s === 'none') return null;
    var m = s.match(/(rgba?\([^)]*\)|#[0-9a-f]+)\s+(-?[\d.]+)px\s+(-?[\d.]+)px\s+(-?[\d.]+)px(?:\s+(-?[\d.]+)px)?/i);
    if (!m) return null;
    return {c: color(m[1]), dx: parseFloat(m[2]), dy: parseFloat(m[3]),
            blur: parseFloat(m[4]), spread: parseFloat(m[5] || 0)};
  }

  /* ---- images ---------------------------------------------------------------------------- */
  // Report the PAINTED content rect, not the element box: `object-fit: contain` letterboxes and
  // `cover` crops, and the emitter must place the picture where the eye sees it. Doing this here
  // makes non-uniform image scaling unrepresentable downstream rather than merely audited.
  function fitted(el, r, cs) {
    var nw = el.naturalWidth || 0, nh = el.naturalHeight || 0;
    var fit = cs.objectFit || 'fill';
    if (!nw || !nh || fit === 'fill') return {rect: r, crop: null};
    var sc = fit === 'cover' ? Math.max(r.width / nw, r.height / nh)
                             : Math.min(r.width / nw, r.height / nh);
    if (fit === 'scale-down') sc = Math.min(sc, 1);
    var dw = nw * sc, dh = nh * sc;
    if (fit === 'cover') {
      // Crop the source to the element box (fractions of the natural size).
      var cw = Math.min(1, r.width / dw), ch = Math.min(1, r.height / dh);
      return {rect: r, crop: {l: (1 - cw) / 2, t: (1 - ch) / 2, r: (1 - cw) / 2, b: (1 - ch) / 2}};
    }
    return {rect: new DOMRect(r.x + (r.width - dw) / 2, r.y + (r.height - dh) / 2, dw, dh), crop: null};
  }

  // Inline SVG covers the whole icon set and every ASCII diagram (`_embed` inlines SVG as markup
  // so it inherits `currentColor`). Deduped by source: a deck repeats icons heavily, and the
  // payload travels through a DOM dump.
  var svgs = {}, svgN = 0;
  function svgId(src) {
    for (var k in svgs) if (svgs[k] === src) return k;
    var id = 's' + (svgN++);
    svgs[id] = src;
    return id;
  }

  /* ---- the walk -------------------------------------------------------------------------- */
  var SKIP = /^(deckanim|deckpdf|deckfull|deckstyle|deckthemes|deckstylemenu|notes)$/;

  function skip(el) {
    var c = el.getAttribute && el.getAttribute('class');
    if (c) { var p = c.split(/\s+/); for (var i = 0; i < p.length; i++) if (SKIP.test(p[i])) return true; }
    return el.hasAttribute && (el.hasAttribute('data-deck-pdf') || el.hasAttribute('data-deck-full'));
  }

  /* An element is emitted as a BOX when it paints (fill, border, shadow), as IMG/SVG when it is
   * one (recursion stops — a picture's guts are not shapes), and as TEXT when its content is
   * inline-only (recursion stops — its children are runs, not blocks). Otherwise recurse. A
   * parent is pushed before its children, which is paint order, so the display list can be
   * emitted front to back with no z-sorting. */
  function walk(el, ox, oy, clip, out, warn) {
    var cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return;
    if (skip(el)) return;
    var br = el.getBoundingClientRect();
    if (br.width < 0.5 || br.height < 0.5) return;
    var r = intersect(rect(br, ox, oy), clip);
    if (r.w < 0.5 || r.h < 0.5) return;

    var bg = color(cs.backgroundColor);
    var bd = borders(cs);
    var sh = shadow(cs);
    var bimg = cs.backgroundImage && cs.backgroundImage !== 'none' ? cs.backgroundImage : null;

    if (opaque(bg) || bd || sh || bimg) {
      out.push({k: 'box', tag: el.tagName.toLowerCase(), cls: el.getAttribute('class') || '',
                x: r.x, y: r.y, w: r.w, h: r.h,
                fill: opaque(bg) ? bg : null, borders: bd, shadow: sh,
                radius: radii(cs), op: parseFloat(cs.opacity),
                approx: bimg ? 'background-image' : null});
      if (bimg) warn.push('approximated background-image on .' + (el.getAttribute('class') || el.tagName));
    }

    pseudo(el, '::before', ox, oy, clip, out);

    if (el.tagName === 'IMG') {
      var f = fitted(el, br, cs);
      var fr = intersect(rect(f.rect, ox, oy), clip);
      out.push({k: 'img', x: fr.x, y: fr.y, w: fr.w, h: fr.h, crop: f.crop,
                src: el.getAttribute('src') || '', alt: el.getAttribute('alt') || '',
                nw: el.naturalWidth || 0, nh: el.naturalHeight || 0});
      return;
    }
    if (el.tagName === 'svg' || el.tagName === 'SVG') {
      out.push({k: 'svg', x: r.x, y: r.y, w: r.w, h: r.h,
                cls: String(el.getAttribute('class') || ''), col: color(cs.color),
                id: svgId(el.outerHTML)});
      return;
    }
    if (el.tagName === 'VIDEO' || el.tagName === 'IFRAME' || el.tagName === 'CANVAS') {
      out.push({k: 'media', tag: el.tagName.toLowerCase(), x: r.x, y: r.y, w: r.w, h: r.h,
                src: el.getAttribute('src') || el.getAttribute('data-src') || ''});
      warn.push(el.tagName.toLowerCase() + ' cannot be exported — a poster frame is drawn');
      return;
    }

    var raw = el.textContent || '';
    if (raw.trim() && inlineOnly(el)) {
      var m0 = marks(cs, null);
      var flat = runsOf(el, m0, []);
      // One paragraph per <br> and, in `pre` mode, per newline: `.cbcode` must keep its lines.
      var pre = /^(pre|pre-wrap|break-spaces)/.test(cs.whiteSpace);
      var paras = [[]];
      for (var i = 0; i < flat.length; i++) {
        var run = flat[i];
        if (run.br) { paras.push([]); continue; }
        var parts = pre ? run.s.split('\n') : [run.s];
        for (var j = 0; j < parts.length; j++) {
          if (j) paras.push([]);
          if (parts[j] !== '') paras[paras.length - 1].push({s: parts[j], m: run.m});
        }
      }
      var lines = pre ? paras.length : lineCount(el);
      // Free vertical space below: the emitter grows a wrapped textbox into it so one extra
      // line lands in whitespace rather than on the next card.
      var slack = 0;
      if (el.parentElement) {
        var pcs = getComputedStyle(el.parentElement);
        var pb = el.parentElement.getBoundingClientRect().bottom - (parseFloat(pcs.paddingBottom) || 0);
        slack = Math.max(0, px(pb - br.bottom));
      }
      out.push({
        k: 'text', tag: el.tagName.toLowerCase(), cls: el.getAttribute('class') || '',
        x: r.x, y: r.y, w: r.w, h: r.h,
        pad: [parseFloat(cs.paddingTop) || 0, parseFloat(cs.paddingRight) || 0,
              parseFloat(cs.paddingBottom) || 0, parseFloat(cs.paddingLeft) || 0],
        fs: px(parseFloat(cs.fontSize) || 0),
        lh: cs.lineHeight === 'normal' ? null : px(parseFloat(cs.lineHeight) || 0),
        align: cs.textAlign, pre: pre,
        vertical: /vertical/.test(cs.writingMode || ''),
        lines: lines, wrap: lines > 1, slack: slack,
        sc: px(accScale(el)), paras: paras
      });
      pseudo(el, '::after', ox, oy, clip, out);
      return;
    }

    // Clip descendants to this element when it hides its overflow (`.cbody`, `.codebox`,
    // `.ncard`, every image frame) — otherwise a shrunk code panel exports its hidden tail.
    var sub = clip;
    if (cs.overflow === 'hidden' || cs.overflowX === 'hidden' || cs.overflowY === 'hidden') {
      sub = intersect(rect(br, ox, oy), clip);
    }
    for (var c = 0; c < el.children.length; c++) walk(el.children[c], ox, oy, sub, out, warn);
    pseudo(el, '::after', ox, oy, clip, out);
  }

  /* ---- speaker notes ---------------------------------------------------------------------- */
  // The notes aside is `display:none`, so the walk never reaches it. Harvesting it here (rather
  // than re-reading slide-model.json) keeps one text path and one markdown resolver, and means a
  // deck can be exported on its own, with no Talk folder beside it.
  function notesOf(sec) {
    var a = sec.querySelector('aside.notes');
    if (!a) return '';
    var ps = a.querySelectorAll('p'), parts = [];
    for (var i = 0; i < ps.length; i++) parts.push(ps[i].textContent || '');
    if (!parts.length) parts.push(a.textContent || '');
    return parts.join('\n\n').replace(/\n{3,}/g, '\n\n').trim();
  }

  /* ---- entry ------------------------------------------------------------------------------ */
  function emit(id, obj) {
    var s = document.createElement('script');
    s.type = 'application/json';
    s.id = id;
    // Escape "</" so nothing in the harvested content can end this block early.
    s.textContent = JSON.stringify(obj).replace(/<\//g, '<\\/');
    document.body.appendChild(s);
  }

  function harvest() {
    if (document.getElementById('deck-harvest')) return;
    try {
      var slides = [];
      var secs = document.querySelectorAll('.reveal .slides section.slide');
      for (var i = 0; i < secs.length; i++) {
        var sec = secs[i];
        var cs = getComputedStyle(sec);
        var br = sec.getBoundingClientRect();
        var nodes = [], warn = [];
        var clip = {x: 0, y: 0, w: px(br.width), h: px(br.height)};
        for (var c = 0; c < sec.children.length; c++) {
          walk(sec.children[c], br.x, br.y, clip, nodes, warn);
        }
        slides.push({i: i, kind: sec.getAttribute('data-kind') || '',
                     w: px(br.width), h: px(br.height),
                     bg: color(cs.backgroundColor), notes: notesOf(sec),
                     warnings: warn, nodes: nodes});
      }
      var root = document.documentElement;
      emit('deck-harvest', {
        v: 1,
        deck: {
          w: slides.length ? slides[0].w : 1280,
          h: slides.length ? slides[0].h : 720,
          theme: root.getAttribute('data-deck-theme') || 'light',
          style: root.getAttribute('data-deck-style') || 'default',
          lang: root.getAttribute('lang') || 'en',
          title: document.title || '',
          fonts: {
            sans: getComputedStyle(document.body).getPropertyValue('--sans').trim(),
            mono: getComputedStyle(document.body).getPropertyValue('--mono').trim()
          },
          page: color(getComputedStyle(document.body).backgroundColor)
        },
        svgs: svgs,
        slides: slides
      });
      root.setAttribute('data-harvest-ready', String(slides.length));
    } catch (e) {
      emit('deck-harvest-error', {error: String((e && e.message) || e), stack: String((e && e.stack) || '')});
      document.documentElement.setAttribute('data-harvest-error', '1');
    }
  }

  // Registered after the init script's own `pdf-ready` listener, so `fitAll()` has already run.
  document.addEventListener('pdf-ready', function () { setTimeout(harvest, 300); });
  // Backstop: if the print view never signals, harvest anyway rather than hand the exporter an
  // empty dump with nothing to explain it.
  setTimeout(harvest, 15000);
})();
