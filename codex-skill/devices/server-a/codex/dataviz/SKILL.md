---
name: dataviz
description: >
  Expert skill for creating data visualizations — charts, graphs, dashboards, infographics,
  interactive plots, and inline SVG/HTML widgets. Use this skill whenever the user asks to
  visualize data, create a chart or graph, plot a dataset, build a dashboard, explore data
  visually, or asks "how should I display this data?". Also trigger for tool/library
  selection questions (ggplot2, seaborn, altair, matplotlib, Vega-Lite, D3.js, Plotly,
  Bokeh, deck.gl), questions about visual encoding, chart type choice, color palettes,
  Gestalt principles, perception/cognition, chart critique, or fixing a misleading
  chart. Even if the user just pastes a CSV, a table, or a messy dataset and asks
  "what can I do with this?" — use this skill. Covers code-based output (Python, R, JS)
  and inline SVG/HTML artifacts, plus evaluation and storytelling for the final product.
---

# Data Visualization Skill

A comprehensive skill for transforming data into effective, accurate, and beautiful
visualizations. Covers task framing, chart selection, visual encoding, tool
implementation, design principles, storytelling, and evaluation — grounded in the
research tradition of Tufte, Bertin, Mackinlay, Cleveland & McGill, Shneiderman,
Franconeri, Wilke, Knaflic, Schwabish, and Murray.

---

## 1. Start with the Task, Not the Chart

Before writing a single line of code or picking a chart type, work through the
"Why / What / How" triad (the framing used across modern viz pedagogy):

1. **Why** — What is the intent? Exploration, explanation, decision support, or art/communication?
2. **What** — What are the data types? Categorical, ordinal, quantitative, sequential, diverging, temporal, geospatial?
3. **How** — What design choices encode, manipulate, facet, or reduce the data? How will the viz be built and read?

Then narrow down:

- **Audience** — experts/analysts or general public? Adjust complexity and labeling accordingly.
- **Question** — comparison, distribution, correlation, trend, part-to-whole, flow, hierarchy, geography?
- **Output format** — inline SVG/HTML artifact, Python/R code, static image, or interactive dashboard?
- **Tool** — if not specified, infer from context (see §3).

If the user says "visualize this" and pastes data, make a principled choice, show it,
and briefly state the reasoning — don't over-ask.

> **Data transformations shape the message.** Dropping vs. imputing missing values,
> aggregating vs. showing raw points, and absolute counts vs. rates per capita are all
> *design decisions* that change what the chart says. Flag these choices; they are not
> neutral.

---

## 2. Chart Selection Guide

Match the **data relationship** to the right chart family. This table reflects the
consensus across Schwabish, Wilke, and data-to-viz.com.

| Relationship | Best Charts | Avoid |
|---|---|---|
| Comparison (categories) | Bar, Dot plot, Lollipop | Pie (>4 slices), 3D, radar |
| Comparison (over time) | Line, Area, Slope (2 points) | Bar for long time series |
| Distribution (1 group) | Histogram, Density, Strip plot | Pie |
| Distribution (many groups) | Violin, Box plot, Ridgeline, Beeswarm | Overlapping histograms |
| Correlation | Scatter, Bubble, Hex-bin, Heatmap | Line chart |
| Part-to-whole | Stacked bar, Treemap, Waffle, Donut (≤5) | 3D pie, exploded pie |
| Ranking | Sorted bar, Slope, Dumbbell | Unsorted bar |
| Trend | Line, Smoothed line, Sparkline | Bar for continuous x |
| Geospatial | Choropleth (rates!), Dot map, Proportional symbol, Cartogram | 3D maps, raw counts on choropleth |
| Flow / Process | Sankey, Alluvial, Chord | Overloaded network diagrams |
| Hierarchy | Treemap, Sunburst, Icicle | Deep nested pies |
| Multivariate | Small multiples, Parallel coordinates, Scatter-matrix | Single chart with 6+ encodings |
| Uncertainty | Error bars, Confidence bands, Gradient plots, HOPs | Hiding the uncertainty |

**Quick decision heuristic:**
- 1 variable → histogram / density / bar
- 2 vars (cat + num) → bar, box, or strip plot
- 2 vars (num + num) → scatter
- 3+ vars → color/size/shape encoding **or** small multiples (prefer the latter once categories > 3)
- Time + numeric → line
- Geography + numeric → choropleth of *rates*, not counts

