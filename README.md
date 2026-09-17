# ENGIE Particuliers for Home Assistant

Unofficial Home Assistant integration for **ENGIE Particuliers**. It exposes current electricity and gas prices, recent consumption, billing, and can import daily history into the Energy dashboard.

It talks to the same backends as the mobile app through the [`ha-engie-api`](https://pypi.org/project/ha-engie-api/) Python client (`engie_particuliers`). Home Assistant installs that package from PyPI when you add the integration.

This is the French ENGIE Particuliers app, not ENGIE Belgium. Features that only exist in Belgium (EPEX day-ahead, Happy Hours, capacity tariff) are not implemented.

## What you get

One Home Assistant **device per energy contract**:

| Entity | Unit | Energy dashboard |
|--------|------|------------------|
| **Price kWh TTC** | `EUR/kWh` | Use this for *current price* |
| Price kWh HT | `EUR/kWh` | Optional |
| Subscription TTC | `EUR` | Monthly standing charge |
| `{cadran}` price kWh TTC / HT | `EUR/kWh` | BASE / HP / HC when ENGIE reports bands |
| Last day consumption | `kWh` | Latest daily histo row |
| Last day cost TTC | `EUR` | Billed energy cost for that day |

One **account** device:

| Entity | Notes |
|--------|--------|
| Outstanding balance | `soldeApayerV2` |
| Next invoice | Date when ENGIE reports one |
| Last invoice TTC | Amount of `derniereFacture` |
| Authenticated | Diagnostic connectivity sensor |
| Supply cut | Diagnostic, disabled by default |

Daily consumption is also written to **long-term statistics** (`engie:<contract>_energy` and `_cost`) so you can add it under Energy → Gas / Electricity grid consumption.

## Session: login once

You log in **once** (including MFA if ENGIE asks). After that:

1. OAuth access + refresh tokens are saved in Home Assistant storage (`.storage/engie_<entry_id>`)
2. The coordinator refreshes on an interval (default 6 hours)
3. The access token is renewed with the refresh token before it expires — **no MFA on each poll**
4. If ENGIE revokes the refresh token, Home Assistant starts a re-auth flow and you enter the code again

Password is kept on the config entry only as a fallback when the refresh token dies.

## Installation

Copy `custom_components/engie` into your Home Assistant `custom_components` folder, restart, then **Settings → Devices & services → Add integration → ENGIE Particuliers**.

Home Assistant will install `ha-engie-api` automatically from `manifest.json` (`>=0.2.0`).

## Energy dashboard

1. **Settings → Dashboards → Energy**
2. Electricity grid: *Use an entity with the current price* → the **Price kWh TTC** sensor on the electricity contract
3. Gas: same, on the gas contract — your gas energy sensor must be in **kWh** (Gazpar), not m³
4. Optionally pick the imported `engie:…_energy` statistics as the consumption source if you do not already have a local meter

The first poll backfills about 400 days of daily history. To redo it, call the `engie.import_history` service. `engie.clear_import_history` deletes those statistic streams.

HP / HC bands are extra sensors. The Energy dashboard still takes **one** current-price entity; pick the contract-level TTC sensor unless you split peak/off-peak yourself.

## Options

In the integration options you can change the poll interval (seconds, 5 minutes to 24 hours). Default is 6 hours.

## Limitations

- Unofficial API — ENGIE may change it
- Per-cadran HP/HC rates are not always available on every contract
- Gas €/kWh is variable and excludes the standing charge
- History import uses daily `histo*Jours` rows, not Linky half-hours
- Use at your own risk; respect ENGIE terms of service
