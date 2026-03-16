# Codex UI/UX Graded Audit

**Date:** 2026-03-16
**Auditor:** Frontend Agent
**Scope:** Visual design, layout, responsiveness, accessibility, navigation, loading/error states, mobile experience
**Note:** This audit covers UI/UX quality only. Functional bugs are tracked separately in `UX_AUDIT_REPORT.md`.

---

## Overall Grade: C+

| Area | Grade | Summary |
|------|-------|---------|
| Layout | B | Clean sidebar + content structure, some inconsistencies |
| Responsiveness | B- | Good breakpoint coverage, grid issues at certain widths |
| Accessibility | D | Critical failures: no focus indicators, small touch targets, missing aria-labels |
| Navigation | B | Consistent back buttons, clean URLs, lacks breadcrumbs |
| Visual Design | B+ | Cohesive dark theme, good color palette, minor inconsistencies |
| Loading States | B- | Skeleton screens present but inconsistent patterns |
| Error States | C- | Basic error messages exist, no error boundary, no retry UI |
| Mobile Experience | C | Responsive sidebar works, touch targets far too small |

---

## 1. Layout — Grade: B

**Strengths:**
- Clean sidebar + main content architecture in `AppLayout.tsx`
- Desktop sidebar is fixed 240px width — appropriate for 10 nav items
- Content padding scales properly: `p-4` mobile → `md:p-8` desktop
- Mobile sidebar uses proper off-canvas pattern with overlay backdrop

**Issues:**

| Issue | Severity | Location |
|-------|----------|----------|
| Inconsistent max-width across pages | Medium | DashboardPage uses `max-w-6xl`, other pages are full-width |
| No content max-width on Library/Authors pages | Medium | Wide monitors get extremely stretched grids |
| Settings page negative margin hack | Low | `SettingsPage.tsx` — `h-[calc(100vh-4rem)] -m-6` is fragile |
| Sidebar nav spacing could be tighter on mobile | Low | `AppLayout.tsx` — 10 items take significant vertical space |

**Recommendations:**
- Apply a consistent `max-w-7xl mx-auto` wrapper to all page content
- Replace the calc-based height hack in Settings with a proper flex layout
- Consider collapsible nav groups if more items are added

---

## 2. Responsiveness — Grade: B-

**Strengths:**
- Proper breakpoint usage: `sm:` (640px), `md:` (768px), `lg:` (1024px), `xl:` (1280px)
- BookGrid scales well: `grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6`
- SearchBar breaks to column layout on mobile with `sm:flex-row`
- Wishlist table hides non-essential columns on mobile via `hidden sm:table-cell`
- Viewport meta tag correctly configured in `index.html`

**Issues:**

| Issue | Severity | Location |
|-------|----------|----------|
| 6-column grid too aggressive at XL with sidebar | Medium | `BookGrid.tsx` — at 1280px minus 240px sidebar, columns are ~140px |
| AuthorsPage grid has same 6-column issue | Medium | `AuthorsPage.tsx` — author cards cramped at breakpoint edges |
| Table horizontal scroll has no visual affordance | Low | `WishlistPage.tsx` — users may not discover scrollable content |
| Modal overflow not visually indicated | Low | `FindReleasesModal.tsx` — `max-h-[85vh]` content may be cut off without scroll hint |

**Recommendations:**
- Reduce XL grid to 5 columns to account for sidebar width
- Add a subtle gradient fade or scroll shadow on horizontally scrollable tables
- Add a scroll indicator (shadow/fade) on modals with overflow content

---

## 3. Accessibility — Grade: D

This is the weakest area. Multiple WCAG 2.1 Level AA failures.

**Critical Failures:**

| Issue | WCAG | Severity | Location |
|-------|------|----------|----------|
| No visible focus indicators anywhere | 2.4.7 (AA) | Critical | Global — inputs use `focus:outline-none` without `focus-visible` replacement |
| Icon-only buttons lack `aria-label` | 4.1.2 (A) | Critical | RefreshCw, Eye/EyeOff, Close buttons across multiple components |
| No focus trapping in modals | 2.4.3 (A) | Critical | `FindReleasesModal.tsx`, `FolderBrowserModal.tsx` — Tab key escapes modal |
| Touch targets below 44×44px | 2.5.8 (AA) | High | Icon buttons use `p-1` (≈22px), should be 48×48px minimum |

**Major Issues:**

