---
name: farmwise-glassmorphism-ui
description: Apple-design glassmorphism UI patterns for FarmWise. Use when building Next.js frontend components, pages, or layouts. Triggers on UI tasks, component creation, or styling work.
---

# FarmWise Glassmorphism UI

Apple-inspired glassmorphism design system for the FarmWise potato crop monitoring PWA. Every UI element uses frosted glass aesthetics.

## Design System

### Glass Variables (globals.css)
```css
:root {
  --glass-bg: rgba(255, 255, 255, 0.72);
  --glass-border: rgba(255, 255, 255, 0.24);
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  --glass-blur: 20px;
  --primary: #166534;
  --primary-light: #22c55e;
  --earth: #92400e;
  --earth-light: #f59e0b;
  --cream: #fefce8;
  --soil: #78350f;
  --leaf: #15803d;
  --text-primary: #1a2e05;
  --text-secondary: #4a5e2a;
  --radius: 1.25rem;
}
```

### Component Patterns
- Every card: `bg-white/70 backdrop-blur-xl border border-white/20 rounded-2xl shadow-lg`
- Primary buttons: `bg-green-800 text-white rounded-full px-6 py-3 font-semibold`
- Nav: fixed bottom, glass bar with `backdrop-blur-2xl bg-white/80 border-t border-white/20`
- Inputs: `bg-white/50 backdrop-blur border border-white/30 rounded-xl px-4 py-3`
- Icons: Lucide React (leaf, cloud-sun, bar-chart3, shield-check, user)

### Typography
- Headings: `font-sans tracking-tight` (system SF Pro via Tailwind)
- Body: `font-sans text-base leading-relaxed`
- Numbers/metrics: `tabular-nums font-mono`

### Motion
- Page load: staggered fade-up reveals with `animation-delay`
- Cards: hover `scale-[1.02]` with `transition-all duration-300`
- Nav: hide/show on scroll (use `useScrollPosition` hook)
- Stage bar: spring animation on progress change

### Pages
- Home: hero with advice card (large glass panel, gradient bg cream → green-50)
- Onboarding: multi-step form with glass panels, progress dots
- Dashboard: bottom nav, glass cards with Recharts inside
- Certificate: PDF view in glass frame

### Never Use
- Solid white backgrounds (always use glass)
- Sharp corners (always rounded-xl or rounded-2xl)
- Generic fonts (Arial, Inter, Roboto)
- Purple gradients
- Cookie-cutter layouts
