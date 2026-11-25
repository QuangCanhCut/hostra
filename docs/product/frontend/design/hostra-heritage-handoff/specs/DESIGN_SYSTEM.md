# Heritage Luxury — Design System v0.5 (proposal)

## Visual intent
Premium editorial craft meets serious commerce operations. Earthy obsidian/espresso, bronze rules, champagne gold CTA, ivory text, restrained landscape and product photography. Avoid neon AI gradients, glowing cubes, generic rainbow charts, gratuitous sparkle, excessive border nesting, overuse of pills, decorative glass, and repeating the same card layout on all screens. Use imagery deliberately on dashboard, presenter library, catalog details, and public entry; operational tables, claims and control room must remain clean and efficient. Pattern is optional and subtle, not a full-page repeating background.

## Semantic tokens
Read `tokens.json` and `../theme.css`. Map existing Tailwind/CSS variables or component theme to semantic names, not one-off colors. Do not overwrite status semantics with gold. Red remains LIVE/danger, green verified/healthy, amber warning/pending, blue info, neutral stopped/unknown. Critical action red solid, text labels and icons, never color alone. `primary` gold dark mode; dark brown text over warm gold. Light companion uses darker bronze foreground/accent for legibility. Both themes retain same information hierarchy, content and permissions; light is proposed and not newly approved by Owner.

## Typography and geometry
- Body: Be Vietnam Pro (approved in DS-D1), Inter fallback, system sans fallback. Use existing licensed fonts; validate full Vietnamese diacritics. Display only: Georgia or a Vietnamese-capable editorial serif (e.g. Noto Serif if already available). Do not use serif in forms/table/control bar. Browser previews may use system fonts; check after actual font loading.
- Display h1 32–36 / 1.15, hero 30–34 / 1.14, h2 18–20 / 1.35, h3 15–16 / 1.45; body 14 / 1.5; small 12–13; labels >= 11 where needed. Mobile h1 26–28. Tabular numeric figures.
- Spacing scale 4, 8, 12, 16, 20, 24, 28, 32, 40, 48 px. Desktop app sidebar 248px (216px at 801–1150), topbar 60px, main gutters 28px, content max 1700px, card gap 16px, radius 12px; controls radius 8px. Desktop 1440 × 1000 reference. On mobile 390×844, main gutter 16px, sidebar drawer/hamburger, form and modal adapt; table visual cards. Tablet layouts depend on actual width; no page horizontal overflow. Keyboard focus visible; targets >= 44px mobile production (sample HTML may be compact; adjust for touch).
- Elevation: subtle warm surface gradient, borders mostly #503E2D; #896641 reserved for featured content/focus. No glow on every control. Keep fixed/scrolling shell accessible.

## Component requirements
| Component | Visual/behavior |
|---|---|
| AppShell, Header, Sidebar | Shared across merchant routes; active nav bronze; rights/viewer separate; workspace/role from store. Sidebar landscape at bottom with gradient fade, noninteractive. Mobile drawer focus trap/close/Escape; theme mode persists by existing preferences. |
| PageHeader | Display heading, short subtitle, contextual action; no marketing hero on every page. |
| Hero | 208–240px desktop; image asset only on right, dark overlay, native text + CTA left; conditional next action; no external platform promises. |
| Card / StatCard | Regular surface, focus border only if featured; labels/numbers native DOM; decorative WebP at 30–40% right with mask. No meaningless trend lines. |
| StatusBadge | Semantic colors with text; independent lifecycle, AI, Media, Publisher, OCOP, Knowledge, consent, QC. |
| Button | Primary one per action context; outline secondary, ghost tertiary, danger solid. Hover + focus + disabled + pending spinner; preserve handler and permissions. |
| Table / mobile card | Real semantic table with header, row hover and actionable links; mobile labels/cards, no clipped columns, sorting/pagination from existing logic. |
| Form and Stepper | Label above field, native controls, clear required/optional and validation, save/resume. Do not infer success when submit requested. |
| Tabs / Filters | Selected bronze underline/border; keyboard navigation; horizontal scroll or wrap on mobile; preserve deep-link and history. |
| Drawer / Modal | Right drawer ~420–480px desktop, full-width mobile; focus trap, Escape, restore focus, destructive confirmation, no cropped text. |
| Toast / Banner | Inline error for persistent state, toast for completed operation, warning/danger banner for gate or stale state; no auto-dismiss on critical issues. |
| Evidence / Claim | Document source on left, structured facts/decision on right; use source anchors, not arbitrary approve buttons. Mobile source sheet. |
| Media / control dock | 16:9 subscribe-only preview, separate player and AI state, stable sticky runtime controls, red danger actions distinct, comments/queue accessible. Mobile keep controls reachable while scrolling. |
| Chart | Truthful data, explicit unit, time axis and legend, no fake curves; missing N/A or partial. |
| Public Viewer | No Studio sidebar, minimal brand, AI disclosure, video above SKU then chat on mobile, no chat overlay on video, no camera/mic publish. |

## Assets manifest
| File | Use | Source / limitation |
|---|---|---|
| hero.webp | Dashboard hero right half / entry illustration | Crop from chosen generated image; no text baked in the selected region; not actual product evidence. |
| sidebar-landscape.webp | Sidebar bottom | Crop from selected mockup, mask edges. |
| presenter-heritage.webp | Featured session still thumbnail | Crop from mockup; static only, no video or claims. |
| microphone.webp / plums.webp / knowledge-book.webp / camera.webp | Resource tiles | Crops, decorative only. |
| linh.webp / mai.webp / an.webp | Presenter library/demo player | Crop from original screenshot 05; demo only, replace with approved real assets. |
| logo.svg | Draft emblem | Approximate vector mark, not final legal branding. |

Do not use product illustrations as certificate evidence or approved presenter identity. Do not replace live player with decorative image. Real repo may already contain portrait/product assets; prefer those for business UI. For user-specific workspace, make dashboard hero theme generic or configurable; not all merchants are Mường Lát. Asset optimization: WebP/AVIF, responsive widths, lazy load below fold, preload hero only if critical. No external image CDN required for this package.
