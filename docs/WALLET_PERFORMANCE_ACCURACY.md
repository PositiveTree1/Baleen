# Wallet performance accuracy and selection

Implemented 2026-09-13. These are screening defaults, not optimized or guaranteed returns.

## Chart source

The Polymarket profile page's `fetchUserPnlSeries` calls
`https://user-pnl-api.polymarket.com/user-pnl` with `user_address`, `interval`,
and `fidelity`. Baleen now preserves its timestamp/value observations. The ALL
series uses daily observations; shorter chart windows request their own series.
The UI no longer cumulatively sums or rebases those values.

Daily bars show changes between observations, not gross winning/losing trades.
The first observation has unknown daily change. It is not assumed to start at
zero. Missing provider data displays as unavailable. Old reconstructed caches
are invalidated; a recent cache with explicit source provenance can be used
when the provider fails. Charts do not replace stored ranking assessments.

The newer [documented v2 PnL endpoint](https://docs.polymarket.com/api-reference/wallet/get-a-users-pnl-series)
exposes several different PnL compositions. It is intentionally not silently
substituted for the profile website's series: that would change the definition.

Live comparison against independently fetched profile observations:

| Wallet | Observations | Exact value matches | Latest profile PnL |
|---|---:|---:|---:|
| 00gringo00 (`0x51698a47f840a242abc2ca0351371c7ffac41842`) | 6 | 6 | $1,946,872.40 |
| wr0ngw4yb3tt0r (`0x224a89dbe0db0d6124b335edabd15b3f877da3d5`) | 102 | 102 | -$4,231,227.50 |
| BreakTheBank (`0xf0318c32136c2db7fec88b84869aee6a1106c80c`) | 235 | 235 | $3,743,617.00 |

This verifies data parity for those observations, not pixel-level browser parity
or the accounting accuracy of Polymarket's upstream feed.

## Outcomes and coverage

- Win rate uses profitable versus losing completed positions, excluding break-even positions.
- Settled, unredeemed positions with an observed cost basis are included, so holding a resolved loser does not hide it. Floating open profits and partial sales are not completed wins.
- Profit factor is gross positive outcome PnL divided by absolute negative outcome PnL. With no observed losses it is undefined, not an invented number or infinity.
- Expectancy is net outcome PnL divided by the number of non-break-even outcomes.
- Zero values survive. No losses are estimated from a discrepancy with a profile total, and monthly leaderboard PnL cannot stand in for lifetime PnL.
- Provider failures, malformed pages, mismatched identities, repeated pages, and history caps cannot be treated as complete histories. Current positions are paginated with a zero size threshold.

References: [closed positions](https://docs.polymarket.com/api-reference/core/get-closed-positions-for-a-user),
[leaderboard contract](https://docs.polymarket.com/api-reference/core/get-trader-leaderboard-rankings).

## Selection policy

Discovery searches ALL, MONTH, and WEEK leaderboards across all 11 documented
categories, alongside the existing recent-trade and market sources. Pages use
the documented maximum of 50 and contiguous offsets. This broadens discovery;
it does not establish that every wallet on the website has been examined.

An assessment needs verified chart/profile evidence, at least 30 completed
outcomes, and 60 daily changes within the past 90 days. It requires positive
lifetime, current cumulative, and recent PnL; positive outcome expectancy;
profit factor of at least 1.25 when defined; and recent activity. It rejects
excessive PnL drawdown, profit concentrated in a single outcome, substantial
open losses, and identified high-frequency/rapid-round-trip activity.

Ranking weights:

| Component | Weight |
|---|---:|
| Payoff after losses (profit factor) | 25% |
| Fraction of profitable weeks | 20% |
| Mean daily dollar PnL relative to its variability | 15% |
| Control of peak-to-trough PnL losses | 15% |
| Completed-outcome sample size | 15% |
| Profit spread across outcomes | 10% |

Dollar-PnL variability is **not** a capital-return Sharpe ratio. The drawdown
percentage is relative to peak cumulative PnL, not portfolio equity; historical
funded capital is not available from this series. Win rate is descriptive,
not an estimate of the probability of winning the next market.

The roster retains category and correlation checks without backfilling rejected
correlated wallets. Capital sets an upper bound: under $250: 1; under $1,000: 2;
under $3,000: 3; under $10,000: 4; $10,000 and above: 5. Zero capital selects none.
These are diversification defaults, not a claim that five wallets are optimal.

Scheduled rescoring now refreshes provider evidence before ranking. The full
assessment is retained with its versioned chart cache, so refreshing the basket
cannot discard profit factor and other risk inputs. Simply opening an unseen
profile creates a pending wallet with unknown metrics, never an active wallet
with made-up scores.

## Rollout and remaining evidence

Deploy the backend and frontend together, then run the normal discovery/rescore
job to replace existing assessments and select the new roster. No production
deployment or live roster mutation was performed by this change.

Before treating these thresholds as a money-making strategy, validate them on
forward paper-copy results with executable entry/exit prices, fees, slippage,
latency, missed fills, and capital constraints. Use time-separated evaluation
and compare against the previous policy; avoid selecting and testing wallets
on the same historical period. Existing per-trade execution/risk gates remain
in force and can reject trades from an otherwise qualified wallet.
