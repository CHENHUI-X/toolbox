# Libraries Quick-Start Reference

Syntax cheatsheets for the most common visualization libraries. For decision criteria
(which library to pick), see SKILL.md §3.

---

## Python: seaborn

Fast, beautiful defaults, pandas-native. Best default for exploratory Python viz.

```python
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_theme(style="whitegrid", palette="colorblind")

# Bar
sns.barplot(data=df, x="cat", y="val", errorbar=None)

# Line with CI
sns.lineplot(data=df, x="date", y="val", hue="group")

# Scatter
sns.scatterplot(data=df, x="x", y="y", hue="cat", size="weight")

# Histogram with KDE
sns.histplot(data=df, x="val", bins=30, kde=True)

# Box / Violin
sns.boxplot(data=df, x="group", y="val")
sns.violinplot(data=df, x="group", y="val", inner="quart")

# Heatmap
sns.heatmap(corr_matrix, annot=True, cmap="Blues", fmt=".2f")

# Small multiples
g = sns.FacetGrid(df, col="category", col_wrap=3, sharex=True, sharey=True)
g.map(sns.histplot, "value")

# Finishing touches
plt.title("Active title stating the finding", fontsize=14, fontweight="bold")
plt.xlabel("X label (units)")
plt.ylabel("Y label (units)")
sns.despine()
plt.tight_layout()
```

---

## Python: altair (Vega-Lite)

Declarative Grammar of Graphics. Great for quick interactive charts and JSON-first workflows.

```python
import altair as alt

base = alt.Chart(df)

# Bar, sorted descending
(base.mark_bar()
     .encode(
         x=alt.X("category:N", sort="-y"),
         y="value:Q",
         color="group:N",
         tooltip=["category", "value"])
     .properties(title="Active title", width=500, height=300))

# Interactive line
(base.mark_line(point=True)
     .encode(x="date:T", y="value:Q", color="group:N")
     .interactive())

# Scatter with tooltip
base.mark_point().encode(
    x="x:Q", y="y:Q",
    color="cat:N", size="weight:Q",
    tooltip=alt.Tooltip(["x", "y", "cat"]))

# Histogram
base.mark_bar().encode(
    alt.X("value:Q", bin=alt.Bin(maxbins=30)),
    y="count()")

# Heatmap
base.mark_rect().encode(
    x="col_var:O", y="row_var:O",
    color=alt.Color("value:Q", scale=alt.Scale(scheme="blues")))

# Facets, layer, concatenation
chart.facet(facet="category:N", columns=3)
alt.layer(line_chart, scatter_chart)
alt.hconcat(chart1, chart2)

# Brushing + linking
brush = alt.selection_interval()
scatter = base.mark_point().encode(
    x="x:Q", y="y:Q",
    color=alt.condition(brush, "category:N", alt.value("lightgray"))
).add_params(brush)
```

---

## Python: matplotlib

Full control, publication figures. Use when seaborn can't express the layout.

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5))

ax.bar(x, height, color="#0173B2", edgecolor="white")
ax.plot(x, y, linewidth=2, color="#0173B2", label="Group A")
ax.fill_between(x, y_low, y_high, alpha=0.2)  # confidence band
ax.scatter(x, y, c=color_vals, cmap="viridis", s=size_vals, alpha=0.7)
ax.errorbar(x, y, yerr=err, fmt="o", capsize=5)

# Small multiples with shared axes
fig, axes = plt.subplots(2, 3, figsize=(12, 8), sharex=True, sharey=True)

# Styling
ax.set_title("Active title", fontsize=14, fontweight="bold")
ax.set_xlabel("X (units)", fontsize=11)
ax.set_ylabel("Y (units)", fontsize=11)
ax.tick_params(colors="#555555")
ax.spines[["top", "right"]].set_visible(False)  # declutter
ax.grid(axis="y", alpha=0.3)
ax.legend(frameon=False)
plt.tight_layout()
```

---

## Python: Plotly

Interactive charts with minimal code. Hover/zoom/export to HTML. Good for dashboards.

```python
import plotly.express as px
import plotly.graph_objects as go