For deeper guidance including less common charts (ridgeline, waffle, Sankey, cartogram),
load `references/chart_types.md`.

> **Schwabish's rule of thumb:** *"It's not about showing the least amount of data,
> it's about showing the data that matter most."*

---

## 3. Tool & Library Selection

| Context | Recommended | When |
|---|---|---|
| Python, fast exploratory | **seaborn** | pandas-native, colorblind default, minimal code |
| Python, Grammar of Graphics | **altair** / Vega-Lite | Declarative, interactive, JSON spec |
| Python, full control | **matplotlib** | Publication figures, custom layouts |
| Python, interactive web | **plotly**, **bokeh** | Hover, zoom, dashboards |
| R, grammar of graphics | **ggplot2** (+ **ggdist**, **ggalluvial**) | Layered, elegant, publication-ready |
| Inline SVG/HTML in chat | **plain SVG** or **Vega-Lite JSON** | Quick visual for the conversation |
| Web, fully custom | **D3.js** (Murray 2017 reference) | Unique interactive work; steep curve |
| Web, geo | **deck.gl**, **Leaflet** + D3 | Large or 3D geographic data |
| Dashboards | **Plotly Dash** (Py), **Shiny** (R), **Streamlit** | Multi-chart, interactive apps |
| Static/no-code | SVG artifact via `show_widget` | Quick visual for chat |

**Default behavior:** if the user hasn't specified a language and just wants to see
something → produce an **inline SVG or Vega-Lite artifact** using the `show_widget`
tool. If the user is coding in Python → start with seaborn unless they asked for
interactivity.

---

## 4. Visual Encoding: Grammar of Graphics

Every visualization maps **data attributes** to **visual channels**. This is the
Grammar of Graphics (Wilkinson; popularized by Wickham via ggplot2, also underlying
Altair and Vega-Lite).

### The seven components

| Component | Role | Example |
|---|---|---|
| **Data** | The raw table to plot | `df` |
| **Aesthetics (aes)** | Mappings: which column → which channel | `x = date, y = temp, color = season` |
| **Scales** | How data values translate to visual values | `date → pixel x; temp → pixel y` |
| **Geometries (geom)** | The mark type | points, lines, bars, areas |
| **Statistics (stat)** | Transformations before plotting | binning, smoothing, quantiles |
| **Coordinates** | Coordinate system | Cartesian, polar, geographic |
| **Facets** | Splitting into small multiples | `facet_wrap(~ region)` |

This is why ggplot2 chains with `+` and Altair chains with `.encode(...).properties(...)`:
each step adds one layer of the grammar. Build visualizations *incrementally*, one
component at a time, rather than reaching for a fixed chart template.

### Channel effectiveness ranking

Based on Cleveland & McGill (1984), refined by Mackinlay (1986) and Franconeri et al.
(2021). For **quantitative** data, from highest precision to lowest:

**Position → Length → Angle → Area → Intensity (color saturation / value) → Color hue → Volume**

For **categorical** data: Position → Color hue → Shape → Texture.

**Consequences:**
- Encode the **most important variable** with position (x or y).
- Bars beat pies because length beats angle.
- Bubble size should scale by **area**, not radius: `r = √(value / π)`. Our eyes
  underestimate large circles regardless, so add a size legend.
- Use color only when position is already taken, or to highlight a subset.
- Don't stack multiple encodings on the same variable unless you have an accessibility reason.

### Bertin's visual variables (1967)

Jacques Bertin's foundational list — still useful as a mental checklist of what you
*could* encode with: **position, size, shape, value (luminosity), color (hue and
saturation), orientation, texture**. Match the variable to the *structure* of your data
(nominal, ordinal, quantitative).

### Schemas & expectations (Franconeri et al., 2021)

Viewers rely on learned metaphors. Honor them:
- **Up = more**, down = less
- **Left-to-right = time** (in left-reading cultures)
- **Dark = important / more** (for sequential scales)
- **Red = bad / hot / negative**, blue = good / cool / positive
- **Green = good / natural**, yellow = caution

Violating these schemas is occasionally justified (e.g., keeping a brand palette), but
it *costs* the reader cognitive effort. Most of the time, go with the expectation.

