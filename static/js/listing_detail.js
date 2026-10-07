(function () {
  const form = document.getElementById("listing-edit-form");
  const editStatus = document.getElementById("edit-status");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const listingId = form.dataset.listingId;
      const fd = new FormData(form);
      const payload = {};
      for (const [key, value] of fd.entries()) {
        const raw = String(value).trim();
        if (key === "interest" && !raw) {
          payload.interest = null;
          continue;
        }
        if (["price", "monthly_fee", "floor"].includes(key)) {
          payload[key] = raw === "" ? null : Number(raw);
          continue;
        }
        if (["rooms", "area_sqm"].includes(key)) {
          payload[key] = raw === "" ? null : parseFloat(raw);
          continue;
        }
        if (key === "url") {
          payload.url = raw || null;
          continue;
        }
        if (key === "notes") {
          payload.notes = raw || null;
          continue;
        }
        payload[key] = raw;
      }
      const saveBtn = document.getElementById("btn-save-listing");
      saveBtn.disabled = true;
      editStatus.hidden = false;
      editStatus.textContent = "Sparar…";
      try {
        const res = await fetch(`/listings/${listingId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || res.statusText);
        }
        editStatus.textContent = "Sparat.";
        window.setTimeout(() => {
          window.location.reload();
        }, 400);
      } catch (err) {
        editStatus.textContent = "Fel: " + (err.message || "kunde inte spara");
      } finally {
        saveBtn.disabled = false;
      }
    });
  }

  const btn = document.getElementById("btn-evaluate");
  const statusEl = document.getElementById("evaluate-status");
  const resultEl = document.getElementById("evaluate-result");
  if (!btn) return;

  const listingId = btn.dataset.listingId;

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function statusClass(st) {
    if (st === "pass") return "status-pass";
    if (st === "fail") return "status-fail";
    return "status-unverified";
  }

  function renderResult(data) {
    const brf = data.brf_assessment;
    let html = '<div class="score-row">';
    html += `<div class="score-box"><div class="value">${Math.round(data.criteria_score)}</div>Kriterier</div>`;
    if (brf) {
      html += `<div class="score-box"><div class="value">${Math.round(brf.economy_score)}</div>BRF</div>`;
    }
    html += "</div>";

    html += `<p><strong>Sammanfattning:</strong> ${esc(data.summary)}</p>`;

    if (data.unverified && data.unverified.length) {
      html += "<p><strong>Ej verifierat:</strong> " + esc(data.unverified.join(", ")) + "</p>";
    }

    if (data.red_flags && data.red_flags.length) {
      html += '<div class="flags flag-red"><strong>Röda flaggor</strong><ul>';
      data.red_flags.forEach((f) => {
        html += "<li>" + esc(f) + "</li>";
      });
      html += "</ul></div>";
    }

    if (brf && brf.green_flags && brf.green_flags.length) {
      html += '<div class="flags flag-green"><strong>Gröna flaggor (BRF)</strong><ul>';
      brf.green_flags.forEach((f) => {
        html += "<li>" + esc(f) + "</li>";
      });
      html += "</ul></div>";
    }

    if (brf && brf.red_flags && brf.red_flags.length) {
      html += '<div class="flags flag-red"><strong>BRF — varningar</strong><ul>';
      brf.red_flags.forEach((f) => {
        html += "<li>" + esc(f) + "</li>";
      });
      html += "</ul></div>";
    }

    if (data.criteria_results && data.criteria_results.length) {
      html += "<h3>Kriterier</h3><table class='criteria-table'><thead><tr>";
      html += "<th>Kriterium</th><th>Typ</th><th>Status</th><th>Detalj</th></tr></thead><tbody>";
      data.criteria_results.forEach((r) => {
        html +=
          "<tr><td>" +
          esc(r.name) +
          "</td><td>" +
          esc(r.kind) +
          "</td><td class='" +
          statusClass(r.status) +
          "'>" +
          esc(r.status) +
          "</td><td>" +
          esc(r.detail || "") +
          "</td></tr>";
      });
      html += "</tbody></table>";
    }

    resultEl.innerHTML = html;
    resultEl.hidden = false;
  }

  btn.addEventListener("click", async () => {
    btn.disabled = true;
    statusEl.hidden = false;
    statusEl.textContent = "Utvärderar…";
    resultEl.hidden = true;

    try {
      const res = await fetch(`/listings/${listingId}/evaluate`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      statusEl.textContent = "";
      statusEl.hidden = true;
      renderResult(data);
    } catch (e) {
      statusEl.textContent = "Fel: " + (e.message || "kunde inte utvärdera");
    } finally {
      btn.disabled = false;
    }
  });
})();
