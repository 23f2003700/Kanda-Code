# Project timeline

Each date below can be traced to a document or a recorded event, shown in the Source column. Where we have no record of exactly when something happened, we say so rather than guess.

| Date | What happened | Source |
|---|---|---|
| **23 Oct 2026** | Project proposal submitted for topic approval: the sell-or-store question, hypotheses H1–H3, a five-step method (prepare data → EDA and H1 → forecast → optimise → validate) and the team plan. | [`docs/Project_Proposal.pdf`](docs/Project_Proposal.pdf), dated 23 Oct 2026 |
| 23 Oct – 11 Nov 2026 | Main build, split into the five workstreams of the proposal, each with one lead and one reviewer (see the table below). | Proposal §9; work done outside this repository |
| **11 Nov 2026** | Complete project committed to this repository: data, analysis pipeline, Excel Solver model, notebook, report, presentation and contribution sheet. | First commit, 11 Nov 2026 14:54 IST |
| **11 Nov 2026** | Release **v1.0 · final submission** published. It ships the 113 MB raw dataset as a release asset. | [Release v1.0](https://github.com/23f2003700/Kanda-Code/releases/tag/v1.0) |
| **22 Nov 2026** | All-India robustness check: the same model, unchanged, rerun on 118 markets in 15 states. | Commit "All-India robustness check of the sell-or-store method" |
| **22 Nov 2026** | Report, README, methodology and classic deck updated with the all-India result. The report's problem statement now names the rerun. | Commits "Add all-India check…" and "Report: problem statement…" |
| **22 Nov 2026** | Viva presentation site built (15 animated slides, per-speaker script) and published at the GitHub Pages root. The original deck moved to `/classic`. | Commit "Viva deck…" |

## Who led what

All five members contributed equally (20% each; see [`submission/Kanda_Code_Individual_Contribution.xlsx`](submission/Kanda_Code_Individual_Contribution.xlsx)).

| Member | Leads | Reviews |
|---|---|---|
| Raghuram Devarayi | Data: acquisition, cleaning, Lasalgaon validation, data dictionary | Optimisation |
| Parashmani Datta | EDA and H1 regression | Data |
| Kathan Desai | Price forecasting: model selection, validation and test | EDA and H1 |
| Aaryan Choudhary | Optimisation: LP (PuLP and Excel Solver), backtest; coordination | Forecasting |
| Yash Arabhavi | Industry 4.0 valuation, sensitivity, implications, report editing | Report |

## How to read the commit history

The work before 11 Nov 2026 happened outside this repository. It was committed in one piece on 11 Nov. That commit was later split into seven commits, one per part of the project (setup, data, analysis pipeline, Excel and notebook, report, presentation, README). All seven keep the original 11 Nov 2026 timestamp, so their dates say when each part was committed here, not when it was first written. Each commit after them carries the time it was actually made.
