# Component Browser Panel Design

**Date:** 2026-03-02
**Status:** Approved

## Problem

The Add tab has unused space in the bottom half. Users must manually type component names/values or use the small suggestion popup. During sorting sessions, a visual browser of available components would speed up entry.

## Solution

A reactive chip-grid panel at the bottom of the Add tab. Shows clickable component chips from two data sources (DTU shop CSV and existing inventory), filtered by the active category and value field input.

## Layout

```
┌─────────────────────────────────────────────────────────┐
│  Add New Component        [resistor] [capacitor] [IC].. │
├───────────────────────────────────┬─────────────────────┤
│  Form fields (name, cat, value,   │  Recent sidebar     │
│  package, qty, notes, buttons)    │                     │
├───────────────────────────────────┴─────────────────────┤
│  Component Browser    [Shop | My Inventory]    100/523  │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐│
│  │ 10Ω  │ │ 22Ω  │ │ 47Ω  │ │100Ω  │ │220Ω  │ │330Ω ││
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └─────┘│
│  (scrollable, wrapping grid of chips)                   │
└─────────────────────────────────────────────────────────┘
```

- Panel spans full width below the form + recent sidebar
- Header row: title, Shop/Inventory toggle, item count badge
- Body: scrollable frame with wrapping chip grid

## Data Sources

### Shop mode
- Source: DTU shop CSV (`dtu_component_shop(1).csv`, 1464 items, 14 categories)
- Chip label: value field (for passives) or part_number (for ICs/actives)
- Auto-fill on click: name = `{part_number} {subcategory}`, value, category, notes = description

### Inventory mode
- Source: SQLite DB, filtered by category
- Chip label: value or name
- Auto-fill on click: name, value, package, category, notes

## Reactive Filtering

1. **Category change** (quick-select buttons or dropdown) repopulates chips for that category
2. **Value field typing** filters chips live — matches against value, part_number, subcategory
3. **Toggle switch** swaps between shop and inventory data, re-applies current filters

## Chip Click Action

1. Auto-fill form fields (name, value, category, notes; package if available)
2. Move focus to Quantity field for quick adjustment
3. User hits Save or Enter to commit

## Visual Design

- Chip background: `#2d2d2d`, rounded corners, white text 11-12px
- Hover: accent blue glow (`#3b8ed0`)
- Resistor chips: thin left-border colored by first band (brown=1x, red=2x, etc.)
- Toggle: two-segment button, active=accent blue, inactive=gray25
- Scrolling: vertical mousewheel, chips wrap naturally

## Performance

- Lazy rendering: show first 100 chips, load more on scroll
- Count badge: "showing N of M"
- Shop data loaded once at startup (already cached in `ShopData` class)

## Scope Boundaries

- Only on the Add tab (not inventory/stock/dashboard tabs)
- No editing of shop data
- No drag-and-drop
