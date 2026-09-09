# Stashive Brand

## Identity

Name:
- **Stashive**

Positioning:
- self-hosted collection and inventory management
- organized, technical, modern
- visually related in spirit to Meshive, but a distinct product

Concept:
- storage box = physical inventory
- map pin = location / finding
- green glow = active, modern, recognizable product identity

## Core palette

| Token | Hex | Purpose |
|---|---|---|
| Emerald | `#065F46` | primary brand / deep green |
| Aqua Glow | `#10E6A1` | primary accent / glow |
| Mint | `#6FF3C7` | secondary highlight |
| Ink | `#0F172A` | primary text / dark UI |
| Cloud | `#F6FBF9` | light background |

## Suggested CSS tokens

```css
:root {
  --stashive-emerald: #065F46;
  --stashive-glow: #10E6A1;
  --stashive-mint: #6FF3C7;
  --stashive-ink: #0F172A;
  --stashive-cloud: #F6FBF9;

  --color-brand-primary: var(--stashive-emerald);
  --color-brand-accent: var(--stashive-glow);
  --color-brand-soft: var(--stashive-mint);
  --color-text-primary: var(--stashive-ink);
  --color-page-background: var(--stashive-cloud);
}
```

## Glow usage

The glow should create recognizable emphasis, not visual noise.

Use glow for:
- active navigation accent
- selected cards
- primary scan action
- logo treatment
- focus/hover highlights
- important status accent

Avoid:
- large glowing text blocks
- every card edge glowing
- high bloom around body text
- glow replacing accessible contrast

## Logo

Reference assets are in `assets/`.

Rules:
- do not redraw or regenerate the logo as part of normal frontend work
- preserve aspect ratio
- transparent asset preferred on application surfaces
- maintain clear space around the logo
- use icon-only form where horizontal space is limited
- use horizontal form for header/login/about surfaces

## UI feel

Target:
- dark technical surfaces can use Ink + Emerald
- light surfaces use Cloud with restrained green accents
- rounded but not toy-like
- clean inventory density
- crisp typography
- green glow should make interactive focus obvious

The UI should feel like a serious self-hosted tool with a distinct identity, not a generic admin dashboard.
