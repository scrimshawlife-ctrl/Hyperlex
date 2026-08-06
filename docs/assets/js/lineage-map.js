/**
 * Hyperlex lineage constellation map
 * Radial family hubs + term orbits + deep links (?term= / ?family= / ?q=)
 * Within-family hash-neighbor arcs when a term is selected (INFERRED ≠ Brier)
 */
(function () {
  "use strict";

  const ROOT = document.getElementById("hlx-lineage-map");
  if (!ROOT) return;

  const DATA_URL =
    ROOT.getAttribute("data-src") ||
    new URL("lineage-map.json", document.baseURI).href;

  const state = {
    data: null,
    focus: "hyperlex",
    query: "",
    selectedTermId: null,
  };

  function oklch(h, l, c) {
    return `oklch(${l}% ${c} ${h})`;
  }
  function familyColor(hue) {
    return oklch(hue || 220, 72, 0.14);
  }
  function familySoft(hue) {
    return oklch(hue || 220, 28, 0.06);
  }

  function parseDeepLink() {
    const params = new URLSearchParams(window.location.search);
    return {
      term: (params.get("term") || "").trim(),
      family: (params.get("family") || "").trim(),
      q: (params.get("q") || params.get("query") || "").trim(),
    };
  }

  function findTermNode(termText) {
    if (!termText || !state.data) return null;
    const key = termText.toLowerCase();
    const exact = state.data.nodes.filter(
      (n) => n.kind === "term" && n.label.toLowerCase() === key
    );
    if (exact.length) return exact[0];
    const partial = state.data.nodes.find(
      (n) => n.kind === "term" && n.label.toLowerCase().includes(key)
    );
    return partial || null;
  }

  function findFamily(familyId) {
    if (!familyId || !state.data) return null;
    return (
      state.data.nodes.find(
        (n) => n.kind === "family" && n.id === familyId
      ) ||
      state.data.nodes.find(
        (n) =>
          n.kind === "family" &&
          n.label.toLowerCase() === familyId.toLowerCase()
      )
    );
  }

  function applyDeepLink() {
    const dl = parseDeepLink();
    if (dl.q) state.query = dl.q;
    if (dl.term) {
      const t = findTermNode(dl.term);
      if (t) {
        state.focus = t.family_id;
        state.selectedTermId = t.id;
        state.query = state.query || t.label;
        return { type: "term", node: t };
      }
    }
    if (dl.family) {
      const f = findFamily(dl.family);
      if (f) {
        state.focus = f.id;
        state.selectedTermId = null;
        return { type: "family", node: f };
      }
    }
    if (dl.q) {
      const t = findTermNode(dl.q);
      if (t) {
        state.focus = t.family_id;
        state.selectedTermId = t.id;
        return { type: "term", node: t };
      }
    }
    return { type: "overview" };
  }

  function pushDeepLink() {
    if (!window.history || !window.history.replaceState) return;
    const params = new URLSearchParams();
    if (state.selectedTermId) {
      const t = state.data.nodes.find((n) => n.id === state.selectedTermId);
      if (t) params.set("term", t.label);
    } else if (state.focus && state.focus !== "hyperlex") {
      params.set("family", state.focus);
    }
    if (state.query && !state.selectedTermId) {
      params.set("q", state.query);
    }
    const qs = params.toString();
    const url = qs
      ? `${window.location.pathname}?${qs}${window.location.hash || ""}`
      : `${window.location.pathname}${window.location.hash || ""}`;
    window.history.replaceState({}, "", url);
  }

  async function load() {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load lineage-map.json");
    state.data = await res.json();
    const applied = applyDeepLink();
    render();
    if (applied.type === "term") showTerm(applied.node);
    else if (applied.type === "family") showFamily(applied.node);
    else showOverview();
  }

  function families() {
    return state.data.nodes.filter((n) => n.kind === "family");
  }

  function termsFor(familyId) {
    return state.data.nodes.filter(
      (n) => n.kind === "term" && n.family_id === familyId
    );
  }

  function matchQuery(label) {
    const q = state.query.trim().toLowerCase();
    if (!q) return true;
    return String(label).toLowerCase().includes(q);
  }

  function selectFamily(f, { push = true } = {}) {
    state.focus = f.id;
    state.selectedTermId = null;
    render();
    showFamily(f);
    if (push) pushDeepLink();
  }

  function selectTerm(t, { push = true } = {}) {
    state.focus = t.family_id;
    state.selectedTermId = t.id;
    render();
    showTerm(t);
    if (push) pushDeepLink();
  }

  function resetView({ push = true } = {}) {
    state.focus = "hyperlex";
    state.query = "";
    state.selectedTermId = null;
    render();
    showOverview();
    if (push) pushDeepLink();
  }

  function shortFamilyLabel(label, narrow) {
    if (!narrow) return label;
    // Compact labels for phone constellation
    const map = {
      "Betting / Sharp": "Betting",
      "Crypto / Degen": "Crypto",
      "AI-native": "AI",
      "Brainrot / Aura": "Brainrot",
      Kinship: "Kin",
      "Political status": "Political",
      "Gaming / Meta": "Gaming",
      "Workplace / Corp": "Work",
    };
    return map[label] || label;
  }

  function render() {
    const fams = families();
    const narrow = (ROOT.clientWidth || 720) < 480;
    const W = Math.min(ROOT.clientWidth || 720, 900);
    const H = narrow
      ? Math.min(400, Math.max(320, W * 0.95))
      : Math.min(560, Math.max(420, W * 0.72));
    const cx = W / 2;
    const cy = H / 2;
    const R = Math.min(W, H) * (narrow ? 0.28 : 0.32);

    const focusFam =
      state.focus !== "hyperlex"
        ? fams.find((f) => f.id === state.focus)
        : null;
    const focusTerms = focusFam
      ? termsFor(focusFam.id).filter((t) => matchQuery(t.label))
      : [];

    const famPos = {};
    fams.forEach((f, i) => {
      const a = -Math.PI / 2 + (i / fams.length) * Math.PI * 2;
      famPos[f.id] = { x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R, a };
    });

    const termPos = {};
    if (focusFam) {
      const p = famPos[focusFam.id];
      const n = Math.max(focusTerms.length, 1);
      const baseR = narrow ? 64 : 88;
      focusTerms.forEach((t, i) => {
        const a = -Math.PI / 2 + (i / n) * Math.PI * 2;
        const r = baseR + (i % 3) * (narrow ? 8 : 10);
        termPos[t.id] = {
          x: p.x + Math.cos(a) * r,
          y: p.y + Math.sin(a) * r,
        };
      });
    }

    const q = state.query.trim().toLowerCase();
    const hitTerms = q
      ? state.data.nodes.filter(
          (n) => n.kind === "term" && matchQuery(n.label)
        )
      : [];

    ROOT.innerHTML = "";
    ROOT.classList.add("hlx-map-root");

    const shell = el("div", "hlx-map-shell");
    const toolbar = el("div", "hlx-map-toolbar");
    const nTerms = state.data.n_nodes - 1 - state.data.n_families;
    toolbar.innerHTML = `
      <div class="hlx-map-title">
        <strong>Slang lineage map</strong>
        <span>${state.data.n_families} families · ${nTerms} terms
        · neighbors INFERRED · brier null</span>
      </div>
      <label class="hlx-map-search">
        <span class="sr-only">Search terms</span>
        <input type="search" placeholder="Find a term…" value="${escapeAttr(
          state.query
        )}" autocomplete="off" />
      </label>
      <button type="button" class="hlx-map-reset" ${
        state.focus === "hyperlex" && !state.query && !state.selectedTermId
          ? "disabled"
          : ""
      }>Reset view</button>
      <button type="button" class="hlx-map-copy" title="Copy link to this view">Copy link</button>
    `;
    shell.appendChild(toolbar);

    const body = el("div", "hlx-map-body");
    const canvasWrap = el("div", "hlx-map-canvas-wrap");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Radial map of slang families and terms");
    svg.classList.add("hlx-map-svg");

    svg.appendChild(
      svgEl("circle", {
        cx,
        cy,
        r: R,
        class: "hlx-map-ring",
        fill: "none",
      })
    );

    fams.forEach((f) => {
      const p = famPos[f.id];
      const active =
        !focusFam ||
        focusFam.id === f.id ||
        hitTerms.some((t) => t.family_id === f.id);
      svg.appendChild(
        svgEl("line", {
          x1: cx,
          y1: cy,
          x2: p.x,
          y2: p.y,
          class: active ? "hlx-map-edge" : "hlx-map-edge is-dim",
          stroke: familyColor(f.hue),
        })
      );
    });

    // Neighbor arcs for selected term
    if (focusFam && state.selectedTermId && termPos[state.selectedTermId]) {
      const selected = focusTerms.find((t) => t.id === state.selectedTermId);
      if (selected && selected.neighbors) {
        selected.neighbors.forEach((n) => {
          const other = focusTerms.find(
            (t) => t.label.toLowerCase() === String(n.term).toLowerCase()
          );
          if (!other || !termPos[other.id]) return;
          const a = termPos[selected.id];
          const b = termPos[other.id];
          svg.appendChild(
            svgEl("line", {
              x1: a.x,
              y1: a.y,
              x2: b.x,
              y2: b.y,
              class: "hlx-map-edge-neighbor",
              stroke: familyColor(focusFam.hue),
              "stroke-opacity": Math.min(0.85, 0.25 + n.score),
            })
          );
        });
      }
    }

    if (focusFam) {
      const p = famPos[focusFam.id];
      focusTerms.forEach((t) => {
        const tp = termPos[t.id];
        svg.appendChild(
          svgEl("line", {
            x1: p.x,
            y1: p.y,
            x2: tp.x,
            y2: tp.y,
            class: "hlx-map-edge-term",
            stroke: familyColor(focusFam.hue),
          })
        );
      });
      focusTerms.forEach((t) => {
        const tp = termPos[t.id];
        const selected = t.id === state.selectedTermId;
        const g = svgEl("g", {
          class: selected ? "hlx-map-term is-selected" : "hlx-map-term",
          transform: `translate(${tp.x},${tp.y})`,
          "data-id": t.id,
        });
        if (selected) {
          g.appendChild(
            svgEl("circle", {
              r: 12,
              class: "hlx-map-term-ring",
              fill: "none",
              stroke: familyColor(t.hue),
            })
          );
        }
        g.appendChild(
          svgEl("circle", {
            r: selected ? 7 : 5,
            fill: familyColor(t.hue),
            class: "hlx-map-term-dot",
          })
        );
        const label = svgEl("text", {
          x: 8,
          y: 4,
          class: selected
            ? "hlx-map-term-label is-selected"
            : "hlx-map-term-label",
        });
        label.textContent = t.label;
        g.appendChild(label);
        g.addEventListener("click", (ev) => {
          ev.stopPropagation();
          selectTerm(t);
        });
        svg.appendChild(g);
      });
    }

    fams.forEach((f) => {
      const p = famPos[f.id];
      const dim =
        focusFam &&
        focusFam.id !== f.id &&
        !hitTerms.some((t) => t.family_id === f.id);
      const g = svgEl("g", {
        class: dim ? "hlx-map-family is-dim" : "hlx-map-family",
        transform: `translate(${p.x},${p.y})`,
        "data-id": f.id,
        tabindex: "0",
        role: "button",
        "aria-label": `${f.label}, ${f.n_terms} terms`,
      });
      const r = (narrow ? 14 : 18) + Math.min(narrow ? 10 : 14, Math.sqrt(f.n_terms) * 3);
      g.appendChild(
        svgEl("circle", {
          r,
          fill: familySoft(f.hue),
          stroke: familyColor(f.hue),
          class: "hlx-map-family-disk",
        })
      );
      const count = svgEl("text", {
        y: 4,
        "text-anchor": "middle",
        class: "hlx-map-family-count",
      });
      count.textContent = String(f.n_terms);
      g.appendChild(count);
      const lab = svgEl("text", {
        y: r + (narrow ? 12 : 14),
        "text-anchor": "middle",
        class: "hlx-map-family-label",
      });
      lab.textContent = shortFamilyLabel(f.label, narrow);
      g.appendChild(lab);
      g.addEventListener("click", () => selectFamily(f));
      g.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          selectFamily(f);
        }
      });
      svg.appendChild(g);
    });

    const hub = svgEl("g", {
      class: "hlx-map-hub",
      transform: `translate(${cx},${cy})`,
      tabindex: "0",
      role: "button",
      "aria-label": "Show all families",
    });
    hub.appendChild(svgEl("circle", { r: 36, class: "hlx-map-hub-disk" }));
    const hubT = svgEl("text", {
      y: -2,
      "text-anchor": "middle",
      class: "hlx-map-hub-title",
    });
    hubT.textContent = "Slang";
    hub.appendChild(hubT);
    const hubS = svgEl("text", {
      y: 14,
      "text-anchor": "middle",
      class: "hlx-map-hub-sub",
    });
    hubS.textContent = `${fams.length} families`;
    hub.appendChild(hubS);
    hub.addEventListener("click", () => resetView());
    svg.appendChild(hub);

    canvasWrap.appendChild(svg);
    body.appendChild(canvasWrap);

    const panel = el("aside", "hlx-map-panel");
    panel.id = "hlx-map-panel";
    body.appendChild(panel);
    shell.appendChild(body);

    const legend = el("div", "hlx-map-legend");
    legend.innerHTML = `
      <span><i class="hlx-swatch is-family"></i> Family hub (size ∝ term count)</span>
      <span><i class="hlx-swatch is-term"></i> Term leaf</span>
      <span><i class="hlx-swatch is-neighbor"></i> Hash neighbor (INFERRED)</span>
      <span>Deep link: <code>?term=rizz</code> · <code>?family=brainrot-aura</code></span>
      <span>Map / cosine ≠ Brier</span>
    `;
    shell.appendChild(legend);
    ROOT.appendChild(shell);

    const input = toolbar.querySelector("input");
    input.addEventListener("input", () => {
      state.query = input.value;
      state.selectedTermId = null;
      if (state.query.trim()) {
        const hits = state.data.nodes.filter(
          (n) => n.kind === "term" && matchQuery(n.label)
        );
        if (hits.length) {
          const counts = {};
          hits.forEach((h) => {
            counts[h.family_id] = (counts[h.family_id] || 0) + 1;
          });
          const best = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
          if (best) state.focus = best[0];
        }
      }
      render();
      if (state.focus !== "hyperlex") {
        const f = fams.find((x) => x.id === state.focus);
        if (f) showFamily(f);
      } else showOverview();
      pushDeepLink();
    });
    toolbar.querySelector(".hlx-map-reset").addEventListener("click", () => {
      resetView();
    });
    toolbar.querySelector(".hlx-map-copy").addEventListener("click", () => {
      pushDeepLink();
      const url = window.location.href;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => {
          const btn = toolbar.querySelector(".hlx-map-copy");
          const prev = btn.textContent;
          btn.textContent = "Copied";
          setTimeout(() => {
            btn.textContent = prev;
          }, 1200);
        });
      }
    });

    if (focusFam && state.selectedTermId) {
      const t = focusTerms.find((x) => x.id === state.selectedTermId);
      if (t) showTerm(t);
      else showFamily(focusFam);
    } else if (focusFam) showFamily(focusFam);
    else showOverview();

    if (q && hitTerms.length && !state.selectedTermId) {
      const list = hitTerms
        .slice(0, 12)
        .map(
          (t) =>
            `<li><button type="button" data-term="${escapeAttr(
              t.id
            )}"><code>${escapeHtml(t.label)}</code> · ${escapeHtml(
              t.family_id
            )}</button></li>`
        )
        .join("");
      panel.insertAdjacentHTML(
        "beforeend",
        `<div class="hlx-map-hits"><p class="hlx-map-kicker">Search hits (${hitTerms.length})</p><ul>${list}</ul></div>`
      );
      panel.querySelectorAll("[data-term]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const t = state.data.nodes.find(
            (n) => n.id === btn.getAttribute("data-term")
          );
          if (t) selectTerm(t);
        });
      });
    }
  }

  function showOverview() {
    const panel = document.getElementById("hlx-map-panel");
    if (!panel || !state.data) return;
    const fams = families()
      .slice()
      .sort((a, b) => b.n_terms - a.n_terms);
    panel.innerHTML = `
      <p class="hlx-map-kicker">Overview</p>
      <h2>Eight slang families</h2>
      <p class="hlx-map-blurb">Each hub is a <strong>lineage family</strong>.
      Size scales with term count. Click a hub to open leaves.
      Share a view with <code>?term=rizz</code> or <code>?family=ai-native</code>.</p>
      <ul class="hlx-map-famlist">
        ${fams
          .map(
            (f) => `
          <li>
            <button type="button" data-fam="${escapeAttr(f.id)}">
              <span class="dot" style="background:${familyColor(f.hue)}"></span>
              <span class="name">${escapeHtml(f.label)}</span>
              <span class="n">${f.n_terms}</span>
            </button>
          </li>`
          )
          .join("")}
      </ul>
      <p class="hlx-map-footnote">Data: LINEAGE_REGISTRY + YTD first-seen + within-family hash neighbors · not live Cloud.</p>
    `;
    panel.querySelectorAll("[data-fam]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const f = fams.find((x) => x.id === btn.getAttribute("data-fam"));
        if (f) selectFamily(f);
      });
    });
  }

  function showFamily(f) {
    const panel = document.getElementById("hlx-map-panel");
    if (!panel) return;
    const terms = termsFor(f.id).filter((t) => matchQuery(t.label));
    const mapBase = window.location.pathname;
    panel.innerHTML = `
      <p class="hlx-map-kicker">Family</p>
      <h2 style="color:${familyColor(f.hue)}">${escapeHtml(f.label)}</h2>
      <p class="hlx-map-meta"><code>${escapeHtml(f.family_id)}</code>
        · operator <code>${escapeHtml(f.branch_operator || "—")}</code>
        · ${f.n_terms} terms
        · <a href="${escapeAttr(mapBase + "?family=" + encodeURIComponent(f.id))}">permalink</a></p>
      <p class="hlx-map-blurb">${escapeHtml(f.payload_note || "")}</p>
      <p class="hlx-map-kicker">Terms</p>
      <div class="hlx-map-chips">
        ${terms
          .map((t) => {
            const leaf = t.first_seen_month
              ? `<span class="when">${escapeHtml(t.first_seen_month)}</span>`
              : "";
            const sel =
              t.id === state.selectedTermId ? " is-selected" : "";
            return `<button type="button" class="chip${sel}" data-term="${escapeAttr(
              t.id
            )}"><code>${escapeHtml(t.label)}</code>${leaf}</button>`;
          })
          .join("")}
      </div>
      ${
        f.diagram_ref
          ? `<p class="hlx-map-footnote">Static diagram: <code>${escapeHtml(
              f.diagram_ref
            )}</code></p>`
          : ""
      }
      <p class="hlx-map-footnote"><a href="../slang-lineages/">Lineage docs</a> ·
        <a href="../demos/reading-evidence/">How to read evidence</a></p>
    `;
    panel.querySelectorAll("[data-term]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const t = state.data.nodes.find(
          (n) => n.id === btn.getAttribute("data-term")
        );
        if (t) selectTerm(t);
      });
    });
  }

  function showTerm(t) {
    const panel = document.getElementById("hlx-map-panel");
    if (!panel) return;
    const fam = families().find((f) => f.id === t.family_id);
    const mapBase = window.location.pathname;
    const neigh = (t.neighbors || [])
      .map(
        (n) =>
          `<button type="button" class="chip" data-neigh="${escapeAttr(
            n.term
          )}"><code>${escapeHtml(n.term)}</code>
          <span class="when">${n.score}</span></button>`
      )
      .join("");
    panel.innerHTML = `
      <p class="hlx-map-kicker">Term</p>
      <h2><code>${escapeHtml(t.label)}</code></h2>
      <p class="hlx-map-meta">Family
        <button type="button" class="linkish" data-fam="${escapeAttr(
          t.family_id
        )}">${escapeHtml(fam ? fam.label : t.family_id)}</button>
        ${
          t.first_seen_month
            ? ` · first seen <code>${escapeHtml(t.first_seen_month)}</code>`
            : " · registry trunk"
        }
        · <a href="${escapeAttr(
          mapBase + "?term=" + encodeURIComponent(t.label)
        )}">permalink</a>
      </p>
      <p class="hlx-map-blurb">${escapeHtml(
        (fam && fam.payload_note) || "Atomic slang unit in this lineage family."
      )}</p>
      ${
        neigh
          ? `<p class="hlx-map-kicker">Within-family neighbors (hash embed · INFERRED)</p>
             <div class="hlx-map-chips">${neigh}</div>
             <p class="hlx-map-footnote">Cosine on hyperlex.hash_ngram_v1.d256 — not Brier.</p>`
          : ""
      }
      <div class="hlx-claim hlx-claim--good" style="margin-top:0.75rem">
        <p><strong>Say</strong></p>
        <p>“${escapeHtml(t.label)} is an atomic leaf in the
        ${escapeHtml(fam ? fam.label : t.family_id)} family.”</p>
      </div>
      <div class="hlx-claim hlx-claim--bad" style="margin-top:0.5rem">
        <p><strong>Don’t say</strong></p>
        <p>Map position or neighbor score is a probability of virality or Brier skill.</p>
      </div>
    `;
    const b = panel.querySelector("[data-fam]");
    if (b) {
      b.addEventListener("click", () => {
        const f = fam;
        if (f) selectFamily(f);
      });
    }
    panel.querySelectorAll("[data-neigh]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const label = btn.getAttribute("data-neigh");
        const node = termsFor(t.family_id).find(
          (x) => x.label.toLowerCase() === String(label).toLowerCase()
        );
        if (node) selectTerm(node);
      });
    });
  }

  function el(tag, cls) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    return n;
  }

  function svgEl(tag, attrs) {
    const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    if (attrs) {
      Object.entries(attrs).forEach(([k, v]) => {
        if (v != null) n.setAttribute(k, String(v));
      });
    }
    return n;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (state.data) {
        const sel = state.selectedTermId;
        const focus = state.focus;
        render();
        if (sel) {
          const t = state.data.nodes.find((n) => n.id === sel);
          if (t) showTerm(t);
        } else if (focus !== "hyperlex") {
          const f = families().find((x) => x.id === focus);
          if (f) showFamily(f);
        } else showOverview();
      }
    }, 120);
  });

  window.addEventListener("popstate", () => {
    if (!state.data) return;
    state.focus = "hyperlex";
    state.query = "";
    state.selectedTermId = null;
    const applied = applyDeepLink();
    render();
    if (applied.type === "term") showTerm(applied.node);
    else if (applied.type === "family") showFamily(applied.node);
    else showOverview();
  });

  load().catch((err) => {
    ROOT.innerHTML = `<p class="hlx-map-error">Could not load map data: ${escapeHtml(
      err.message
    )}</p>`;
  });
})();
