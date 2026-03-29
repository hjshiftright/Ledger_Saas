---
name: frontend-antigravity
description: Architect and develop production-grade React interfaces driven by Markdown requirements. Ensures absolute visual consistency across multi-screen applications while optimizing for screen real estate and structural code integrity.
---

# Frontend Engineering & Design System Skill

This skill guides the creation of cohesive, high-density React applications where the **Markdown file is the single source of truth** for requirements.

## 1. Requirement-Driven Architecture (The Plan)
- **Source-to-Code:** Treat the user's Markdown file as the definitive blueprint. Parse requirements into functional React components without deviating from the stated logic.
- **Proper Implementation:** Use TypeScript for all components. Ensure the UI code structure is modular, following a "Atomic Design" pattern (Atoms, Molecules, Organisms).

## 2. Global Visual Consistency (The "Same Look" Rule)
- **Design Tokens:** Instead of unique styles for every screen, implement a strict **Design System**. Use a centralized theme (Tailwind config or CSS Variables).
- **Style Lockdown:** Every screen must use the same color palette, typography scales, and border-radii defined in the system. Avoid "Snowflake CSS" (one-off styles).
- **Component Reusability:** If a UI pattern repeats across screens, it must be abstracted into a shared component to ensure identical behavior and look.

## 3. Spatial Intelligence & Real Estate
- **Apt Real Estate Usage:** Do not leave vast empty spaces on large monitors. Use **CSS Grid (grid-template-areas)** to create layouts that intelligently expand and reflow.
- **Information Density:** For data-heavy screens, use "Compact" layouts. For landing pages, use "Comfortable" spacing.
- **Fluid Scaling:** Use the `clamp()` function for typography and spacing so the UI feels "weightless" and scales smoothly between 13" laptops and 32" monitors.

## 4. Frontend Aesthetics (Refined)
- **Typography**: Pair a distinctive display font (from the requirements) with a highly readable functional sans-serif for UI elements.
- **Motion**: Use `framer-motion` for shared layout transitions between screens to provide a seamless, "antigravity" user experience.
- **Polish**: Add subtle textures (noise, grain) or depth (soft shadows) globally via the base layout to avoid a "flat" AI look.

## 5. Technical Constraints for Claude Code
- **Framework**: React.
- **Styling**: Tailwind CSS (preferred for consistency).
- **Accessibility**: Ensure ARIA labels and semantic HTML are generated as part of the "properly written" code requirement.
- **Performance**: Minimize re-renders across the "many screens" by using proper React hooks (useMemo, useCallback).