# Express API (fast)
fig = px.scatter(df, x="x", y="y", color="cat", size="weight",
                 hover_data=["label"], title="Active title")
fig.update_layout(template="plotly_white")
fig.show()

# Graph Objects (full control)
fig = go.Figure()
fig.add_trace(go.Bar(x=cats, y=vals, name="Series 1"))
fig.update_layout(title="Active title", xaxis_title="X", yaxis_title="Y")
```

Plotly Dash for multi-component dashboards: <https://plotly.com/>

---

## Python: Bokeh

Interactive viz with fine-grained widgets. Server apps too.

```python
from bokeh.plotting import figure, show
from bokeh.io import output_notebook

output_notebook()
p = figure(title="Active title", x_axis_label="X", y_axis_label="Y",
           width=600, height=400)
p.circle("x", "y", source=source, size=8, alpha=0.6, color="navy")
show(p)
```

Tutorial: <https://realpython.com/python-data-visualization-bokeh/>

---

## R: ggplot2

Core structure: `ggplot(data, aes(...)) + geom_*() + scale_*() + theme_*()`.
Each `+` adds one component of the Grammar of Graphics.

```r
library(ggplot2)
library(dplyr)

# Bar chart with horizontal flip for readability
ggplot(df, aes(x = reorder(category, value), y = value, fill = group)) +
  geom_col() +
  coord_flip() +
  scale_fill_brewer(palette = "Set2") +
  labs(title = "Active title", x = NULL, y = "Value (units)") +
  theme_minimal()

# Line chart with confidence ribbon
ggplot(df, aes(x = date, y = value, color = group)) +
  geom_ribbon(aes(ymin = lower, ymax = upper, fill = group),
              alpha = 0.2, color = NA) +
  geom_line(linewidth = 1) +
  scale_color_brewer(palette = "Set1") +
  theme_minimal() +
  theme(legend.position = "bottom")

# Scatter + trend line
ggplot(df, aes(x = x, y = y, color = category)) +
  geom_point(alpha = 0.6) +
  geom_smooth(method = "lm", se = TRUE) +
  scale_color_viridis_d() +
  theme_minimal()

# Histogram + density
ggplot(df, aes(x = value, fill = group)) +
  geom_histogram(aes(y = after_stat(density)), bins = 30,
                 alpha = 0.5, position = "identity") +
  geom_density(aes(color = group), linewidth = 1) +
  theme_minimal()

# Violin + box
ggplot(df, aes(x = group, y = value)) +
  geom_violin(fill = "lightblue", alpha = 0.6) +
  geom_boxplot(width = 0.1) +
  theme_minimal()

# Heatmap with labels
ggplot(df, aes(x = col_var, y = row_var, fill = value)) +
  geom_tile() +
  scale_fill_distiller(palette = "Blues", direction = 1) +
  geom_text(aes(label = round(value, 2)), size = 3) +
  theme_minimal()

# Small multiples
ggplot(df, aes(x = x, y = y)) +
  geom_point() +
  facet_wrap(~ category, scales = "fixed")  # shared scales

# Save
ggsave("output.png", dpi = 300, width = 8, height = 5, bg = "white")
```

Useful companions: `ggdist` (uncertainty), `ggalluvial` (Sankey/alluvial),
`ggrepel` (non-overlapping labels), `patchwork` (composing multiple plots).

---

## Vega-Lite (JSON / standalone)

Renders in browsers, embeds in docs, exports from Altair. Pure JSON spec.

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "data": {"url": "data.csv"},
  "mark": "bar",
  "encoding": {
    "x": {"field": "category", "type": "nominal", "sort": "-y"},
    "y": {"field": "value", "type": "quantitative"},
    "color": {"field": "group", "type": "nominal",
              "scale": {"scheme": "tableau10"}},
    "tooltip": [{"field": "category"}, {"field": "value"}]
  },
  "title": "Active title",
  "width": 500,
  "height": 300
}
```

