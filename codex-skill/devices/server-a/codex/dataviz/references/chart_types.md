# Chart Types Reference

Detailed guide for 25+ chart types — when to use, pitfalls, implementation notes.
Synthesized from Schwabish (2021), Wilke (2019), Murray (2017), and data-to-viz.com.

---

## Bar Charts

**Use for:** comparing values across discrete categories.

**Rules:**
- Always start y-axis at 0 — bars encode length, so a broken baseline lies about ratios.
- Sort bars by value unless order has semantic meaning (time, ordinal category).
- Horizontal bars preferred for many categories (> 6) or long labels.
- Avoid grouped bars with > 3 groups — use small multiples instead.
- Direct-label the value at the bar end; remove or mute the axis.

**Variants:**
- **Grouped bar** — 2–3 groups per category.
- **Stacked bar** — part-to-whole; avoid > 3 segments.
- **100% stacked bar** — composition comparison only (not absolute values).
- **Lollipop** — cleaner alternative for sparse data; a line + dot.
- **Dumbbell (dot-plot pair)** — change between two time points.
- **Paired bar** — before/after, actual/target.

**Pitfall:** truncated y-axis exaggerates differences — always start at 0.

---

## Line Charts

**Use for:** trends over continuous data, usually time.

**Rules:**
- Connect only when x is truly continuous.
- ≤ 5 lines per chart — beyond that, use small multiples or highlight-gray.
- Label lines directly at the end; avoid legend lookup.
- Use smoothing (loess, `geom_smooth`) for noisy data; show the raw points too when space allows.
- Non-zero y-axis is acceptable for line charts (unlike bar) but must be justified.

**Variants:**
- **Area chart** — emphasizes volume/magnitude beneath the line.
- **Stacked area** — part-to-whole over time; hard to read middle segments.
- **Streamgraph** — symmetric stacked area; evocative but less precise.
- **Sparkline** — inline mini-chart, trend only, no axes.
- **Cycle plot** — seasonal pattern made explicit.
- **Slope chart** — ranking/change between exactly two time points.

---

## Scatter Plots

**Use for:** correlation / relationship between two numeric variables.

**Rules:**
- Add a trend line (linear or loess) when correlation is the story.
- Use transparency (`alpha`) for overplotting; switch to hex-bins or contour plots above ~10k points.
- Label outliers directly.
- Bubble chart = scatter + size encoding (3rd var); size legend is mandatory.

**Pitfall:** correlation ≠ causation — don't imply it in the title.

---

## Histograms & Distributions

- **Histogram** — distribution of one numeric variable. Try multiple bin widths
  (Sturges, Freedman–Diaconis). Start with `bins = 30`.
- **Density plot (KDE)** — smoothed alternative; better for overlapping groups.
- **Box plot** — summary statistics (median, IQR, outliers). Great for comparing
  distributions across groups; hides bimodality.
- **Violin plot** — box plot + density; better than box for multi-modal distributions.
- **Ridgeline plot** (`ggridges` in R, `joypy` in Python) — overlapping densities
  for many groups; great for temporal or ordinal comparisons.
- **Strip / jitter plot** — every data point on a single axis; honest about sample size.
- **Beeswarm** — strip plot with non-overlapping jitter; shape reveals density.

---

## Pie & Donut Charts

**Use for:** part-to-whole, when ≤ 5 slices and the total is meaningful.

**Rules:**
- Maximum 5 slices; aggregate the rest as "Other".
- Order slices by size, starting at 12 o'clock.
- Label slices directly with the percentage.
- Donut charts have a slight edge: the center can hold a summary number.

**Pitfall:** humans are poor at judging angles. Bar beats pie whenever precision matters.
Tufte: "Pie charts are useless." That's overstated, but use them sparingly.

---

## Heatmaps

**Use for:** matrix data, correlation matrices, calendar data, geographic grids.

**Rules:**
- Sequential palette for single-direction data (white → dark blue).
- Diverging palette when data has a meaningful midpoint (red → white → blue).
- Annotate cells with values when precision matters.
- Cluster rows/columns by similarity (hierarchical clustering) when the ordering
  is not semantically fixed.

---

## Treemaps

**Use for:** hierarchical part-to-whole data.

**Rules:**
- Area encodes magnitude — scale correctly.
- Avoid when hierarchy depth > 2 levels.
- Add color as a second variable (e.g., performance vs. size).

---

## Slope Charts

