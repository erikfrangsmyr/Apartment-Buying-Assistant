(function () {
  const form = document.getElementById("cost-form");
  const resultEl = document.getElementById("cost-result");
  if (!form) return;

  function fmt(n) {
    return Math.round(n).toLocaleString("sv-SE") + " kr";
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const payload = {
      price: Number(fd.get("price")),
      down_payment: Number(fd.get("down_payment")),
      interest_rate: Number(fd.get("interest_rate")),
      monthly_fee: Number(fd.get("monthly_fee")),
      operating_costs: Number(fd.get("operating_costs")),
    };

    resultEl.hidden = false;
    resultEl.innerHTML = "<p class='muted'>Beräknar…</p>";

    try {
      const res = await fetch("/calculations/monthly-cost", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Beräkning misslyckades");
      const data = await res.json();

      let html = "<h2>Resultat</h2>";
      html += "<dl class='detail-grid'>";
      html += `<dt>Lån</dt><dd>${fmt(data.loan_amount)}</dd>`;
      html += `<dt>Belåningsgrad</dt><dd>${(data.loan_to_value * 100).toFixed(1)} %</dd>`;
      html += `<dt>Ränta/mån</dt><dd>${fmt(data.interest)} (efter avdrag: ${fmt(data.interest_after_deduction)})</dd>`;
      html += `<dt>Amortering/mån</dt><dd>${fmt(data.amortization)} (${data.amortization_rate} %/år)</dd>`;
      html += `<dt>Avgift + drift</dt><dd>${fmt(data.monthly_fee + data.operating_costs)}</dd>`;
      html += `<dt><strong>Total/mån</strong></dt><dd><strong>${fmt(data.total_after_deduction)}</strong> (före avdrag: ${fmt(data.total)})</dd>`;
      html += "</dl>";

      if (data.warnings && data.warnings.length) {
        html += '<div class="flags flag-red"><strong>Varningar</strong><ul>';
        data.warnings.forEach((w) => {
          html += "<li>" + w + "</li>";
        });
        html += "</ul></div>";
      }

      resultEl.innerHTML = html;
    } catch (err) {
      resultEl.innerHTML = "<p class='flag-red'>Kunde inte beräkna månadskostnad.</p>";
    }
  });
})();
