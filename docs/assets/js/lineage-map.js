/**
 * Hyperlex lineage constellation map
 * Radial family hubs + term orbits. Instantly scannable; no external libs.
 * Hallmark · macrostructure: Map/Diagram · technical desk tokens
 */
(function () {
  "use strict";

  const ROOT = document.getElementById("hlx-lineage-map");
  if (!ROOT) return;

  const DATA_URL =
    ROOT.getAttribute("data-src") ||
    new URL("lineage-map.json", ROOT.baseURI || document.baseURI).href;

  const state = {
    data: null,
    focus: "hyperlex", // family id or hyperlex
    query: "",
    hover: null,
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

  async function load() {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load lineage-map.json");
    state.data = await res.json();
    render();
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

  function render() {
    const fams = families();
    const W = Math.min(ROOT.clientWidth || 720, 900);
    const H = Math.min(560, Math.max(420, W * 0.72));
    const cx = W / 2;
    const cy = H / 2;
    const R = Math.min(W, H) * 0.32;

    const focusFam =
      state.focus !== "hyperlex"
        ? fams.find((f) => f.id === state.focus)
        : null;
    const focusTerms = focusFam
      ? termsFor(focusFam.id).filter((t) => matchQuery(t.label))
      : [];

    // Layout family nodes on a ring
    const famPos = {};
    fams.forEach((f, i) => {
      const a = -Math.PI / 2 + (i / fams.length) * Math.PI * 2;
      famPos[f.id] = { x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R, a };
    });

    // Term positions: second ring around focused family, or faint around all
    const termPos = {};
    if (focusFam) {
      const p = famPos[focusFam.id];
      const n = Math.max(focusTerms.length, 1);
      focusTerms.forEach((t, i) => {
        const a = -Math.PI / 2 + (i / n) * Math.PI * 2;
        const r = 88 + (i % 3) * 10;
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

    // Shell
    const shell = el("div", "hlx-map-shell");
    const toolbar = el("div", "hlx-map-toolbar");
    toolbar.innerHTML = `
      <div class="hlx-map-title">
        <strong>Slang lineage map</strong>
        <span>${state.data.n_families} families · ${
      state.data.n_nodes - 1 - state.data.n_families
    } terms · brier null</span>
      </div>
      <label class="hlx-map-search">
        <span class="sr-only">Search terms</span>
        <input type="search" placeholder="Find a term…" value="${escapeAttr(
          state.query
        )}" autocomplete="off" />
      </label>
      <button type="button" class="hlx-map-reset" ${
        state.focus === "hyperlex" && !state.query ? "disabled" : ""
      }>Reset view</button>
    `;
    shell.appendChild(toolbar);

    const body = el("div", "hlx-map-body");
    const canvasWrap = el("div", "hlx-map-canvas-wrap");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("role", "img");
    svg.setAttribute(
      "aria-label",
      "Radial map of slang families and terms"
    );
    svg.classList.add("hlx-map-svg");

    // ring guide
    svg.appendChild(
      svgEl("circle", {
        cx,
        cy,
        r: R,
        class: "hlx-map-ring",
        fill: "none",
      })
    );

    // edges family → root
    fams.forEach((f) => {
      const p = famPos[f.id];
      const active =
        !focusFam || focusFam.id === f.id || hitTerms.some((t) => t.family_id === f.id);
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

    // term edges + nodes
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
        const g = svgEl("g", {
          class: "hlx-map-term",
          transform: `translate(${tp.x},${tp.y})`,
          "data-id": t.id,
        });
        g.appendChild(
          svgEl("circle", {
            r: 5,
            fill: familyColor(t.hue),
            class: "hlx-map-term-dot",
          })
        );
        const label = svgEl("text", {
          x: 8,
          y: 4,
          class: "hlx-map-term-label",
        });
        label.textContent = t.label;
        g.appendChild(label);
        g.addEventListener("click", (ev) => {
          ev.stopPropagation();
          showTerm(t);
        });
        svg.appendChild(g);
      });
    }

    // family nodes
    fams.forEach((f) => {
      const p = famPos[f.id];
      const dim =
        focusFam && focusFam.id !== f.id && !hitTerms.some((t) => t.family_id === f.id);
      const g = svgEl("g", {
        class: dim ? "hlx-map-family is-dim" : "hlx-map-family",
        transform: `translate(${p.x},${p.y})`,
        "data-id": f.id,
        tabindex: "0",
        role: "button",
        "aria-label": `${f.label}, ${f.n_terms} terms`,
      });
      const r = 18 + Math.min(14, Math.sqrt(f.n_terms) * 3);
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
        y: r + 14,
        "text-anchor": "middle",
        class: "hlx-map-family-label",
      });
      lab.textContent = f.label;
      g.appendChild(lab);
      g.addEventListener("click", () => {
        state.focus = f.id;
        render();
        showFamily(f);
      });
      g.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          state.focus = f.id;
          render();
          showFamily(f);
        }
      });
      svg.appendChild(g);
    });

    // center hub
    const hub = svgEl("g", {
      class: "hlx-map-hub",
      transform: `translate(${cx},${cy})`,
      tabindex: "0",
      role: "button",
      "aria-label": "Show all families",
    });
    hub.appendChild(
      svgEl("circle", { r: 36, class: "hlx-map-hub-disk" })
    );
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
    hub.addEventListener("click", () => {
      state.focus = "hyperlex";
      render();
      showOverview();
    });
    svg.appendChild(hub);

    canvasWrap.appendChild(svg);
    body.appendChild(canvasWrap);

    const panel = el("aside", "hlx-map-panel");
    panel.id = "hlx-map-panel";
    body.appendChild(panel);

    shell.appendChild(body);

    // legend
    const legend = el("div", "hlx-map-legend");
    legend.innerHTML = `
      <span><i class="hlx-swatch is-family"></i> Family hub (size ∝ term count)</span>
      <span><i class="hlx-swatch is-term"></i> Term leaf</span>
      <span>Click a hub to expand · search filters terms</span>
      <span>Similarity / map ≠ Brier</span>
    `;
    shell.appendChild(legend);

    ROOT.appendChild(shell);

    // wire controls
    const input = toolbar.querySelector("input");
    input.addEventListener("input", () => {
      state.query = input.value;
      // if searching, auto-focus first matching family
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
    });
    toolbar.querySelector(".hlx-map-reset").addEventListener("click", () => {
      state.focus = "hyperlex";
      state.query = "";
      render();
      showOverview();
    });

    // initial panel
    if (focusFam) showFamily(focusFam);
    else showOverview();

    // search highlight list
    if (q && hitTerms.length) {
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
          const t = state.data.nodes.find((n) => n.id === btn.getAttribute("data-term"));
          if (t) {
            state.focus = t.family_id;
            render();
            showTerm(t);
          }
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
      <p class="hlx-map-blurb">Each hub is a <strong>lineage family</strong> — not a flat word list.
      Size scales with term count. Click a hub to open its leaves.</p>
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
      <p class="hlx-map-footnote">Data: LINEAGE_REGISTRY + YTD first-seen · publish-safe static export · not live Cloud.</p>
    `;
    panel.querySelectorAll("[data-fam]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const f = fams.find((x) => x.id === btn.getAttribute("data-fam"));
        if (f) {
          state.focus = f.id;
          render();
          showFamily(f);
        }
      });
    });
  }

  function showFamily(f) {
    const panel = document.getElementById("hlx-map-panel");
    if (!panel) return;
    const terms = termsFor(f.id).filter((t) => matchQuery(t.label));
    panel.innerHTML = `
      <p class="hlx-map-kicker">Family</p>
      <h2 style="color:${familyColor(f.hue)}">${escapeHtml(f.label)}</h2>
      <p class="hlx-map-meta"><code>${escapeHtml(f.family_id)}</code>
        · operator <code>${escapeHtml(f.branch_operator || "—")}</code>
        · ${f.n_terms} terms</p>
      <p class="hlx-map-blurb">${escapeHtml(f.payload_note || "")}</p>
      <p class="hlx-map-kicker">Terms</p>
      <div class="hlx-map-chips">
        ${terms
          .map((t) => {
            const leaf = t.first_seen_month
              ? `<span class="when">${escapeHtml(t.first_seen_month)}</span>`
              : "";
            return `<button type="button" class="chip" data-term="${escapeAttr(
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
        const t = state.data.nodes.find((n) => n.id === btn.getAttribute("data-term"));
        if (t) showTerm(t);
      });
    });
  }

  function showTerm(t) {
    const panel = document.getElementById("hlx-map-panel");
    if (!panel) return;
    const fam = families().find((f) => f.id === t.family_id);
    panel.innerHTML = `
      <p class="hlx-map-kicker">Term</p>
      <h2><code>${escapeHtml(t.label)}</code></h2>
      <p class="hlx-map-meta">Family
        <button type="button" class="linkish" data-fam="${escapeAttr(
          t.family_id
        )}">${escapeHtml(fam ? fam.label : t.family_id)}</button>
        ${
          t.first_seen_month
            ? ` · first seen in packs <code>${escapeHtml(
                t.first_seen_month
              )}</code>`
            : " · registry trunk (no YTD first-seen)"
        }
      </p>
      <p class="hlx-map-blurb">${escapeHtml(
        (fam && fam.payload_note) || "Atomic slang unit in this lineage family."
      )}</p>
      <div class="hlx-claim hlx-claim--good" style="margin-top:0.75rem">
        <p><strong>Say</strong></p>
        <p>“${escapeHtml(t.label)} is an atomic leaf in the
        ${escapeHtml(fam ? fam.label : t.family_id)} family
        (${escapeHtml(t.branch_operator || "lineage")} operator).”</p>
      </div>
      <div class="hlx-claim hlx-claim--bad" style="margin-top:0.5rem">
        <p><strong>Don’t say</strong></p>
        <p>Map position or cosine score is a probability of virality or Brier skill.</p>
      </div>
    `;
    const b = panel.querySelector("[data-fam]");
    if (b) {
      b.addEventListener("click", () => {
        state.focus = t.family_id;
        render();
        if (fam) showFamily(fam);
      });
    }
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

  // re-render on resize (debounced)
  let t = null;
  window.addEventListener("resize", () => {
    clearTimeout(t);
    t = setTimeout(() => {
      if (state.data) render();
    }, 120);
  });

  load().catch((err) => {
    ROOT.innerHTML = `<p class="hlx-map-error">Could not load map data: ${escapeHtml(
      err.message
    )}</p>`;
  });
})();
