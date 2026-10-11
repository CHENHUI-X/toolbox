# Color Palettes Reference

Ready-to-use palettes for data visualization. All recommended palettes are
colorblind-tested.

> Core rule (Schwabish, Wilke): **start with gray, add color only where needed.**
> Color is an attention-direction tool, not a decoration.

---

## Matching Palette Family to Data Type

| Data type | Palette family | Examples |
|---|---|---|
| Categorical / nominal | Qualitative | Tableau 10, ColorBrewer Set2, seaborn `colorblind` |
| Ordinal / sequential quantitative | Sequential | Blues, Greens, Viridis, Plasma |
| Quantitative with meaningful midpoint | Diverging | RdBu, PuOr, BrBG |
| Highlight vs. context | Gray + one accent | `#CCCCCC` + single brand color |

Match the **structure of the data** to the **structure of the palette**. Mismatches
(e.g., rainbow on ordinal data) create false categorical boundaries.

---

## Qualitative (Categorical) Palettes

### Colorblind-safe (seaborn default)
```python
palette = "colorblind"
# Hex values:
colors = ["#0173B2", "#DE8F05", "#029E73", "#D55E00", "#CC78BC",
          "#CA9161", "#FBAFE4", "#949494", "#ECE133", "#56B4E9"]
```

### Tableau 10
```
#4E79A7  #F28E2B  #E15759  #76B7B2  #59A14F
#EDC948  #B07AA1  #FF9DA7  #9C755F  #BAB0AC
```

### ColorBrewer Set2 (soft, good for academic)
```
#66C2A5  #FC8D62  #8DA0CB  #E78AC3  #A6D854  #FFD92F  #E5C494  #B3B3B3
```

### For 3–4 categories (matplotlib tab10 subset)
```
#1f77b4  #ff7f0e  #2ca02c  #d62728
```

---

## Sequential Palettes (ordered / magnitude data)

Use a single-hue gradient. Light = small, dark = large (honoring the "dark = more"
schema).

### Blues
```
#EFF3FF  #BDD7E7  #6BAED6  #2171B5  #084594
```

### Greens
```
#EDF8E9  #BAE4B3  #74C476  #31A354  #006D2C
```

### Oranges
```
#FEEDDE  #FDBE85  #FD8D3C  #E6550D  #A63603
```

### Viridis family (perceptually uniform, colorblind-safe, print-safe in grayscale)
```python
import matplotlib.cm as cm
colors = cm.viridis   # or 'plasma', 'inferno', 'magma', 'cividis'
```

These are the default for `matplotlib` imshow and `seaborn` heatmap continuous —
and they should be the default for any quantitative color scale unless you have a
brand reason otherwise.

---

## Diverging Palettes (deviation from a midpoint)

Use only when the data has a meaningful zero or midpoint (change, difference,
anomaly, deviation).

### Red–Blue (RdBu) — ColorBrewer
```
#B2182B  #D6604D  #F4A582  #FDDBC7  #F7F7F7  #D1E5F0  #92C5DE  #4393C3  #2166AC
```

### Purple–Orange (PuOr) — colorblind-safe alternative
```
#7B3294  #C2A5CF  #F7F7F7  #F6B85B  #E66101
```

### Brown–Blue–Green (BrBG)
```
#8C510A  #D8B365  #F6E8C3  #F5F5F5  #C7EACB  #5AB4AC  #01665E
```

### ⚠️ Red–Green is NOT safe
```
# ~6% of men are deuteranopic. Pure red/green diverging palettes are unreadable
# for them. Use Red–Blue or Purple–Orange instead.
```

---

## HUSL Color Space

HUSL gives perceptually uniform hues — useful for generating custom categorical
palettes where every color feels equally "loud."

```python
import seaborn as sns
palette = sns.husl_palette(n_colors=6)
```

Website: <https://husl-colors.org/>

---

## Colorblind Simulation & Testing

Before shipping any color-coded chart, test with:

- **Coblis:** <https://www.color-blindness.com/coblis-color-blindness-simulator/>
- **Viz Palette:** <https://projects.susielu.com/viz-palette>
- **Adobe Color Accessibility:** <https://color.adobe.com/create/color-accessibility>

Most common impairments:
- **Deuteranopia** (green-blind): ~6% of men, ~0.4% of women — confuses red/green.
- **Protanopia** (red-blind): ~1% of men — confuses red/green.
- **Tritanopia** (blue-blind): rare; affects blue/yellow discrimination.

**Safe defaults:** blue + orange, Viridis, ColorBrewer `colorblind` scheme.

---

## Highlighting: Start With Gray

The most underused technique in everyday viz. Schwabish's rule:

1. Plot every series in light gray (`#CCCCCC` or similar).
2. Overlay the one or two series that matter in a saturated accent color.
3. Direct-label the accent series; leave the gray ones unlabeled or faintly labeled.

Effect: the reader's eye lands immediately on the point, and the context is still
present but recedes. Works for line-heavy charts, scatters with outliers, and
faceted comparisons alike.

---

## R Quick Reference

```r
# ColorBrewer in ggplot2
scale_color_brewer(palette = "Set2")      # qualitative
scale_fill_brewer(palette = "Blues")      # sequential
scale_fill_distiller(palette = "RdBu")    # diverging continuous

# Viridis
scale_color_viridis_c()   # continuous
scale_color_viridis_d()   # discrete

# Custom
scale_color_manual(values = c("#0173B2", "#DE8F05", "#029E73"))

# Highlight one group, gray the rest
scale_color_manual(values = c("KeyGroup" = "#D55E00",
                              "OtherA" = "#CCCCCC",
                              "OtherB" = "#CCCCCC"))
```

---

## Python Quick Reference

```python
# seaborn
sns.set_palette("colorblind")
sns.color_palette("Blues", as_cmap=True)     # sequential

# matplotlib
plt.set_cmap("viridis")

# altair
alt.Color("col:N", scale=alt.Scale(scheme="tableau10"))
alt.Color("col:Q", scale=alt.Scale(scheme="blues"))
alt.Color("col:Q", scale=alt.Scale(scheme="redblue",
                                   domainMid=0))  # diverging

# plotly
import plotly.express as px
px.colors.qualitative.Safe       # colorblind-friendly categorical
px.colors.sequential.Viridis
px.colors.diverging.RdBu
```

---

## Further Reading

- ColorBrewer (Cynthia Brewer): <https://colorbrewer2.org/>
- HUSL: <https://husl-colors.org/>
- Wilke, *Fundamentals of Data Visualization*, chapter on color:
  <https://clauswilke.com/dataviz/>