| Issue | WCAG | Severity | Location |
|-------|------|----------|----------|
| Color contrast borderline on secondary text | 1.4.3 (AA) | High | `text-gray-500` on `bg-gray-900` ≈ 4.5:1 ratio (borderline) |
| Placeholder text low contrast | 1.4.3 (AA) | High | `placeholder-gray-500` on dark inputs |
| Error messages lack `role="alert"` | 4.1.3 (AA) | Medium | `RootFoldersSection.tsx` — error paragraph not announced by screen readers |
| Form inputs missing `<label htmlFor>` association | 1.3.1 (A) | Medium | Several inputs have visual labels but no programmatic association |
| No `aria-current="page"` on active nav link | — | Low | `AppLayout.tsx` — NavLink has visual styling but no ARIA attribute |
| `line-clamp-3` truncation not announced | — | Low | `AuthorDetailPage.tsx` — truncated bio confusing for screen readers |

**Positive Notes:**
- Semantic HTML used properly: `<nav>`, `<main>`, `<header>`, `<section>`
- Toggle switch has correct `role="switch"` and `aria-checked`
- Book cover images have appropriate `alt` text
- NavLink correctly distinguishes active state visually

**Recommendations:**
1. Add global `focus-visible` styles: `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500`
2. Add `aria-label` to every icon-only button (e.g., `aria-label="Refresh catalog"`)
3. Install and use a focus trap library (e.g., `react-focus-lock`) for all modals
4. Increase all icon button padding to minimum `p-2.5` (40px) or ideally `p-3` (48px)
5. Upgrade secondary text from `text-gray-500` to `text-gray-400` for better contrast
6. Add `role="alert"` to error message containers

---

## 4. Navigation — Grade: B

**Strengths:**
- Clean URL structure: `/authors/:id`, `/series/:id`, `/books/:id`
- All detail pages have consistent "Back to X" links with ArrowLeft icon
- Search page supports query params: `/search?q=keyword`
- BookDetailPage has series navigation bar with prev/next buttons
- Sidebar auto-closes on item click on mobile
- Settings page has sub-navigation sidebar

**Issues:**

| Issue | Severity | Location |
|-------|----------|----------|
| No breadcrumb navigation on detail pages | Medium | Only "Back to X" links — no visual hierarchy trail |
| Back link on BookDetailPage always goes to `/books` | Medium | Ignores whether user came from author/series/search page |
| Comics sidebar link goes to wrong route | High | `AppLayout.tsx` — links to `/books?media_type=comic` instead of `/comics` |
| No keyboard shortcut hints | Low | No documented or visible shortcuts for power users |

**Recommendations:**
- Add breadcrumbs: `Authors > Author Name` on detail pages
- Use `useNavigate(-1)` or track referrer to make Back buttons context-aware
- Fix Comics nav link to use `/comics` route (tracked in functional audit as C3)

---

## 5. Visual Design — Grade: B+

**Strengths:**
- Cohesive dark theme with well-defined CSS custom properties in `globals.css`
- Color palette: `bg-gray-950` primary, `bg-gray-900` surface, `indigo-600` accent — modern and readable
- Consistent button styles: primary (indigo), secondary (gray), danger (red) with proper hover/disabled states
- Badge system uses opacity-based coloring (`bg-indigo-500/20 text-indigo-400`) — clean look
- Card hover effects are subtle and tasteful: `hover:border-indigo-500/50 hover:shadow-lg`
- System font stack is performant and appropriate

**Issues:**

| Issue | Severity | Location |
|-------|----------|----------|
| Inconsistent border colors | Low | Most use `border-gray-800`, some modals use `border-gray-700`, some use `border-gray-800/50` |
| Shadow inconsistency | Low | BookCard has hover shadow, modals have none (should have elevation) |
| Text size hierarchy unclear | Medium | Section titles alternate between `text-lg font-semibold` and `text-sm font-medium` |
| Icon sizing not consistently mapped to button sizes | Low | Mix of `size={14}` and `size={18}` without clear rules |
| Very small `text-xs` (12px) text on dark background | Low | Strains readability, especially for metadata labels |

**Recommendations:**
- Standardize on `border-gray-800` everywhere
- Add `shadow-xl shadow-black/30` to modals for visual elevation
- Define a clear text hierarchy: page title → section title → label → body → caption
- Bump minimum text size to `text-sm` (14px) for body content

---

## 6. Loading States — Grade: B-

**Strengths:**
- Skeleton screens implemented with shimmer animation (`globals.css` lines 41-45)
- BookGrid shows 12 skeleton cards while loading
- AuthorsPage and SeriesPage both have skeleton loading states
- Real-time download progress via WebSocket with visual progress bars
- Author catalog fetch shows spinner overlay with status text
- Automatic refetch every 3 seconds during active operations

