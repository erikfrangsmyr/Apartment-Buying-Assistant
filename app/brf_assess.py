"""Rule-based BRF (bostadsrättsförening) assessment heuristics.

Thresholds align with docs/brf-evaluation-guide.md — tuned for quick pre-bid screening,
not a substitute for reading the full årsredovisning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.models import AssociationAssessRequest, AssociationAssessResponse, RenovationAssessInput

# Debt per kvm (BOA), kr — common industry bands
DEBT_LOW = 5_000
DEBT_NORMAL_HIGH = 10_000
DEBT_HIGH = 12_000
DEBT_VERY_HIGH = 15_000

# Cash buffer: liquid assets vs annual debt service proxy (rough)
MIN_CASH_PER_APARTMENT = 25_000
STRONG_CASH_PER_APARTMENT = 75_000

STAMBYTE_TYPICAL_AGE = 50
OLD_BUILDING_YEAR = 1975

KNOWN_MANAGEMENT = frozenset(
    {
        "hsb",
        "riksbyggen",
        "sbc",
        "rådet",
        "radet",
        "nabo",
        "momentum",
        "newsec",
        "coor",
    }
)


@dataclass
class _ScoreState:
    score: float = 70.0
    red_flags: list[str] = field(default_factory=list)
    green_flags: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)

    def add_red(self, msg: str, penalty: float = 8) -> None:
        self.red_flags.append(msg)
        self.score -= penalty

    def add_green(self, msg: str, bonus: float = 5) -> None:
        self.green_flags.append(msg)
        self.score += bonus

    def ask(self, q: str) -> None:
        if q not in self.questions:
            self.questions.append(q)


def _renovations_by_kind(renovations: list[RenovationAssessInput]) -> dict[str, list[RenovationAssessInput]]:
    out: dict[str, list[RenovationAssessInput]] = {}
    for r in renovations:
        out.setdefault(r.kind, []).append(r)
    return out


def _has_done(renovations: list[RenovationAssessInput], kind: str, after_year: int | None = None) -> bool:
    for r in renovations:
        if r.kind != kind or r.status != "done":
            continue
        if after_year is None or (r.year is not None and r.year >= after_year):
            return True
    return False


def _has_planned(renovations: list[RenovationAssessInput], kind: str) -> bool:
    return any(r.kind == kind and r.status == "planned" for r in renovations)


def assess_brf(req: AssociationAssessRequest) -> AssociationAssessResponse:
    state = _ScoreState()
    current_year = date.today().year
    by_kind = _renovations_by_kind(req.renovations)

    # --- Legal / structure ---
    if req.is_genuine is False:
        state.add_red("Oäkta förening – annan beskattning och sämre villkor vid försäljning.", 25)
        state.ask("Bekräfta i årsredovisningen att föreningen är privatbostadsföretag (äkta).")
    elif req.is_genuine is True:
        state.add_green("Äkta bostadsrättsförening (privatbostadsföretag).", 3)

    if req.owns_land is False:
        state.add_red(
            "Tomträtt (inte äganderätt till marken) – tomträttsavgäld kan omregleras.",
            10,
        )
        state.ask("När sker nästa omreglering av tomträttsavgälden och vad blev den senaste höjningen?")
        if req.tomtratt_fee and req.tomtratt_fee > 500_000:
            state.add_red(f"Hög tomträttsavgäld ({req.tomtratt_fee:,} kr/år) – tryck på avgiften.", 5)
    elif req.owns_land is True:
        state.add_green("Äganderätt till marken – ingen tomträttsavgäld.", 5)

    rental = req.rental_units_count or 0
    if req.only_bostadsratter is False or rental > 0:
        if rental >= 5:
            state.add_red(f"{rental} hyresrätter i föreningen – annan ekonomi och prioritering.", 6)
        elif rental > 0:
            state.add_red(f"{rental} hyresrätt(er) i föreningen – kontrollera stadgar och ekonomi.", 3)
        state.ask("Hur stor andel av fastigheten är hyresrätter/lokaler, och vem äger dem ekonomiskt?")
    elif req.only_bostadsratter is True:
        state.add_green("Enbart bostadsrätter i föreningen.", 2)

    # --- Size ---
    if req.num_apartments is not None:
        n = req.num_apartments
        if n < 15:
            state.add_red(f"Liten förening ({n} lägenheter) – högre kostnad per lägenhet vid större åtgärder.", 5)
            state.ask("Hur delas kostnader vid stora investeringar i en liten förening?")
        elif 15 <= n <= 80:
            state.add_green(f"Lagom storlek ({n} lägenheter) för effektiv förvaltning.", 2)
        elif n > 150:
            state.ask("Finns flera byggnader/entréer – är underhållsplanen uppdelad per hus?")

    # --- Economy: debt ---
    debt = req.debt_per_sqm
    if debt is not None:
        if debt < DEBT_LOW:
            state.add_green(f"Låg skuldsättning ({debt:,} kr/kvm).", 8)
        elif debt <= DEBT_NORMAL_HIGH:
            state.add_green(f"Normal skuldsättning ({debt:,} kr/kvm).", 3)
        elif debt <= DEBT_HIGH:
            state.add_red(f"Hög skuld ({debt:,} kr/kvm) – räntekänslighet och avgiftshöjningar.", 8)
            state.ask("Vad är räntekänsligheten (+1 % ränta) enligt årsredovisningen?")
        elif debt <= DEBT_VERY_HIGH:
            state.add_red(f"Mycket hög skuld ({debt:,} kr/kvm), typiskt nyproduktion eller stora lån.", 12)
            state.ask("Vilken räntebindning har föreningens lån och när förfaller de?")
        else:
            state.add_red(f"Extrem skuldsättning ({debt:,} kr/kvm).", 15)
            state.ask("Finns plan för amortering eller är skulden avsedd att ligga kvar lång tid?")

    # --- Cash vs debt ---
    if req.cash_balance is not None and req.num_apartments:
        per_apt = req.cash_balance / req.num_apartments
        if req.cash_balance < 0:
            state.add_red("Negativt kassa/bank – svag likviditet.", 12)
        elif per_apt < MIN_CASH_PER_APARTMENT:
            state.add_red(f"Lågt kassa ({req.cash_balance:,} kr, ~{int(per_apt):,} kr/lgh).", 6)
            state.ask("Räcker likviditeten till oförutsedda reparationer utan nyupplåning?")
        elif per_apt >= STRONG_CASH_PER_APARTMENT:
            state.add_green(f"Stark kassa ({req.cash_balance:,} kr, ~{int(per_apt):,} kr/lgh).", 6)
        else:
            state.add_green(f"Acceptabel kassa ({req.cash_balance:,} kr).", 2)

    if req.total_debt and req.cash_balance is not None and req.total_debt > 0:
        ratio = req.cash_balance / req.total_debt
        if ratio < 0.02:
            state.add_red("Kassan är under 2 % av total skuld – liten buffert mot räntehöjningar.", 5)
        elif ratio >= 0.10:
            state.add_green("Kassan motsvarar minst 10 % av föreningsskulden.", 4)

    # --- Management ---
    if req.management_brand:
        brand = req.management_brand.strip()
        if brand.lower() in KNOWN_MANAGEMENT:
            state.add_green(f"Etablerad förvaltare: {brand}.", 2)
        else:
            state.ask(f"Vilken erfarenhet har förvaltaren ({brand}) med liknande föreningar?")

    # --- Building age & renovations ---
    built = req.built_year
    needs_stambyte = built is not None and built <= OLD_BUILDING_YEAR
    if needs_stambyte:
        if _has_done(req.renovations, "stambyte"):
            state.add_green("Stambyte genomfört (äldre hus).", 8)
        elif _has_planned(req.renovations, "stambyte"):
            state.add_red("Stambyte planerat – räkna med avgiftshöjning och störning.", 8)
            state.ask("När planeras stambyte och vilken kostnad per kvm/lägenhet är kalkylerad?")
        else:
            age = current_year - built
            if age >= STAMBYTE_TYPICAL_AGE:
                state.add_red(
                    f"Hus från {built} utan noterat stambyte – hög risk för stora kostnader.", 15
                )
            else:
                state.add_red(f"Hus från {built} – kontrollera om stambyte/relining är gjort.", 8)
            state.ask("Är stammar renoverade eller relinade? När och med vilken metod?")

    for kind, label in (
        ("roof", "Tak"),
        ("facade", "Fasad"),
        ("windows", "Fönster"),
        ("elevator", "Hiss"),
    ):
        if _has_planned(req.renovations, kind):
            state.add_red(f"{label} – planerad åtgärd.", 4)
        elif _has_done(req.renovations, kind):
            state.add_green(f"{label} – genomförd åtgärd finns i historiken.", 2)

    if req.planned_works:
        text = req.planned_works.strip()
        if len(text) > 10:
            state.add_red("Planerade/ar kommande större arbeten angivna.", 5)
            state.ask("Vilka planerade arbeten finansieras med lån respektive avgiftshöjning?")

    # Planned without renovation rows
    for kind in ("roof", "facade", "stambyte", "windows"):
        planned = by_kind.get(kind, [])
        if any(r.status == "planned" and r.cost_estimate and r.cost_estimate > 5_000_000 for r in planned):
            state.add_red(f"Stor planerad kostnad för {kind}.", 3)

    if req.notes and "revisor" in req.notes.lower():
        state.ask("Vad säger revisorns berättelse – anmärkningar eller förbehåll?")

    # Default viewing questions
    if not state.questions:
        state.ask("Finns uppdaterad underhållsplan och stämmer avsättningen med planen?")
    state.ask("Har avgiften höjts kraftigt de senaste tre åren – varför?")

    state.score = max(0.0, min(100.0, round(state.score, 1)))

    if state.score >= 75:
        summary = "BRF:en ser ekonomiskt och strukturellt rimlig ut på papperet – verifiera mot årsredovisning och underhållsplan."
    elif state.score >= 55:
        summary = "Blandad bild – inga enskilda röda flaggor behöver stoppa köp, men granska skuld, kassa och planerade åtgärder noggrant."
    elif state.score >= 35:
        summary = "Flera varningssignaler – räkna med högre risk för avgiftshöjningar eller större investeringar."
    else:
        summary = "Svag BRF-indikator – överväg att prioritera andra föreningar om ni inte accepterar hög ekonomisk risk."

    return AssociationAssessResponse(
        economy_score=state.score,
        red_flags=state.red_flags,
        green_flags=state.green_flags,
        summary=summary,
        questions_to_ask=state.questions,
    )
