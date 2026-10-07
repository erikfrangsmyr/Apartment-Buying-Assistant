(function () {
  const form = document.getElementById("compare-form");
  const resultEl = document.getElementById("compare-result");
  const errorEl = document.getElementById("compare-error");
  if (!form) return;

  const MAX = 4;
  const costDefaults = { interest_rate: 3.5, operating_costs: 800 };

  function selectedIds() {
    return Array.from(form.querySelectorAll('input[name="listing_id"]:checked')).map((el) =>
      Number(el.value)
    );
  }

  function enforceMax(changed) {
    const boxes = Array.from(form.querySelectorAll('input[name="listing_id"]'));
    const checked = boxes.filter((b) => b.checked);
    if (checked.length > MAX) {
      if (changed) changed.checked = false;
      errorEl.hidden = false;
      errorEl.textContent = `Välj högst ${MAX} objekt.`;
    } else {
      errorEl.hidden = true;
    }
  }

  form.querySelectorAll('input[name="listing_id"]').forEach((box) => {
    box.addEventListener("change", () => enforceMax(box));
  });

  function statusClass(status) {
    if (status === "pass") return "status-pass";
    if (status === "fail") return "status-fail";
    return "status-unverified";
  }

  function downPayment(price) {
    if (!price) return 0;
    return Math.round(price * 0.15);
  }

  async function monthlyTotal(listing) {
    const price = listing.price;
    if (price == null) return null;
    const payload = {
      price,
      down_payment: downPayment(price),
      interest_rate: costDefaults.interest_rate,
      monthly_fee: listing.monthly_fee || 0,
      operating_costs: costDefaults.operating_costs,
    };
    const res = await fetch("/calculations/monthly-cost", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.total_after_deduction;
  }

  function criterionByName(evalBody, name) {
    if (!evalBody || !evalBody.criteria_results) return null;
    return evalBody.criteria_results.find((r) => r.name === name) || null;
  }

  function interestDisplay(interest) {
    const map = { love: "❤ Älskar", interested: "👍 Intressant", skip: "👎 Hoppa över" };
    return interest ? map[interest] || interest : "—";
  }

  function buildRows(listing, evalBody, monthly) {
    const crit = (name) => criterionByName(evalBody, name);
    const cell = (status, text, detail) => ({
      status,
      text: text || (status === "pass" ? "✓" : status === "fail" ? "✗" : "?"),
      detail,
    });

    const rows = [];
    const pushCrit = (label, name, display) => {
      const c = crit(name);
      if (c) rows.push({ label, ...cell(c.status, display ?? String(listing[name] ?? "?"), c.detail) });
      else rows.push({ label, ...cell("unverified", display ?? "—") });
    };

    pushCrit("Boarea (m²)", "Minst 65 kvm", listing.area_sqm != null ? String(listing.area_sqm) : "?");
    pushCrit("Rum", "Minst 3 rok", listing.rooms != null ? String(listing.rooms) : "?");
    pushCrit("Pris", "Maxpris 3,5 MSEK", listing.price != null ? listing.price.toLocaleString("sv-SE") + " kr" : "?");
    pushCrit("Avgift/mån", "Avgift högst 8 000 kr/mån", listing.monthly_fee != null ? listing.monthly_fee.toLocaleString("sv-SE") + " kr" : "?");

    const outdoor = crit("Balkong eller uteplats");
    rows.push({
      label: "Balkong/uteplats",
      ...(outdoor ? cell(outdoor.status, outdoor.status === "pass" ? "✓" : outdoor.status === "fail" ? "✗" : "?", outdoor.detail) : cell("unverified", "?")),
    });

    const floorCrit = crit("Inte källarvåning");
    const floorText = listing.floor != null ? String(listing.floor) : "?";
    rows.push({
      label: "Våning",
      ...(floorCrit
        ? cell(floorCrit.status, floorText, floorCrit.detail)
        : cell("unverified", floorText)),
    });

    rows.push({
      label: "Intresse",
      ...cell(listing.interest === "love" ? "pass" : "unverified", interestDisplay(listing.interest)),
    });

    const brf = evalBody && evalBody.brf_assessment;
    if (brf && brf.economy_score != null) {
      rows.push({ label: "BRF-poäng", ...cell("pass", `${Math.round(brf.economy_score)}/100`) });
    } else {
      rows.push({ label: "BRF-poäng", ...cell("unverified", "—") });
    }

    if (monthly != null) {
      rows.push({
        label: "Månadskostnad (ca)",
        ...cell("unverified", monthly.toLocaleString("sv-SE") + " kr/mån"),
      });
    } else {
      rows.push({ label: "Månadskostnad (ca)", ...cell("unverified", "—") });
    }

    return rows;
  }

  function renderTable(listingsData, evals, monthlies) {
    const rowLabels = buildRows(listingsData[0], evals[0], monthlies[0]).map((r) => r.label);
    let html = '<div class="compare-table-wrap"><table class="data-table compare-table"><thead><tr><th>Kriterium</th>';
    listingsData.forEach((l) => {
      html += `<th>${l.address}</th>`;
    });
    html += "</tr></thead><tbody>";

    rowLabels.forEach((label, ri) => {
      html += `<tr><th scope="row">${label}</th>`;
      listingsData.forEach((_, ci) => {
        const rows = buildRows(listingsData[ci], evals[ci], monthlies[ci]);
        const cell = rows[ri];
        const title = cell.detail ? ` title="${cell.detail.replace(/"/g, "&quot;")}"` : "";
        html += `<td class="${statusClass(cell.status)}"${title}>${cell.text}</td>`;
      });
      html += "</tr>";
    });

    html += "</tbody></table></div>";
    if (evals.some((e) => e && e.summary)) {
      html += '<div class="compare-summaries">';
      listingsData.forEach((l, i) => {
        if (evals[i] && evals[i].summary) {
          html += `<p class="muted"><strong>${l.address}:</strong> ${evals[i].summary}</p>`;
        }
      });
      html += "</div>";
    }
    return html;
  }

  async function runCompare() {
    const ids = selectedIds();
    if (ids.length === 0) {
      errorEl.hidden = false;
      errorEl.textContent = "Välj minst ett objekt.";
      resultEl.hidden = true;
      return;
    }
    if (ids.length > MAX) {
      enforceMax(null);
      return;
    }

    const btn = document.getElementById("compare-btn");
    btn.disabled = true;
    errorEl.hidden = true;
    resultEl.hidden = false;
    resultEl.innerHTML = "<p class='muted'>Hämtar utvärderingar…</p>";

    try {
      const listingRes = await fetch("/listings");
      if (!listingRes.ok) throw new Error("Kunde inte läsa objekt");
      const allListings = await listingRes.json();
      const listingsData = ids.map((id) => allListings.find((l) => l.id === id)).filter(Boolean);
      if (listingsData.length !== ids.length) throw new Error("Saknade objekt i databasen");

      const evals = await Promise.all(
        ids.map(async (id) => {
          const res = await fetch(`/listings/${id}/evaluate`, { method: "POST" });
          if (!res.ok) throw new Error(`Utvärdering misslyckades för objekt ${id}`);
          return res.json();
        })
      );

      const monthlies = await Promise.all(listingsData.map((l) => monthlyTotal(l)));

      resultEl.innerHTML = renderTable(listingsData, evals, monthlies);
    } catch (err) {
      resultEl.hidden = true;
      errorEl.hidden = false;
      errorEl.textContent = err.message || "Jämförelse misslyckades.";
    } finally {
      btn.disabled = false;
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    runCompare();
  });

  if (window.COMPARE_AUTO && selectedIds().length > 0) {
    runCompare();
  }
})();