---

## 5. Perception & Cognitive Load

The visual system is powerful but fallible — it relies on statistical regularities and
has hard limits.

### Preattentive attributes

Certain features pop out in parallel, before focused attention kicks in: **color, size,
shape, orientation, enclosure, line width, motion, position**. Use at most one or two
of these to direct attention to the key number or line. A highlighted value in a
gray-on-gray table jumps out; the same number in a rainbow table gets lost.

### Gestalt principles (apply to layout and grouping)

- **Proximity** — group related elements by placing them close together.
- **Similarity** — same color/shape/size implies same category.
- **Enclosure** — a border or background groups elements more strongly than proximity or color.
- **Continuity** — the eye follows smooth lines and aligned edges; align everything on a grid.
- **Closure** — the mind completes broken shapes; leverage this for minimalist marks.
- **Connection** — connected elements are perceived as one unit (stronger than similarity).
- **Figure & ground** — the viewer separates foreground from background; make sure the *data* is figure.
- **Symmetry** — symmetric arrangements are perceived as more stable and grouped.

### Working memory limits

Viewers can compare only ~2–3 items per second, and working memory holds about 4
"chunks." Concrete consequences (Franconeri et al., 2021):

- A 20-bar chart costs ~10 seconds of active comparison work.
- Legends force an eye–memory shift every time the reader looks up a color → **direct-label instead**.
- Highlight or annotate the key differences for the reader instead of making them find them.
- Chunk and summarize rather than showing every datum, unless the dots *are* the point.

### Key takeaways for design

1. Use high-precision channels (position, length) for the most important comparison.
2. Leverage Gestalt and preattentive features deliberately — don't wallpaper with color.
3. Minimize cognitive load: direct labels, pre-computed comparisons, restrained palettes.
4. Design ethically: show patterns, not persuasion.

---

## 6. Five Guidelines for Better Data Visualizations (Schwabish)

A compact checklist every chart should pass:

1. **Show the data.** Let the data be the star. This doesn't mean show *everything* —
   show what *matters*. Highlighting 6 countries in gray-vs-color is more
   informative than a rainbow of 30.
2. **Reduce clutter.** Remove heavy tick marks, borders, 3D effects, redundant gridlines,
   texture fills, overlapping markers. Every pixel that isn't data is a tax on attention.
3. **Integrate graphics and text.** Active titles ("Sales rose 40% in Q3") beat
   descriptive titles ("Sales by Quarter"). Annotations inside the plot area beat
   captions below it. Tell the reader what to see.
4. **Avoid the spaghetti chart.** When you have many series, either (a) highlight the
   ones that matter and gray out the rest, or (b) break into small multiples.
5. **Start with gray.** Default every mark to gray, then add color only where needed
   to direct attention. Color is a scarce resource, not a default.

---

## 7. Color: Using It Well

Color is the encoding most often misused. Three palette families, each for a different
data shape:

- **Qualitative (categorical):** ColorBrewer Set2, Tableau 10, seaborn `colorblind`, HUSL.
  Keep to ≤ 8 distinct colors; beyond that, use shape/position instead.
- **Sequential (ordered):** single-hue gradient (light → dark). Blues, Greens, Oranges,
  Viridis/Plasma (perceptually uniform, colorblind-safe).
- **Diverging (midpoint):** two-hue gradient through neutral (RdBu, PuOr, BrBG).
  Use only when there is a *meaningful zero* (change, difference, deviation).

### Rules

- Always test for colorblind accessibility. ~6% of men are deuteranopic (green-blind),
  ~1% protanopic (red-blind). **Avoid pure red/green pairs.**
- Never use rainbow / jet for quantitative data — it is not perceptually uniform and
  creates false boundaries.
- For highlighting, start gray and use one saturated color for the series of interest.
- Darker/saturated = more important. Muted/gray = context.
- Keep brand colors for accents, not the entire data layer.

### Accessibility

- Minimum text contrast WCAG AA: 4.5:1 for text, 3:1 for large text / graphical elements.
- Encode category with shape *and* color when possible.
- Test with a colorblind simulator (Coblis, Viz Palette).

For palette hex codes and library syntax, load `references/color_palettes.md`.

---

## 8. Avoid Misleading Practices