Examples gallery: <https://vega.github.io/vega-lite/examples/>

---

## D3.js

When no library fits. Data-binding DOM for SVG/Canvas. Steep curve but maximal freedom.

### Minimal bar chart skeleton

```js
const data = [5, 10, 15, 20, 25];
const w = 400, h = 200, padding = 20;

const svg = d3.select("body").append("svg")
  .attr("width", w).attr("height", h);

// Scales: domain (data) → range (pixels)
const xScale = d3.scaleBand()
  .domain(data.map((_, i) => i))
  .range([padding, w - padding])
  .padding(0.1);

const yScale = d3.scaleLinear()
  .domain([0, d3.max(data)])
  .range([h - padding, padding]);

// Data join: bind data, enter-append bars
svg.selectAll("rect")
  .data(data)
  .enter().append("rect")
    .attr("x", (_, i) => xScale(i))
    .attr("y", d => yScale(d))
    .attr("width", xScale.bandwidth())
    .attr("height", d => h - padding - yScale(d))
    .attr("fill", "#0173B2");

// Axes
svg.append("g")
  .attr("transform", `translate(0, ${h - padding})`)
  .call(d3.axisBottom(xScale));

svg.append("g")
  .attr("transform", `translate(${padding}, 0)`)
  .call(d3.axisLeft(yScale));
```

### Core concepts (Murray 2017)

- **Selections** — `d3.select`, `d3.selectAll`; the bridge between data and DOM.
- **Data joins** — `.data()` binds; `.enter()` / `.exit()` / `.merge()` handle add/update/remove.
- **Scales** — `scaleLinear`, `scaleBand`, `scaleTime`, `scaleQuantize`, `scaleOrdinal`.
- **Axes** — `d3.axisBottom(scale)`, `.ticks(5)`, `.tickFormat(d3.format(",.0f"))`.
- **Shapes** — `d3.line()`, `d3.area()`, `d3.arc()`, `d3.pie()`, `d3.stack()`, `d3.geoPath()`.
- **Transitions** — `.transition().duration(500).ease(d3.easeCubicInOut)`.
- **Interactions** — `.on("click", ...)`, `.on("mouseover", ...)`; tooltips via SVG `<title>` or HTML div.
- **Geo** — `d3.geoMercator()`, `d3.geoPath()`, topoJSON for compact shapes.

### D3 resources
- Hitchhiker's Guide to D3.js: <https://medium.com/@enjalot/the-hitchhikers-guide-to-d3-js-a8552174733a>
- Observable (Bostock's collection): <https://observablehq.com/@d3>

---

## deck.gl (large / 3D geo)

WebGL-powered, handles millions of points, 2D/3D maps. Works with Mapbox / MapLibre.

- Homepage: <https://deck.gl/>
- Good for: flight-path maps, 3D city density, scatter over satellite imagery.

---

## Interactive SVG/HTML in Chat (`show_widget`)

When building inline artifacts, prefer:
1. **Vega-Lite JSON** for any real chart (it's a full grammar).
2. **Plain SVG** for a simple, bespoke illustration.

Minimal SVG skeleton:

```html
<svg viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
  <!-- Axes -->
  <line x1="60" y1="350" x2="560" y2="350" stroke="#ccc"/>
  <line x1="60" y1="50"  x2="60"  y2="350" stroke="#ccc"/>
  <!-- Bars / data elements here -->
  <!-- Labels -->
  <!-- Title -->
  <text x="300" y="30" text-anchor="middle"
        font-size="16" font-weight="bold">Active title</text>
</svg>
```

Use CSS variables for colors to respect the app's light/dark theme. Keep the
background transparent.
