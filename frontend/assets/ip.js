/* IndiaPulse — shared frontend helpers
   Loads json/<category>.json (written by backend/export.py) and renders
   a standard opportunity table. Pure vanilla JS, no build step, so the
   dashboards can be opened directly or served by any static file server. */

const IP = (() => {
  // json/ sits at the repo root. Pages live at different depths below it:
  //   frontend/index.html                -> depth 1 (../json/)
  //   frontend/markets/*.html, etc.       -> depth 2 (../../json/)
  // Pass the actual depth explicitly rather than a root/non-root boolean,
  // since a boolean can't distinguish more than two depths.
  async function loadCategory(name, { depth = 2 } = {}) {
    const base = "../".repeat(depth) + "json/";
    const res = await fetch(`${base}${name}.json`, { cache: "no-store" });
    if (!res.ok) throw new Error(`Could not load ${name}.json (${res.status})`);
    return res.json();
  }

  function tagClass(label) {
    if (!label) return "nodata";
    const key = label.toLowerCase().replace(/\s+/g, "-");
    return key;
  }

  function tag(label) {
    if (!label) return `<span class="tag nodata">No Data</span>`;
    return `<span class="tag ${tagClass(label)}">${label}</span>`;
  }

  function scoreBar(score) {
    const s = Math.max(0, Math.min(100, score ?? 0));
    return `<span class="score-bar-track"><span class="score-bar-fill" style="width:${s}%"></span></span>${s.toFixed(1)}`;
  }

  function renderEmpty(container, message) {
    container.innerHTML = `<div class="ip-empty">${message}</div>`;
  }

  function renderOpportunityTable(container, rows, { limit = null } = {}) {
    if (!rows || rows.length === 0) {
      renderEmpty(container, "No analytics computed yet — run `python -m backend.main --download` to populate this dashboard.");
      return;
    }
    const list = limit ? rows.slice(0, limit) : rows;
    const body = list.map((r, i) => `
      <tr>
        <td class="rank-num">${i + 1}</td>
        <td class="symbol">${r.symbol}</td>
        <td>${r.category ?? ""}</td>
        <td>${tag(r.trend)}</td>
        <td>${tag(r.momentum)}</td>
        <td>${tag(r.seasonality)}</td>
        <td class="num">${scoreBar(r.opportunity_score)}</td>
      </tr>
    `).join("");

    container.innerHTML = `
      <table class="ip-table">
        <thead>
          <tr>
            <th></th><th>Symbol</th><th>Category</th><th>Trend</th><th>Momentum</th><th>Seasonality</th><th>Opportunity</th>
          </tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    `;
  }

  function renderSummaryCards(container, payload) {
    const results = payload?.data || [];
    if (!results.length && !payload?.count) {
      renderEmpty(container, "No data yet.");
      return;
    }
    const total = payload?.count ?? results.length;
    const scored = payload?.scored_count ?? results.length;
    const gaps = payload?.coverage_gaps?.length ?? 0;
    const bullish = results.filter(r => r.trend?.trend === "Bullish").length;
    const avgOpp = payload?.avg_opportunity_score != null ? payload.avg_opportunity_score.toFixed(1) : "—";
    const strongSeason = results.filter(r => r.seasonality?.seasonality === "Seasonally Strong").length;
    const top = [...results].sort((a, b) => (b.opportunity?.opportunity_score ?? 0) - (a.opportunity?.opportunity_score ?? 0))[0];

    container.innerHTML = `
      <div class="ip-card"><div class="label">Constituents</div><div class="value">${total}</div>${gaps ? `<div class="sub">${scored} scored · ${gaps} pending data</div>` : ""}</div>
      <div class="ip-card"><div class="label">Bullish Trend</div><div class="value">${bullish}/${scored}</div></div>
      <div class="ip-card"><div class="label">Avg Opportunity Score</div><div class="value">${avgOpp}</div></div>
      <div class="ip-card"><div class="label">Seasonally Strong</div><div class="value">${strongSeason}</div></div>
      <div class="ip-card"><div class="label">Top Symbol</div><div class="value">${top?.symbol ?? "—"}</div><div class="sub">${top?.opportunity?.opportunity_score ?? ""}</div></div>
    `;
  }

  function renderCoverageGaps(container, gaps) {
    if (!gaps || gaps.length === 0) {
      container.innerHTML = "";
      container.style.display = "none";
      return;
    }
    container.style.display = "";
    const body = gaps.map(g => `
      <tr>
        <td class="symbol">${g.symbol}</td>
        <td>${g.category ?? ""}</td>
        <td>${g.reason ?? "insufficient underlying data"}</td>
      </tr>
    `).join("");
    container.innerHTML = `
      <table class="ip-table">
        <thead><tr><th>Symbol</th><th>Category</th><th>Why it's not ranked</th></tr></thead>
        <tbody>${body}</tbody>
      </table>
    `;
  }

  function renderDetailTable(container, results) {
    if (!results || results.length === 0) {
      renderEmpty(container, "No analytics computed yet — run the backend pipeline to populate this dashboard.");
      return;
    }
    const sorted = [...results].sort((a, b) => (b.opportunity?.opportunity_score ?? 0) - (a.opportunity?.opportunity_score ?? 0));
    const body = sorted.map(r => `
      <tr>
        <td class="symbol">${r.symbol}</td>
        <td>${tag(r.trend?.trend)}</td>
        <td>${tag(r.momentum?.momentum)}</td>
        <td>${tag(r.volatility?.volatility)}</td>
        <td>${tag(r.risk?.risk)}</td>
        <td>${tag(r.seasonality?.seasonality)}</td>
        <td class="num">${r.trend?.price ?? "—"}</td>
        <td class="num">${scoreBar(r.opportunity?.opportunity_score)}</td>
        <td>${tag(r.opportunity?.rating)}</td>
      </tr>
    `).join("");

    container.innerHTML = `
      <table class="ip-table">
        <thead>
          <tr>
            <th>Symbol</th><th>Trend</th><th>Momentum</th><th>Volatility</th><th>Risk</th><th>Seasonality</th><th>Price</th><th>Opp. Score</th><th>Rating</th>
          </tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    `;
  }

  return { loadCategory, tag, scoreBar, renderEmpty, renderOpportunityTable, renderSummaryCards, renderDetailTable, renderCoverageGaps };
})();
