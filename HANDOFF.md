# FoodGrump — Handoff / Resume Notes

Last updated: 2026-07-22. Read this file first to resume with minimal context.

## Where things stand

**The app is live and working** — a backend-free web build published to GitHub Pages:
- Live URL: **https://mikhailemmanuel.github.io/The-Grump-App/**
- Deploys automatically on every push to `main` via `.github/workflows/deploy-web.yml`.
- Runs offline against a curated dataset (`mobile/lib/seed.json`, 182 venues across 11
  cities), scored by the real weighting model. Flag: `USE_LOCAL_DATA` in `mobile/lib/config.ts`.

**A design prototype exists** (separate from the live app) — a self-contained HTML design
study, published as a Claude Artifact:
- Artifact URL: **https://claude.ai/code/artifact/374c900c-459c-4fc8-9e02-f2725f21921b**
- Source: `mobile/design/foodgrump-prototype.template.html` (+ data injected)
- Rebuild: `node mobile/design/build-prototype.mjs` → `mobile/design/foodgrump-prototype.html`
- To update the SAME artifact URL: publish that file via the Artifact tool, passing
  `url: https://claude.ai/code/artifact/374c900c-459c-4fc8-9e02-f2725f21921b`.

## Prototype design direction (agreed)
Editorial "guidebook" identity: pine-green accent, brass "seal" for the composite score,
serif venue names, cool green-biased paper neutral, full light/dark. Screens:
- **Explore** = a map with pins (pine = restaurants, brass = hotels), All/Eat/Stay filter.
- **Rankings** = sticky city + type header; filters for cuisine, cost ($–$$$$), rating (70/80/90+).
- **Search** = name/city/cuisine.
- **My List** (was "Profile") = Want to Go + Visited; Visited filters by city, type, and the
  verdict you left (Go back / Iffy / Skip). Verdict is set on the venue detail screen.

## Open design decisions (ask the user)
1. Map pins: score-inside-pin (current) vs plain category-colored dots?
2. Rankings cost/rating filters: single-select (current) vs multi-select?

## Next task (not yet started)
**Port the prototype design into the real Expo app** so it deploys live:
- Explore → real map (Explore currently uses a list; live app has `react-native-maps`,
  which only renders on native — for web use a web map or a styled fallback).
- Rankings → sticky header + cuisine/cost/rating filters.
- Rename Profile → My List; Saved → Visited; add verdict + Visited filters.
- Real-app files: `mobile/app/(tabs)/*.tsx`, `mobile/app/venue/[id].tsx`,
  `mobile/components/*`, data via `mobile/lib/dataSource.ts` + `localData.ts` + `localStore.ts`.

## How to resume cheaply (token/context tips)
- **Start a NEW session** (empty context is far cheaper than continuing a long one).
- First message: *"Read HANDOFF.md and continue — let's [port to the app / refine the prototype]."*
- Point me at specific files; avoid asking me to re-scan the whole repo.
- The big reference facts are already captured here and in the code — I don't need to re-derive them.

## Branch / deploy notes
- Develop on branch `claude/fervent-davinci-2Ldwr`; open a PR to `main`; deploy runs from `main`.
- GitHub Pages base path is set in `mobile/app.json` (`experiments.baseUrl: "/The-Grump-App"`) —
  must match the repo name's casing or the published page goes blank.
