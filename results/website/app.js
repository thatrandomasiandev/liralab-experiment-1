(() => {
  const D = window.PEBBLE_DATA;
  const EPS = ["0.0", "0.05", "0.1", "0.2"];

  const ink = "#e8ebe6";
  const muted = "rgba(180, 196, 210, 0.75)";
  const grid = "rgba(140, 160, 180, 0.18)";

  Chart.defaults.color = muted;
  Chart.defaults.borderColor = grid;
  Chart.defaults.font.family = "'IBM Plex Mono', ui-monospace, monospace";
  Chart.defaults.font.size = 11;

  function lineSeries(map, pointRadius = 0) {
    return EPS.map((e) => ({
      label: D.labels[e],
      data: map[e],
      borderColor: D.colors[e],
      backgroundColor: D.colors[e],
      borderWidth: 2,
      pointRadius,
      pointHoverRadius: 4,
      tension: 0.25,
    }));
  }

  function makeLine(id, labels, series, yMin, yMax) {
    const el = document.getElementById(id);
    if (!el || typeof Chart === "undefined") return;
    new Chart(el, {
      type: "line",
      data: { labels, datasets: series },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            labels: { boxWidth: 10, boxHeight: 10, color: muted },
          },
          tooltip: {
            backgroundColor: "#1c2430",
            titleColor: ink,
            bodyColor: ink,
            borderColor: grid,
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: { maxRotation: 0, autoSkipPadding: 8 },
            grid: { color: grid },
          },
          y: {
            min: yMin,
            max: yMax,
            grid: { color: grid },
          },
        },
        animation: { duration: 700, easing: "easeOutQuart" },
      },
    });
  }

  function fillTable() {
    const tb = document.getElementById("final-table");
    if (!tb) return;
    tb.innerHTML = EPS.map((e) => {
      const f = D.final[e];
      const cls = e === "0.2" ? ' class="row-bad"' : "";
      return `<tr${cls}>
        <td>${D.labels[e]}</td>
        <td>${f.true}</td>
        <td>${f.proxy}</td>
        <td>${f.eval_true}</td>
        <td>${f.train.toFixed(3)}</td>
        <td>${f.heldout.toFixed(3)}</td>
        <td>${f.onpol.toFixed(3)}</td>
        <td>${f.fixed.toFixed(3)}</td>
        <td>${f.gh} / 10</td>
      </tr>`;
    }).join("");
  }

  let activeRawEps = "0.0";

  function fillRawTable(epsKey) {
    activeRawEps = epsKey;
    const block = D.rawUpdates && D.rawUpdates[epsKey];
    const tb = document.getElementById("raw-table");
    const meta = document.getElementById("raw-meta");
    if (!tb || !block) return;
    tb.innerHTML = block.rows
      .map((r) => {
        const bad = epsKey === "0.2" ? ' class="row-bad"' : "";
        return `<tr${bad}>
          <td>${r.step.toLocaleString()}</td>
          <td>${r.window_id}</td>
          <td>${r.total_feedback}</td>
          <td>${r.train.toFixed(4)}</td>
          <td>${r.heldout.toFixed(4)}</td>
          <td>${r.onpolicy.toFixed(4)}</td>
          <td>${r.fixed.toFixed(4)}</td>
        </tr>`;
      })
      .join("");
    if (meta) {
      meta.textContent = `${D.labels[epsKey]} · ${block.rows.length} RM updates · source ${block.path}`;
    }
    document.querySelectorAll(".raw-tab").forEach((btn) => {
      const on = btn.dataset.eps === epsKey;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
  }

  function fillReturnsRaw() {
    const tb = document.getElementById("returns-raw-table");
    if (!tb || !D.trueReturn) return;
    tb.innerHTML = D.returnCats
      .map((bin, i) => {
        const cells = EPS.map((e) => {
          const v = D.trueReturn[e][i];
          const cls = e === "0.2" && v < 100 ? ' class="row-bad"' : "";
          return `<td${cls}>${v.toFixed(1)}</td>`;
        }).join("");
        return `<tr><td>${bin}</td>${cells}</tr>`;
      })
      .join("");
  }

  function downloadText(filename, text) {
    const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function downloadRawCsv() {
    const block = D.rawUpdates && D.rawUpdates[activeRawEps];
    if (!block) return;
    const header = "step,window_id,total_feedback,acc_train,acc_heldout,acc_onpolicy,acc_fixed_ref";
    const lines = block.rows.map(
      (r) =>
        `${r.step},${r.window_id},${r.total_feedback},${r.train},${r.heldout},${r.onpolicy},${r.fixed}`
    );
    downloadText(`pebble_reward_update_metrics_eps${activeRawEps}.csv`, [header, ...lines].join("\n"));
  }

  function downloadReturnsCsv() {
    const header = "bin_k_steps,eps_0,eps_0.05,eps_0.1,eps_0.2";
    const lines = D.returnCats.map((bin, i) => {
      const vals = EPS.map((e) => D.trueReturn[e][i]).join(",");
      return `${bin},${vals}`;
    });
    downloadText("pebble_true_return_bins.csv", [header, ...lines].join("\n"));
  }

  function wireRawControls() {
    document.querySelectorAll(".raw-tab").forEach((btn) => {
      btn.addEventListener("click", () => fillRawTable(btn.dataset.eps));
    });
    const dl = document.getElementById("btn-download-csv");
    if (dl) dl.addEventListener("click", downloadRawCsv);
    const dlR = document.getElementById("btn-download-returns");
    if (dlR) dlR.addEventListener("click", downloadReturnsCsv);
  }

  function makeBars() {
    const el = document.getElementById("chart-final-bars");
    if (!el || typeof Chart === "undefined") return;
    new Chart(el, {
      type: "bar",
      data: {
        labels: EPS.map((e) => D.labels[e]),
        datasets: [
          { label: "Train", data: EPS.map((e) => D.final[e].train), backgroundColor: "#9aa8b5" },
          { label: "Held-out", data: EPS.map((e) => D.final[e].heldout), backgroundColor: "#6ea8d1" },
          { label: "On-policy", data: EPS.map((e) => D.final[e].onpol), backgroundColor: "#d4a24c" },
          { label: "Fixed-ref", data: EPS.map((e) => D.final[e].fixed), backgroundColor: "#d45a45" },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { boxWidth: 10, boxHeight: 10, color: muted } },
        },
        scales: {
          x: { grid: { display: false } },
          y: { min: 0.5, max: 1, grid: { color: grid } },
        },
        animation: { duration: 700, easing: "easeOutQuart" },
      },
    });
  }

  function makeWithin(epsKey, canvasId, capId) {
    if (!D.within || !D.within[epsKey]) return;
    const w = D.within[epsKey];
    const cap = document.getElementById(capId);
    if (cap) {
      cap.textContent = `${D.labels[epsKey]} · window ${w.window_id} (${w.n} episodes)`;
    }
    const el = document.getElementById(canvasId);
    if (!el || typeof Chart === "undefined") return;
    new Chart(el, {
      type: "line",
      data: {
        labels: w.siw.map((x) => String(x)),
        datasets: [
          {
            label: "True return",
            data: w.true,
            borderColor: "#3db89a",
            backgroundColor: "#3db89a",
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.2,
          },
          {
            label: "Proxy return",
            data: w.proxy,
            borderColor: "#d45a45",
            backgroundColor: "#d45a45",
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { boxWidth: 10, boxHeight: 10, color: muted } },
          tooltip: {
            backgroundColor: "#1c2430",
            titleColor: ink,
            bodyColor: ink,
          },
        },
        scales: {
          x: {
            title: { display: true, text: "Steps into window (×1000)", color: muted },
            ticks: { maxTicksLimit: 8 },
            grid: { color: grid },
          },
          y: {
            title: { display: true, text: "Episode return", color: muted },
            grid: { color: grid },
          },
        },
        animation: { duration: 700, easing: "easeOutQuart" },
      },
    });
  }

  function makeScatter() {
    if (!D.scatter) return;
    const el = document.getElementById("chart-scatter");
    if (!el || typeof Chart === "undefined") return;
    new Chart(el, {
      type: "scatter",
      data: {
        datasets: EPS.map((e) => ({
          label: D.labels[e],
          data: D.scatter[e].heldout.map((x, i) => ({
            x,
            y: D.scatter[e].true[i],
          })),
          backgroundColor: D.colors[e],
          borderColor: D.colors[e],
          pointRadius: 6,
          pointHoverRadius: 8,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { boxWidth: 10, boxHeight: 10, color: muted } },
          tooltip: {
            callbacks: {
              label(ctx) {
                const e = EPS[ctx.datasetIndex];
                const step = D.scatter[e].step[ctx.dataIndex];
                return `${ctx.dataset.label}: held-out=${ctx.parsed.x.toFixed(3)}, true=${ctx.parsed.y.toFixed(0)} @ ${step}`;
              },
            },
          },
        },
        scales: {
          x: {
            min: 0.45,
            max: 0.95,
            title: { display: true, text: "Held-out preference accuracy", color: muted },
            grid: { color: grid },
          },
          y: {
            title: { display: true, text: "True return (nearby episodes)", color: muted },
            grid: { color: grid },
          },
        },
        animation: { duration: 700, easing: "easeOutQuart" },
      },
    });
  }

  function boot() {
    fillTable();
    fillRawTable("0.0");
    fillReturnsRaw();
    wireRawControls();
    makeLine("chart-true", D.returnCats, lineSeries(D.trueReturn), 0, 1000);
    makeLine("chart-proxy", D.returnCats, lineSeries(D.proxyReturn), 0, 700);
    makeLine("chart-heldout", D.rmSteps, lineSeries(D.heldout, 3), 0.45, 1);
    makeLine("chart-fixed", D.rmSteps, lineSeries(D.fixed, 3), 0.45, 1);
    makeLine("chart-onpolicy", D.rmSteps, lineSeries(D.onpolicy, 3), 0.45, 1);
    makeBars();
    makeWithin("0.0", "chart-within-0", "cap-within-0");
    makeWithin("0.2", "chart-within-2", "cap-within-2");
    makeScatter();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      // Chart.js loaded with defer; wait a tick if needed
      if (typeof Chart !== "undefined") boot();
      else window.addEventListener("load", boot);
    });
  } else if (typeof Chart !== "undefined") {
    boot();
  } else {
    window.addEventListener("load", boot);
  }
})();
