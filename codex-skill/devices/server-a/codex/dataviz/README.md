# Data Visualization Skill 📊

An expert agent skill for creating beautiful, accurate, and effective data visualizations. 

This skill is designed for AI agents (like Gemini CLI, Claude Code, Cursor, etc.) to help them transform raw data into insights using the best visualization practices.

## Features

- **Expert Chart Selection**: Automatically chooses the best chart type based on data relationships (Comparison, Distribution, Correlation, etc.).
- **Multi-Library Support**: Proficient in `seaborn`, `matplotlib`, `altair` (Python), `ggplot2` (R), and `D3.js`/`SVG` for inline artifacts.
- **Design Principles**: Applies Gestalt principles, ColorBrewer accessible palettes, and high data-to-ink ratio standards.
- **Context-Aware**: Understands when to use interactive dashboards versus static publication-quality figures.

## Installation

You can install this skill into your local AI agents using [skills.sh](https://skills.sh):

```bash
npx skills add mikeandrusyak/dataviz-skill
```

## Structure

- `SKILL.md`: Core instructions and metadata for AI agents.
- `references/`: Detailed guides for:
  - `chart_types.md`: Deep dive into 25+ chart types.
  - `color_palettes.md`: Accessibility-first color systems.
  - `libraries.md`: Quick-start syntax for major viz libraries.

## License

MIT
