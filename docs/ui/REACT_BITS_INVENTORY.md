# React Bits Inventory

React Bits was evaluated as a source for selected motion categories. No generated React Bits component export was present in the repository. The TASK-028 implementation therefore uses local, controlled motion primitives inspired by the allowed React Bits categories instead of copying the whole library.

Reference: https://www.reactbits.dev/

## Integrated Components

Component: `SoftSignalBackground`
- Purpose: Quiet animated login background.
- Screen: Login.
- Interactive or decorative: Decorative.
- Performance risk: Low CSS-only gradients, one dominant background.
- Reduced-motion behavior: Disabled by global reduced-motion rule.
- Mobile behavior: Non-interactive full-screen layer behind content.
- Fallback: Static gradient/surface background.

Component: `SpotlightPanel`
- Purpose: Premium hover/spotlight affordance for the active chat panel.
- Screen: Chat workspace.
- Interactive or decorative: Decorative hover emphasis.
- Performance risk: Low CSS pseudo/gradient effect.
- Reduced-motion behavior: Transition disabled by reduced-motion rule.
- Mobile behavior: Same panel without layout dependency.
- Fallback: Standard bordered panel.

Component: `ShimmerText`
- Purpose: Chat waiting state while backend retrieves, generates, and validates answer.
- Screen: Chat workspace.
- Interactive or decorative: Status affordance.
- Performance risk: Low; single active viewport usage.
- Reduced-motion behavior: Animation disabled globally.
- Mobile behavior: Inline text remains readable.
- Fallback: Static status text.

## Rejected Effects

- Heavy WebGL/canvas backgrounds: rejected for admin/data screens and bundle weight.
- Animated text for table rows/forms/citations: rejected for readability and accessibility.
- Multiple simultaneous spotlight effects: rejected to avoid distraction.
- Motion in destructive confirmations: rejected to preserve decision clarity.