- **Proportional ink** (Bergstrom & West): the amount of ink used to represent a value
  must be proportional to the value. Trimmed-but-unlabeled bar bases, pictogram
  cheating, and 3D depth all violate this.
- **No truncated axes on bar charts.** Bars encode *length*, so a broken baseline lies
  about ratios. Line charts may break the y-axis if justified and clearly labeled.
- **Dual y-axes** imply correlation that may not exist. Use only when intentional,
  labeled, and both axes are unambiguously tied to specific series.
- **3D charts distort perception** (tilt angle bias); avoid them except for genuinely
  3D data.
- **Choropleths of raw counts** overweight large/populous regions — use rates per capita
  or per area.
- **Cherry-picked time ranges / y-ranges** inflate or hide trends — always ask whether
  the range tells the honest story.
- **Tufte's Lie Factor** = (size of effect shown in graphic) / (size of effect in data).
  Aim for ~1.
- **Show uncertainty** when it exists — confidence intervals, error bars, gradient
  plots, or hypothetical outcome plots. Silently hiding uncertainty is a lie of omission.

---

## 9. Interaction & Storytelling

Modern visualization leans heavily on interaction for exploration and narrative for
explanation.

### Shneiderman's Visual Information-Seeking Mantra (1996)

> **Overview first, zoom and filter, then details on demand.**

The gold-standard pattern for any interactive viz: let readers see the whole, then
drill in. Tooltips, brushing, linked views, and progressive disclosure all serve this.

### Common interaction patterns

- **Zoom / pan** — for large or dense datasets.
- **Filter / subset** — slider, dropdown, or toggle to narrow the scope.
- **Highlight / brush** — select a region in one view, see it highlighted in others.
- **Tooltip** — details on demand for a single mark.
- **Linked views** — small-multiple dashboards with shared selection state.
- **Animated transitions** — help the eye follow changes between states.

### Storytelling structures (Knaflic)

1. **Understand the context** — audience, setting, desired action.
2. **Choose an appropriate display** (see §2).
3. **Eliminate clutter, but not too much** (see §6).
4. **Draw attention where you want it** — preattentive color, bold annotation.
5. **Think like a designer** — the viz must be easy for *this* audience.
6. **Tell a story** — try the **Martini-glass** structure: start with a guided narrative,
   end with free exploration. Lead with the insight; then show the evidence. Use the
   **Five Ws** (who, what, when, where, why).

### Exemplars to study (interactive storytelling)

- **NYT "Coronavirus in the U.S."** — live dashboard with overview → filter → detail.
- **NYT interactive pieces broadly** — annotation-first narrative, scrollytelling.
- **Pudding "Crowdsourcing the Definition of Punk"** — reader becomes data.
- **NZZ "So gefährlich ist Ihre Veloroute"** — map + personal route + risk encoding.
- **Information is Beautiful "Snake Oil"** — interactive bubble chart with evidence strength on y.

Use these as reference calibrations when a user asks for "something like the New York
Times" — the common thread is: one clear question, one clear answer, plenty of
annotation, restrained palette, and a generous amount of white space.

---

## 10. Implementation Workflow

### For code output (Python / R)

```
1. Load & inspect data (shape, dtypes, nulls, ranges)
2. Clean & transform (melt, pivot, aggregate, normalize) — flag the choices
3. Choose chart type (§2)
4. Write minimal working code with chosen library (§3)
5. Apply design principles (§5–§8): labels, restrained color, declutter
6. Add an active title + axis labels with units + source/data credit
7. Add alt-text for accessibility
```

**Every chart ships with:**
- An **active title** ("Germany's schooling grew fastest") beats descriptive ("Years of schooling by country").
- Axis labels with **units**.
- Source / data credit when applicable.
- An **alt-text** description of the finding (for screen readers).

### For inline SVG / HTML artifacts

Use `show_widget` with clean SVG or HTML+JS. Follow the frontend-design skill for
styling. For complex chart-specific SVG patterns, load
`references/chart_types.md`.

Default to Vega-Lite JSON for anything beyond a very simple bar/line chart — it's
declarative, honors the Grammar of Graphics, and renders inline.

### For D3.js (custom web viz)

D3 binds data to DOM/SVG elements and gives you full control. Key concepts (Murray 2017):

