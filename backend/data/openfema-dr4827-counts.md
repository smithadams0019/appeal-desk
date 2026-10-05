# OpenFEMA DR-4827 pull, 2026-10-04T14:55:03Z
Endpoint: https://www.fema.gov/api/open/v2/IndividualsAndHouseholdsProgramValidRegistrations (US government data, public domain)

| filter | count |
|---|---|
| `disasterNumber eq 4827` | 282711 |
| `disasterNumber eq 4827 and ihpEligible eq false` | 121666 |
| `disasterNumber eq 4827 and ihpEligible eq false and ineligibleReason eq '1'` | 15560 |
| `disasterNumber eq 4827 and ihpEligible eq false and ineligibleReason eq '2'` | 20861 |
| `disasterNumber eq 4827 and ihpEligible eq false and ineligibleReason eq '3'` | 22087 |
| `disasterNumber eq 4827 and ihpEligible eq false and ineligibleReason eq '4'` | 7260 |
| `disasterNumber eq 4827 and ihpEligible eq false and ineligibleReason eq '5'` | 712 |
| `disasterNumber eq 4827 and ihpEligible eq false and ineligibleReason eq '7'` | 434 |
| `disasterNumber eq 4827 and ihpEligible eq false and ineligibleReason eq '8'` | 80 |
| `disasterNumber eq 4827 and ihpEligible eq false and ineligibleReason eq '9'` | 4387 |
| `disasterNumber eq 4827 and ihpEligible eq true` | 161045 |

## Ownership/occupancy verification (owners, DR-4827)
| filter | count |
|---|---|
| `disasterNumber eq 4827 and ownRent eq 'O'` | 169174 |
| `disasterNumber eq 4827 and ownRent eq 'O' and verifiedOwnership eq false` | 37129 |
| `disasterNumber eq 4827 and verifiedOccupancy eq false` | 19558 |
| `disasterNumber eq 4827 and ineligibleReason eq '4' and ownRent eq 'O'` | 2480 |
| `disasterNumber eq 4827 and accessFunctionalNeeds eq true and ihpEligible eq false` | 27481 |
