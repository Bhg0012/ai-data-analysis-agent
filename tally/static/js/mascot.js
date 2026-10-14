/* Tally the mascot: a little orange gumdrop with tally-mark hair.
   mood: "idle" (blinks), "think" (looks around), "happy", "oops". */
(function () {
  const T = (window.Tally = window.Tally || {});

  T.mascot = function (size = 64, mood = "idle") {
    const eyes =
      mood === "happy"
        ? `<path class="m-eye-happy" d="M21 35 q4 -5 8 0 M35 35 q4 -5 8 0" />`
        : mood === "oops"
        ? `<g class="m-eyes"><circle cx="25" cy="34" r="2.6"/><circle cx="39" cy="34" r="2.6"/></g>`
        : `<g class="m-eyes"><rect x="22" y="29" width="6" height="10" rx="3"/><rect x="36" y="29" width="6" height="10" rx="3"/></g>`;
    const mouth =
      mood === "oops"
        ? `<path class="m-mouth" d="M28 46 h8" />`
        : `<path class="m-mouth" d="M28 44.5 q4 3.5 8 0" />`;
    return `<svg class="mascot mood-${mood}" width="${size}" height="${size}" viewBox="0 0 64 64" aria-hidden="true">
      <g class="m-hair">
        <path d="M22 5.5v10"/><path d="M28 4.5v11"/><path d="M34 4.5v11"/><path d="M40 5.5v10"/>
        <path class="m-slash" d="M18.5 14 L43.5 6.5"/>
      </g>
      <g class="m-body-g">
        <path class="m-body" d="M32 14c13.5 0 22 7.5 22 21v8c0 8.5-6 13-13 13H23c-7 0-13-4.5-13-13v-8c0-13.5 8.5-21 22-21z"/>
        <ellipse class="m-cheek" cx="18.5" cy="42" rx="3.6" ry="2.2"/>
        <ellipse class="m-cheek" cx="45.5" cy="42" rx="3.6" ry="2.2"/>
        ${eyes}
        ${mouth}
      </g>
    </svg>`;
  };

  /* App icon version: mascot on a dark rounded tile. */
  T.appIcon = function (size = 28) {
    return `<svg class="app-icon" width="${size}" height="${size}" viewBox="0 0 64 64" aria-hidden="true">
      <rect width="64" height="64" rx="15" fill="#16171A"/>
      <g transform="translate(9 9) scale(0.72)">
        <g stroke="#F6F5F1" stroke-width="3.4" stroke-linecap="round" fill="none">
          <path d="M22 5.5v10"/><path d="M28 4.5v11"/><path d="M34 4.5v11"/><path d="M40 5.5v10"/>
          <path d="M18.5 14 L43.5 6.5"/>
        </g>
        <path fill="#EB6834" d="M32 14c13.5 0 22 7.5 22 21v8c0 8.5-6 13-13 13H23c-7 0-13-4.5-13-13v-8c0-13.5 8.5-21 22-21z"/>
        <rect x="22" y="29" width="6" height="10" rx="3" fill="#16171A"/>
        <rect x="36" y="29" width="6" height="10" rx="3" fill="#16171A"/>
        <path d="M28 44.5 q4 3.5 8 0" stroke="#16171A" stroke-width="2.6" stroke-linecap="round" fill="none"/>
      </g>
    </svg>`;
  };
})();