- **Selections** (`d3.select`, `d3.selectAll`) — the bridge between data and DOM.
- **Data joins** (`.data().enter().append()`, with `.merge()` and `.exit()`) — add / update / remove marks as data changes.
- **Scales** (`d3.scaleLinear`, `scaleBand`, `scaleTime`, `scaleQuantize`) — map data domain → pixel range.
- **Axes** (`d3.axisBottom(xScale)`) — auto-generate tick marks and labels from scales.
- **Transitions** (`.transition().duration(500)`) — animate between states.
- **Shapes** (`d3.line`, `d3.area`, `d3.arc`, `d3.pie`, `d3.stack`) — path generators.
- **Geo** (`d3.geoPath`, `d3.geoMercator`) — projections and cartography.

Use D3 when no off-the-shelf library meets the design; otherwise prefer Vega-Lite, Plotly, or Observable.

---

## 11. Code Templates

### Python – seaborn bar chart (colorblind palette, decluttered)

```python
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_theme(style="whitegrid", palette="colorblind")
fig, ax = plt.subplots(figsize=(8, 5))
sns.barplot(data=df, x="category", y="value", ax=ax)
ax.set_title("Active title stating the finding", fontsize=14, fontweight="bold")
ax.set_xlabel("Category")
ax.set_ylabel("Value (units)")
sns.despine()
plt.tight_layout()
plt.show()
```

### Python – altair scatter with tooltip

```python
import altair as alt

chart = (
    alt.Chart(df)
    .mark_point()
    .encode(
        x=alt.X("x_col:Q", title="X label (units)"),
        y=alt.Y("y_col:Q", title="Y label (units)"),
        color=alt.Color("category:N", scale=alt.Scale(scheme="tableau10")),
        tooltip=["x_col", "y_col", "category"],
    )
    .properties(title="Active title", width=500, height=350)
    .interactive()
)
chart
```

### R – ggplot2 line chart with confidence band

```r
library(ggplot2)

ggplot(df, aes(x = date, y = value, color = group, fill = group)) +
  geom_ribbon(aes(ymin = lower, ymax = upper), alpha = 0.2, color = NA) +
  geom_line(linewidth = 1) +
  scale_color_brewer(palette = "Set1") +
  scale_fill_brewer(palette = "Set1") +
  labs(
    title = "Active title",
    x = "Date", y = "Value (units)",
    color = "Group", fill = "Group",
    caption = "Source: ..."
  ) +
  theme_minimal(base_size = 12) +
  theme(legend.position = "bottom")
```

### Vega-Lite – minimal bar chart (inline artifact)

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "data": {"values": []},
  "mark": "bar",
  "encoding": {
    "x": {"field": "category", "type": "nominal", "sort": "-y"},
    "y": {"field": "value", "type": "quantitative"},
    "tooltip": [{"field": "category"}, {"field": "value"}]
  },
  "title": "Active title"
}
```

### D3 – scale + axis skeleton

```js
const xScale = d3.scaleLinear()
  .domain([0, d3.max(data, d => d.value)])
  .range([padding, width - padding]);

const xAxis = d3.axisBottom(xScale).ticks(5);

svg.append("g")
  .attr("class", "axis")
  .attr("transform", `translate(0, ${height - padding})`)
  .call(xAxis);