**Use for:** change between exactly two time points for multiple categories.

**Construction:** two vertical axes (before / after), lines connecting category values.

**Prefer over bar when:** direction and relative ranking of change is the story.

---

## Bubble Charts

**Use for:** three numeric variables (x, y, size) + optional color (4th variable).

**Rules:**
- Scale bubble **area** by value (not radius): `r = √(value / π)`.
- Avoid > 30 bubbles; drop to scatter or hex-bin.
- Legend must explain the size scale.

---

## Sankey / Alluvial Diagrams

**Use for:** flows between categories — survey responses, migration, budget allocation.

**Libraries:** `ggalluvial` (R), `plotly` Sankey (Python), D3 Sankey plugin.

**Pitfall:** hard to read with many nodes; aggregate small flows.

---

## Choropleth Maps

**Use for:** geographic distribution of a variable.

**Rules:**
- Use **rates (per capita)** not raw counts when regions vary in population.
- Sequential or diverging palette — never rainbow/jet.
- Add a legend with clear breakpoints; equal-interval, quantile, and Jenks each tell different stories.
- Consider a **cartogram** when area distorts perception (small populous regions disappear).

**Classics:**
- **Snow's 1854 cholera map** — first great use of a dot map for causal inference.
- **Minard's 1869 Napoleon map** — integrates geography, time, temperature, and troop size.

---

## Small Multiples (Facets)

**Use for:** comparing the same chart across categories or time periods.

**Rules:**
- Keep the same scale across all facets (shared axes).
- Order facets meaningfully (by value, time, geography).
- Use `facet_wrap()` in ggplot2, `alt.facet()` in Altair, `col`/`row` in seaborn.

**When to use:** whenever you have > 3 groups that would create a cluttered single chart.

---

## Dashboard Layouts

A dashboard is a coordinated set of visualizations for monitoring or exploration.

**Rules:**
- **Overview first** — the most important metric above the fold.
- **Alignment & grid** — consistent column widths, gutter spacing (Gestalt continuity).
- **Consistent chart types** — don't mix 10 styles on one screen.
- **Linked views** — selection in one chart filters the others.
- **Progressive disclosure** — details in a drill-down panel, not upfront.

---

## Uncertainty Visualization

Always show uncertainty when the data has it:

- **Error bars** — ±1 SD or 95% CI.
- **Confidence bands** — around trend lines or forecasts.
- **Gradient plots / fan charts** — opacity proportional to confidence.
- **Hypothetical outcome plots (HOPs)** — animated scenarios drawn from the distribution.
- **Quantile dotplots** — discrete dots representing probability mass.

Libraries: `ggdist` (R), `matplotlib` errorbar / fill_between, Altair `mark_errorband`.

---

## Less Common Chart Types

- **Parallel coordinates** — compare many numeric variables per observation; brush to filter.
- **Radar / spider** — categorical comparison across a few axes; polar bar is often better.
- **Waffle chart** — part-to-whole with countable squares; friendlier than pie for small totals.
- **Chord diagram** — pairwise flow between categories (who talks to whom).
- **Network / force-directed graph** — nodes and edges; layout matters enormously.
- **Tree / dendrogram** — hierarchy; use when depth is the story.

---

## Accessibility Patterns

- Always provide alt text describing chart **findings**, not mechanics.
- Use shape + color (not color alone) for categorical encoding.
- Test with a colorblind simulator (Coblis, Viz Palette).
- Minimum font size 11pt for labels, larger for projection/mobile.
- High contrast (WCAG AA: 4.5:1 ratio for text, 3:1 for graphical elements).
- For interactive charts: keyboard navigation, ARIA labels, and a data-table fallback.

---

## Canon to Study

Worth opening and dissecting as reference work:

- **NYT "Coronavirus in the U.S."** — live dashboard, overview → filter → detail.
- **NYT world demographics interactive (2023)** — scrollytelling with shared data layer.
- **Pudding "Crowdsourcing the Definition of Punk"** — reader-as-data.
- **NZZ "So gefährlich ist Ihre Veloroute"** — personal map + risk overlay.
- **Information is Beautiful "Snake Oil"** — bubble chart with evidence axis.
- **Observable collections** — zoomable circle packing, brushable scatterplot matrix, sankey.
- **Kontinentalist** — Asia-focused data storytelling, excellent annotations.

These are reference calibrations for "production quality" when a user asks for a
chart in the style of the NYT, FT, or *The Pudding*.