**Issues:**

| Issue | Severity | Location |
|-------|----------|----------|
| Three different loading patterns used | Medium | Skeletons (BookGrid), Spinners (AuthorsPage refetch), Pulse (DashboardPage) |
| No minimum skeleton display time | Low | Fast queries cause loading flicker (<200ms) |
| Stale data not visually indicated | Low | No "last updated" or "refreshing..." indicator between refetches |
| No progress indication for long operations | Medium | Catalog fetch can take 30+ seconds with only a spinner |

**Recommendations:**
- Standardize: use skeletons for initial page loads, spinners for background refreshes, progress bars for long operations
- Add 200ms minimum display time for skeletons to prevent flicker
- Show estimated progress or step count for catalog fetches

---

## 7. Error States — Grade: C-

**Strengths:**
- Detail pages have "not found" fallback UI (BookDetailPage, AuthorDetailPage, SeriesDetailPage)
- Toast notifications for API errors via `ToastContext`
- AuthorDetailPage has retry button for catalog fetch errors
- Error messages use red AlertCircle icon — visually clear

**Issues:**

| Issue | Severity | Location |
|-------|----------|----------|
| No React error boundary in app tree | Critical | `App.tsx` — any unhandled component error white-screens the entire app |
| Most error states lack a "Retry" button | High | Only AuthorDetailPage has retry; others show message only |
| Empty states look identical to error states | Medium | "No books found" uses same styling as error messages |
| Toast has no max count | Medium | `ToastContext.tsx` — rapid errors flood the UI |
| Toast auto-dismiss at 3.5s may be too fast for errors | Low | Users may not read error details in time |
| SearchPage downloads have no error handler | High | `SearchPage.tsx` — `downloadMutation` has no `onError` |
| Form validation only after failed submit | Low | `RootFoldersSection.tsx` — errors shown post-attempt only |

**Recommendations:**
1. Add a global `ErrorBoundary` wrapping `<App>` with a "Something went wrong" fallback + reload button
2. Add retry buttons to all data-fetching error states
3. Differentiate empty states (friendly illustration + "Add your first book") from error states (red icon + retry)
4. Cap simultaneous toasts at 3-5 and keep error toasts longer (5-6 seconds) or make them dismissible only
5. Add `onError` handlers to all mutations

---

## 8. Mobile Experience — Grade: C

**Strengths:**
- Off-canvas sidebar with overlay backdrop — proper mobile pattern
- Sidebar auto-closes on navigation
- 2-column book grid on mobile — reasonable for small screens
- Modals add `mx-4` margin on mobile — don't span full width
- Wishlist table hides non-essential columns on mobile

**Issues:**

| Issue | Severity | Location |
|-------|----------|----------|
| Icon button touch targets ≈22px | Critical | Menu button, close buttons, table action buttons use `p-1` |
| No mobile breadcrumbs | Medium | Detail pages only show back link, no hierarchy context |
| `text-xs` (12px) labels on mobile | Medium | Metadata labels too small for comfortable phone reading |
| No pull-to-refresh | Low | No mobile-native refresh gesture |
| BulkActionBar may overlap mobile nav | Low | Fixed bottom bar could conflict with phone home indicators |
| No haptic or visual feedback on touch | Low | Buttons lack active state for mobile interactions |

**Recommendations:**
1. Set minimum touch target to 48×48px (`p-3` on icon buttons, or `min-h-[48px] min-w-[48px]`)
2. Add `active:scale-95` or `active:bg-gray-700` for tactile button feedback
3. Bump mobile text minimum to 14px
4. Add `safe-area-inset-bottom` padding to BulkActionBar for notched phones
5. Consider adding pull-to-refresh for library views

---

## Priority Action Items

### P0 — Must Fix (Accessibility/Legal Risk)
1. Add visible focus indicators globally
2. Add `aria-label` to all icon-only buttons
3. Implement focus trapping in modals
4. Increase touch targets to 48×48px minimum
5. Add React error boundary to app root

### P1 — Should Fix (User Experience)
6. Standardize loading state patterns
7. Add retry buttons to error states
8. Differentiate empty states from errors
9. Cap toast count and extend error toast duration
10. Fix inconsistent max-width across pages

### P2 — Nice to Have (Polish)
11. Add breadcrumb navigation
12. Standardize border colors and shadows
13. Define clear text size hierarchy
14. Add context-aware back navigation
15. Add pull-to-refresh for mobile