```

For fuller syntax across ggplot2 / seaborn / altair / matplotlib / Vega-Lite / D3,
load `references/libraries.md`.

---

## 12. Evaluation: Does the Chart Work?

Don't ship a chart without evaluating it. Three complementary methods:

### (a) Heuristic evaluation (fast, no participants — Forsell & Johansson, 2010)

Run this 10-point checklist on the chart:

1. **Information coding** — does the visual encoding match the data?
2. **Minimal actions** — can the reader reach their goal with minimal effort?
3. **Flexibility** — multiple ways to achieve a goal (where relevant)?
4. **Orientation & help** — can users navigate and recover from mistakes?
5. **Spatial organization** — is the layout easy to read?
6. **Consistency** — are similar things presented similarly?
7. **Recognition over recall** — are options visible, or must users remember them?
8. **Prompting** — are available actions clear?
9. **Remove the extraneous** — is there unnecessary visual noise?
10. **Dataset reduction** — can users filter / simplify effectively?

### (b) User observation / think-aloud (Preece, Sharp & Rogers)

Ask representative users to perform real tasks while verbalizing their reasoning.
You will measure:
- **Performance** — accuracy, time, errors
- **Comprehension** — do they arrive at the intended insight?
- **Judgment** — do they trust the chart? Do they prefer it?

Methods include think-aloud, screen recording, structured interviews, post-task
questionnaires, and — for deeper work — eye-tracking.

### (c) Controlled experiments (summative)

A/B test two designs on a defined task. Measure accuracy and response time. Use a
standardized usability instrument (e.g., SUS) when relevant.

### Quick pre-flight checklist

Before presenting any viz, verify:

- [ ] Chart type matches the data relationship (§2).
- [ ] The most important variable is encoded with position.
- [ ] Palette is colorblind-friendly and appropriate (qualitative / sequential / diverging).
- [ ] Axes start at zero (bar charts), or the break is justified and clearly marked.
- [ ] Title states the **finding**, not just the data.
- [ ] Direct labels beat legends where possible.
- [ ] No 3D, no truncated bar baselines, no unjustified dual axes.
- [ ] Uncertainty shown if the data has it.
- [ ] Works at small size (thumbnail legibility).
- [ ] Alt-text describes the insight, not the mechanics.

---

## 13. Working with AI-Generated Visualizations

When helping someone use an AI (including this skill) to build a chart, be honest
about what AI does well and what still needs human judgment.

**AI is good at:** generating boilerplate chart code, modifying existing code,
suggesting alternative chart types, producing titles or captions for simple viz,
writing code templates across libraries.

**Human judgment is still needed for:** identifying the right question from domain
context, choosing visual encodings that match the analytical task, aesthetic and
brand decisions, evaluating whether a chart is truthful and unbiased, ensuring
accessibility, and shaping the narrative. AI can confidently produce misleading or
aesthetically poor charts; understanding the principles above is how you *critically
evaluate, fix, and direct* AI-generated visuals. (Echoing Tukey: visualizations are
analytical instruments, not just outputs.)

---

## 14. Reference Files

Load these when you need more detail:

- `references/chart_types.md` — Deep guide for 25+ chart types with SVG patterns,
  use cases, pitfalls.
- `references/color_palettes.md` — Hex codes for ColorBrewer, HUSL, seaborn palettes;
  colorblind-safe combinations; library syntax.
- `references/libraries.md` — Quick-start syntax for ggplot2, seaborn, altair,
  matplotlib, Vega-Lite, D3.js, plus Bokeh/Plotly links.

**Load the relevant reference file when:**
- The user asks for a less common chart type (Sankey, ridgeline, waffle, cartogram).
- Color selection is central to the task.
- The user wants syntax for a specific library not in §11.

---

## 15. Theoretical Foundations (for attribution & deep dives)

This skill distills ideas from:

- **Bertin, J. (1967)** — *Semiology of Graphics*. Visual variables.
- **Tufte, E. (1983)** — *The Visual Display of Quantitative Information*. Lie Factor, data-ink ratio, "above all else show the data."
- **Cleveland & McGill (1984)** / **Mackinlay (1986)** — Perceptual channel rankings.
- **Wilkinson, L. (1999)** / **Wickham, H. (2010)** — Grammar of Graphics.
- **Shneiderman, B. (1996)** — "The Eyes Have It." Overview → zoom & filter → details.
- **Ware, C. (2020)** — *Information Visualization: Perception for Design*.
- **Wilke, C. O. (2019)** — *Fundamentals of Data Visualization*.
- **Franconeri, S. et al. (2021)** — *The Science of Visual Data Communication*.
- **Knaflic, C. N. (2015)** — *Storytelling with Data*.
- **Schwabish, J. (2021)** — *Better Data Visualizations*. Five guidelines.
- **Murray, S. (2017)** — *Interactive Data Visualization for the Web with D3*.
- **Preece, Sharp & Rogers (2019)** — *Interaction Design*. Usability and evaluation.
- **Bergstrom & West (2020)** — *Calling Bullshit*. Misleading practices.
- **Forsell & Johansson (2010)** — Heuristics for visualization evaluation.

For open datasets to practice with: Kaggle, Awesome Public Datasets (GitHub),
Makeover Monday, Opendata.swiss, OECD Data, World Bank Data360.
