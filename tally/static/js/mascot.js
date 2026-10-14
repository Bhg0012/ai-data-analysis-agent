/* Tally the mascot: a little blue gumdrop with tally-mark hair (four strokes and a slash).
   It dresses up for holidays on its own (see T.costumeFor) and has moods:
   "idle" (blinks), "think" (looks around, hair bounces), "happy" (hops), "oops" (errors). */
(function () {
  const T = (window.Tally = window.Tally || {});

  const BLUE = "#2A78D6", INK = "#16171A", PAPER = "#F6F5F1", CHEEK = "#FFB59A";
  const BODY = "M32 14c13.5 0 22 7.5 22 21v8c0 8.5-6 13-13 13H23c-7 0-13-4.5-13-13v-8c0-13.5 8.5-21 22-21z";
  const VIEW = "-4 -8 72 72";

  // ------------------------------------------------------------ parts
  const hair = () => `<g class="m-hair"><path d="M22 5.5v10"/><path d="M28 4.5v11"/><path d="M34 4.5v11"/><path d="M40 5.5v10"/><path class="m-slash" d="M18.5 14 L43.5 6.5"/></g>`;
  const body = (c) => `<path class="m-body" d="${BODY}" fill="${c}"/>`;
  const cheeks = (c = CHEEK, o = 0.7) => `<ellipse cx="18.5" cy="42" rx="3.6" ry="2.2" fill="${c}" opacity="${o}"/><ellipse cx="45.5" cy="42" rx="3.6" ry="2.2" fill="${c}" opacity="${o}"/>`;
  const line = (d, c = INK, w = 2.6) => `<path d="${d}" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>`;
  const SMILE = "M28 44.5 q4 3.5 8 0";

  function eyes(mood, c = INK) {
    if (mood === "happy") return `<g class="m-eyes">${line("M21 35 q4 -5 8 0 M35 35 q4 -5 8 0", c)}</g>`;
    if (mood === "oops") return `<g class="m-eyes" fill="${c}"><circle cx="25" cy="34" r="2.6"/><circle cx="39" cy="34" r="2.6"/></g>`;
    return `<g class="m-eyes" fill="${c}"><rect x="22" y="29" width="6" height="10" rx="3"/><rect x="36" y="29" width="6" height="10" rx="3"/></g>`;
  }
  const mouth = (mood, c = INK) => (mood === "oops" ? line("M28 46 h8", c) : line(SMILE, c));
  const face = (mood) => eyes(mood) + mouth(mood) + cheeks();

  // ------------------------------------------------------------ everyday looks
  const LOOKS = {
    classic: { name: "Classic", draw: (m) => hair() + `<g class="m-body-g">${body(BLUE)}${face(m)}</g>` },
    blob: { name: "Clean blob", draw: (m) => `<g class="m-body-g">${body(BLUE)}${line("M17 27 q2-7 9-9", "#fff", 2.6).replace("/>", ' opacity=".55"/>')}${face(m)}</g>` },
    tile: {
      name: "App tile",
      draw: (m) => `<g class="m-body-g"><rect x="2" y="2" width="60" height="60" rx="15" fill="${BLUE}"/>
        <g stroke="#fff" stroke-width="2.4" stroke-linecap="round" opacity=".9"><path d="M44 11v7M48 10.5v8M52 10.5v8M56 11v7"/><path d="M42 17.5 L58 12"/></g>
        ${m === "happy" ? `<g class="m-eyes">${line("M20 32 q4 -5 8 0 M36 32 q4 -5 8 0", "#fff", 2.8)}</g>`
          : m === "oops" ? `<g class="m-eyes" fill="#fff"><circle cx="24" cy="31" r="2.8"/><circle cx="40" cy="31" r="2.8"/></g>`
          : `<g class="m-eyes" fill="#fff"><rect x="21" y="25" width="6" height="11" rx="3"/><rect x="37" y="25" width="6" height="11" rx="3"/></g>`}
        ${m === "oops" ? line("M28 44 h8", "#fff", 2.8) : line("M27 43 q5 4.5 10 0", "#fff", 2.8)}</g>`,
    },
    chart: {
      name: "Chart face",
      draw: (m) => `<g class="m-hair"><path d="M26 8v8"/><path d="M32 6v10"/><path d="M38 8v8"/></g><g class="m-body-g">${body(BLUE)}
        ${m === "happy" ? `<g class="m-eyes">${line("M21 35 q4 -5 8 0 M35 35 q4 -5 8 0", "#fff")}</g>`
          : m === "oops" ? `<g class="m-eyes" fill="#fff"><circle cx="25" cy="34" r="2.6"/><circle cx="39" cy="34" r="2.6"/></g>`
          : `<g class="m-eyes" fill="#fff"><rect x="22" y="31" width="6" height="8" rx="2"/><rect x="36" y="27" width="6" height="12" rx="2"/></g>`}
        ${mouth(m, "#fff")}${cheeks("#9EC5F4", 0.9)}</g>`,
    },
  };

  // ------------------------------------------------------------ holiday costumes
  const HAT = {
    party: `<path d="M24 16 L32 -3 L40 16 z" fill="#EDA100"/><path d="M26.5 10 L37.5 10 M29 4 L35 4" stroke="#E87BA4" stroke-width="2.4"/><circle cx="32" cy="-3.5" r="3" fill="#E34948"/>`,
    confetti: `<rect x="4" y="10" width="3" height="3" fill="#EDA100" transform="rotate(20 5 11)"/><rect x="56" y="6" width="3" height="3" fill="#E87BA4"/><circle cx="9" cy="2" r="1.6" fill="#1BAF7A"/><circle cx="55" cy="18" r="1.6" fill="#E34948"/><rect x="50" y="-1" width="3" height="3" fill="${BLUE}" transform="rotate(35 51 0)"/>`,
    tophat: `<rect x="23" y="-4" width="18" height="17" rx="1.5" fill="${INK}"/><rect x="23" y="7" width="18" height="3.5" fill="#E34948"/><rect x="17" y="12" width="30" height="4" rx="2" fill="${INK}"/>`,
    leprechaun: `<path d="M23 2 h18 l3 12 h-24 z" fill="#0B7A3E"/><rect x="23" y="9" width="18" height="3.5" fill="${INK}"/><rect x="29.5" y="8.5" width="5" height="4.5" rx=".8" fill="none" stroke="#EDA100" stroke-width="1.6"/><rect x="15" y="13" width="34" height="4" rx="2" fill="#0B7A3E"/>`,
    shamrock: `<g fill="#0B7A3E" transform="translate(52 40) scale(.9)"><circle cx="0" cy="-3" r="3"/><circle cx="-3" cy="1" r="3"/><circle cx="3" cy="1" r="3"/><path d="M0 1 q1 5 3 7" stroke="#0B7A3E" stroke-width="1.4" fill="none"/></g>`,
    bunny: `<ellipse cx="24" cy="4" rx="5" ry="12" fill="${BLUE}" transform="rotate(-12 24 4)"/><ellipse cx="24" cy="5" rx="2.4" ry="8" fill="#F4B6CC" transform="rotate(-12 24 5)"/><ellipse cx="40" cy="4" rx="5" ry="12" fill="${BLUE}" transform="rotate(12 40 4)"/><ellipse cx="40" cy="5" rx="2.4" ry="8" fill="#F4B6CC" transform="rotate(12 40 5)"/>`,
    egg: `<ellipse cx="54" cy="50" rx="5" ry="6.5" fill="#FAD36B"/><path d="M49.3 49 q2.4 -2 4.7 0 t4.7 0" stroke="#E87BA4" stroke-width="1.4" fill="none"/>`,
    uncleSam: `<rect x="23" y="-4" width="18" height="17" rx="1.5" fill="#fff" stroke="#d3d1c8"/><g stroke="#E34948" stroke-width="2.4"><path d="M27 -3v15M32 -3v15M37 -3v15"/></g><rect x="23" y="7" width="18" height="4" fill="#1C5CAB"/><circle cx="28" cy="9" r=".9" fill="#fff"/><circle cx="32" cy="9" r=".9" fill="#fff"/><circle cx="36" cy="9" r=".9" fill="#fff"/><rect x="17" y="12" width="30" height="4" rx="2" fill="#1C5CAB"/>`,
    fireworks: `<g stroke-linecap="round" stroke-width="1.8"><g stroke="#E34948"><path d="M6 6 l-3 -3M6 6 l3 -3M6 6 l-4 1M6 6 l4 1M6 6v-4"/></g><g stroke="${BLUE}"><path d="M58 4 l-3 -3M58 4 l3 -3M58 4 l-4 1M58 4 l4 1M58 4v-4"/></g></g>`,
    witch: `<path d="M20 15 L33 -6 Q36 -4 37 1 L44 15 z" fill="#4A3A7A"/><rect x="25" y="9" width="16" height="3.5" fill="#EB6834"/><rect x="13" y="13" width="38" height="4" rx="2" fill="#4A3A7A"/>`,
    pilgrim: `<path d="M24 0 h16 l2 13 h-20 z" fill="${INK}"/><rect x="23.5" y="8" width="17" height="3.5" fill="#6B5A44"/><rect x="29" y="7.5" width="6" height="4.5" rx=".6" fill="none" stroke="#EDA100" stroke-width="1.6"/><rect x="15" y="12" width="34" height="4" rx="2" fill="${INK}"/>`,
    santa: `<path d="M16 15 Q18 1 34 0 Q48 0 55 14 L49 16 Q44 8 38 9 Q36 12 46 15 z" fill="#D03B3B"/><circle cx="53" cy="17" r="4.2" fill="#fff"/><rect x="13" y="12" width="36" height="7" rx="3.5" fill="#fff"/>`,
  };
  const heart = (x) => `<path d="M${x} 30.5c-1.6-2.6-5.6-1.3-4.4 1.8.8 2 4.4 4.7 4.4 4.7s3.6-2.7 4.4-4.7c1.2-3.1-2.8-4.4-4.4-1.8z" fill="#D03B3B"/>`;
  const feathers = `<g transform="translate(32 34)">${["#E34948", "#EB6834", "#EDA100", "#9A5B34", "#E34948", "#EB6834", "#EDA100"]
    .map((c, i) => `<ellipse cx="0" cy="-25" rx="5.5" ry="13" fill="${c}" transform="rotate(${-63 + i * 21})"/>`).join("")}</g>`;

  const COSTUMES = {
    newyear: { name: "New Year", back: HAT.confetti, front: HAT.party },
    valentines: { name: "Valentine's Day", hair: true, color: "#E87BA4",
      face: (m) => (m === "idle" || m === "think" ? `<g class="m-eyes">${heart(25)}${heart(39)}</g>${mouth(m)}` : null) },
    presidents: { name: "Presidents' Day", front: HAT.tophat },
    stpatricks: { name: "St. Patrick's Day", color: "#1BAF7A", front: HAT.leprechaun + HAT.shamrock },
    easter: { name: "Easter", back: HAT.bunny, front: HAT.egg },
    july4: { name: "Fourth of July", back: HAT.fireworks, front: HAT.uncleSam },
    pumpkin: { name: "Halloween", color: "#EB6834",
      back: line("M32 15 q0-6 4-9", "#3E7A2A", 3.4),
      deco: `<path d="M24 16 q-4 20 0 39 M40 16 q4 20 0 39" stroke="#C9531F" stroke-width="1.6" fill="none" opacity=".7"/>`,
      face: (m) => (m === "oops" ? null : `<g class="m-eyes" fill="${INK}"><path d="M21 34 l4 -6 l4 6 z M35 34 l4 -6 l4 6 z"/></g><path d="M24 42 l3 3 l3 -3 l3 3 l3 -3 l3 3 l2 -3 q-8 8 -17 0z" fill="${INK}"/>`) },
    witch: { name: "Halloween", front: HAT.witch },
    turkey: { name: "Thanksgiving", color: "#9A5B34", back: feathers,
      face: (m) => eyes(m) + `<path d="M29 40 l3 4 l3 -4 z" fill="#EDA100"/><path d="M33.5 43 q2 4 0 7 q-2 -2 -1 -6z" fill="#D03B3B"/>` + cheeks() },
    pilgrim: { name: "Thanksgiving", front: HAT.pilgrim + `<path d="M23 54 l9 -6 l9 6 z" fill="#fff" opacity=".95"/>` },
    christmas: { name: "Christmas", front: HAT.santa,
      face: (m) => eyes(m) + cheeks() + `<path d="M14 45 q2 14 18 14 q16 0 18 -14 q-6 4 -18 4 q-12 0 -18 -4z" fill="#fff"/><path d="M26 45 q6 -3 12 0" stroke="#fff" stroke-width="3.5" stroke-linecap="round" fill="none"/>` },
  };

  function drawCostume(c, mood) {
    const f = (c.face && c.face(mood)) || face(mood);
    return (c.back || "") + (c.hair ? hair() : "") +
      `<g class="m-body-g">${body(c.color || BLUE)}${c.deco || ""}${f}</g>` + (c.front || "");
  }

  // ------------------------------------------------------------ the holiday calendar
  const day = (y, m, d) => new Date(y, m - 1, d);
  function nthWeekday(y, month, weekday, n) {   // weekday: 0=Sun
    const first = day(y, month, 1);
    return day(y, month, 1 + ((weekday - first.getDay() + 7) % 7) + 7 * (n - 1));
  }
  function easter(y) {                          // anonymous Gregorian algorithm
    const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4;
    const f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451);
    const month = Math.floor((h + l - 7 * m + 114) / 31), dd = ((h + l - 7 * m + 114) % 31) + 1;
    return day(y, month, dd);
  }
  const addDays = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);

  /* Holiday windows for a year, most specific first (the first match wins). */
  function calendar(y) {
    const thanks = nthWeekday(y, 11, 4, 4);
    const pres = nthWeekday(y, 2, 1, 3);
    const east = easter(y);
    return [
      { id: "newyear", from: day(y, 1, 1), to: day(y, 1, 2) },
      { id: "newyear", from: day(y, 12, 31), to: day(y, 12, 31) },
      { id: "valentines", from: day(y, 2, 1), to: day(y, 2, 14) },
      { id: "presidents", from: day(y, 2, 15), to: pres },
      { id: "stpatricks", from: day(y, 3, 1), to: day(y, 3, 17) },
      { id: "easter", from: addDays(east, -7), to: addDays(east, 1) },
      { id: "july4", from: day(y, 6, 27), to: day(y, 7, 5) },
      { id: "pumpkin", from: day(y, 10, 1), to: day(y, 10, 20) },
      { id: "witch", from: day(y, 10, 21), to: day(y, 10, 31) },
      { id: "pilgrim", from: addDays(thanks, -14), to: addDays(thanks, -7) },
      { id: "turkey", from: addDays(thanks, -6), to: addDays(thanks, 3) },
      { id: "christmas", from: day(y, 12, 1), to: day(y, 12, 30) },
    ];
  }

  T.costumeFor = function (date = new Date()) {
    const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const hit = calendar(d.getFullYear()).find((h) => d >= h.from && d <= h.to);
    return hit ? hit.id : null;
  };

  T.nextCostume = function (date = new Date()) {
    const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const all = calendar(d.getFullYear()).concat(calendar(d.getFullYear() + 1)).filter((h) => h.from > d);
    all.sort((a, b) => a.from - b.from);
    return all.length ? { id: all[0].id, name: COSTUMES[all[0].id].name, from: all[0].from } : null;
  };

  // ------------------------------------------------------------ settings + drawing
  // What to wear: settings come from the server (Settings > Tally's look). A URL like
  // ?costume=christmas previews a costume.
  T.mascotPrefs = { look: "classic", holidays: true };

  function current() {
    let forced = null;
    try { forced = new URLSearchParams(location.search).get("costume"); } catch (_) {}
    if (forced && COSTUMES[forced]) return { costume: forced };
    if (T.mascotPrefs.holidays) {
      const c = T.costumeFor();
      if (c) return { costume: c };
    }
    return { look: LOOKS[T.mascotPrefs.look] ? T.mascotPrefs.look : "classic" };
  }

  T.mascot = function (size = 64, mood = "idle", opts = {}) {
    const pick = opts.look || opts.costume ? opts : current();
    const inner = pick.costume ? drawCostume(COSTUMES[pick.costume], mood) : LOOKS[pick.look].draw(mood);
    return `<svg class="mascot mood-${mood}" width="${size}" height="${size}" viewBox="${VIEW}" aria-hidden="true">${inner}</svg>`;
  };

  /* The browser-tab icon follows the mascot (holiday costume included). */
  T.refreshFavicon = function () {
    const svg = T.mascot(64, "idle").replace('class="mascot mood-idle"', 'xmlns="http://www.w3.org/2000/svg"')
      .replace(/<g class="m-hair">/g, `<g class="m-hair" stroke="${INK}" stroke-width="3.4" stroke-linecap="round" fill="none">`);
    let link = document.querySelector('link[rel="icon"]');
    if (!link) { link = document.createElement("link"); link.rel = "icon"; document.head.appendChild(link); }
    link.type = "image/svg+xml";
    link.href = "data:image/svg+xml," + encodeURIComponent(svg);
  };

  T.mascotLooks = Object.fromEntries(Object.entries(LOOKS).map(([k, v]) => [k, v.name]));
  T.mascotCostumes = Object.fromEntries(Object.entries(COSTUMES).map(([k, v]) => [k, v.name]));
  T.BRAND = { BLUE, INK, PAPER };
})();
