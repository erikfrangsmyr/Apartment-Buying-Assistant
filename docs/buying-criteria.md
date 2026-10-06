# Buying criteria — Erik & Jenny

Personal requirements for evaluating **bostadsrätter** in the Stockholm area. Used by the Apartment Buying Assistant when scoring listings and comparing neighborhoods.

## Household

- **Buyers:** Erik and Jenny  
- **Commute anchor:** Odenplan (public transport)

## Hard requirements

These are deal-breakers unless explicitly waived for a specific listing.

| Requirement | Target | Notes |
|-------------|--------|--------|
| Living area | ≥ 65 m² | Minimum comfortable size for the household |
| Rooms | ≥ 3 rok | |
| Purchase price | ≤ 3 500 000 SEK | **Flexible** — still saving; possible family loan from relatives |
| Monthly fee (avgift) | ≤ 8 000 SEK | |
| Commute to Odenplan | ≤ 40 min | By public transport; verify per listing |
| Outdoor space | Balcony **or** small patio | At least one |
| Dishwasher | Yes | |
| Washing machine | Yes | In unit or clearly allowed in apartment |
| Daylight / floor | Not a basement apartment | Lots of daylight; avoid basement units |
| External storage | Possible | e.g. föreningsförråd, locker rental — confirm with BRF |

## Soft requirements (weighted)

Nice-to-haves and area qualities. Higher weight = more important when comparing otherwise similar options.

### Apartment features

- Small private backyard (rare in BRF, bonus if available)
- **80+ m²** living area
- Balcony or patio with **south-east** exposure
- Large kitchen
- Open plan between living room and kitchen
- Patio door from **living/kitchen**, not from bedroom
- Two bathrooms
- Space for laundry in at least one bathroom
- Guest apartment in the BRF (värdlägenhet)

### Location & lifestyle

- Child-friendly area
- Good safety reputation (avoid areas with gang/shooting reputation)
- Kindergarten / preschool nearby
- Grocery within easy reach
- Easy access to water and nature
- Close to swimming water (bath / swim spot)

## Neighborhoods of interest

All listed below are in the seed database. **Commute times to Odenplan are placeholders (TBD)** until verified per area.

| Area | Municipality | Notes |
|------|--------------|--------|
| Sickla | Nacka | |
| Järla | Nacka | |
| Finntorp | Nacka | |
| Järlaberg | Nacka | |
| Nacka Forum | Nacka | |
| Nacka Strand | Nacka | |
| Henriksdal | Nacka | |
| Hammarbyhöjden | Stockholm | |
| Björkhagen | Stockholm | |
| Hammarby Sjöstad | Stockholm | |
| Kärrtorp | Stockholm | |
| Blåsut | Stockholm | |
| Enskede | Stockholm | |
| Årsta | Stockholm | |
| Johanneshov | Stockholm | |
| Södermalm | Stockholm | Broad area — narrow per listing |
| Liljeholmskajen | Stockholm | |
| Årstaberg | Stockholm | |
| Aspudden | Stockholm | |
| Alvik | Stockholm | |
| Bromma | Stockholm | |
| Solna | Solna | |
| Sundbyberg | Sundbyberg | |
| Annedal | Stockholm | |
| Mariehäll | Sundbyberg | |

## How this maps to the database

- Table `criteria`: each row is one rule (`kind` = `hard` or `soft`, `weight` 1–5).  
- Table `neighborhoods`: areas above with ratings and commute fields to fill in over time.  
- Listing evaluation (future / manual): match listing fields (`price`, `rooms`, `area_sqm`, `monthly_fee`, feature flags) against `criteria`.

## Sources

Captured from Erik & Jenny’s stated preferences, 2026-10-06.
