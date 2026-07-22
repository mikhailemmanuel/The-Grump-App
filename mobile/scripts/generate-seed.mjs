#!/usr/bin/env node
/**
 * generate-seed.mjs
 *
 * Reads curated venue JSON (raw editorial data) and produces the bundled
 * dataset the app ships with: mobile/lib/seed.json.
 *
 * The composite scoring here is a faithful port of the backend's
 * app/scrapers/scoring.py so the numbers in the offline app match what the
 * real pipeline would produce.
 */

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

// ── Weight tables (mirror backend scoring.py) ────────────────────────
const RESTAURANT_WEIGHTS = {
  foodgrump: 0.20, michelin: 0.15, reddit: 0.15,
  beli: 0.15, google: 0.15, infatuation: 0.10, eater: 0.10,
};
const HOTEL_WEIGHTS = {
  foodgrump: 0.25, conde_nast: 0.20, michelin: 0.20,
  google: 0.20, reddit: 0.15,
};

const MICHELIN_AWARD_SCORES = {
  '3_stars': 100, '3_keys': 100,
  '2_stars': 90, '2_keys': 90,
  '1_star': 80, '1_key': 80,
  bib_gourmand: 65,
  listed: 50,
};
const EATER_AWARD_SCORES = { eater_38: 100, best_of: 75, mentioned: 40 };
const CONDE_NAST_AWARD_SCORES = {
  cn_gold_list: 100, cn_hot_list: 90, cn_readers_choice: 85, reviewed: 50,
};

// Human-readable award labels for the UI.
const AWARD_LABELS = {
  '3_stars': 'Three Stars', '2_stars': 'Two Stars', '1_star': 'One Star',
  bib_gourmand: 'Bib Gourmand', listed: 'Guide Listed',
  '3_keys': 'Three Keys', '2_keys': 'Two Keys', '1_key': 'One Key',
  eater_38: 'Essential (Eater 38)', best_of: 'Best Of', mentioned: 'Featured',
  cn_gold_list: 'Gold List', cn_hot_list: 'Hot List',
  cn_readers_choice: "Readers' Choice", reviewed: 'Reviewed',
};

const SOURCE_LABELS = {
  michelin: 'Michelin Guide',
  eater: 'Eater',
  conde_nast: 'Condé Nast Traveler',
  infatuation: 'The Infatuation',
  beli: 'Beli',
  google: 'Google Reviews',
  reddit: 'Reddit',
  foodgrump: 'FoodGrump Community',
};

// ── Per-source raw 0–100 score (mirror _source_score_from_rec) ───────
function rawSourceScore(source, data) {
  if (source === 'michelin') return MICHELIN_AWARD_SCORES[data.award] ?? 0;
  if (source === 'eater') return EATER_AWARD_SCORES[data.award] ?? 0;
  if (source === 'conde_nast') return CONDE_NAST_AWARD_SCORES[data.award] ?? 0;
  if (source === 'reddit' || source === 'beli' || source === 'infatuation') {
    return (data.rating ?? 0) * 10.0;
  }
  if (source === 'google') {
    return data.rating != null ? (data.rating - 1.0) * 25.0 : 0;
  }
  return 0;
}

// ── Composite (mirror compute_venue_score) ───────────────────────────
function computeComposite(sources, entityType) {
  const weights = entityType === 'restaurant' ? RESTAURANT_WEIGHTS : HOTEL_WEIGHTS;
  const sourceScores = {};
  for (const [source, data] of Object.entries(sources)) {
    if (!(source in weights)) continue;
    const s = rawSourceScore(source, data);
    if (s > 0) sourceScores[source] = Math.round(s * 10) / 10;
  }
  const present = Object.keys(sourceScores);
  const totalWeight = present.reduce((sum, s) => sum + weights[s], 0);
  let weighted = 0;
  if (totalWeight > 0) {
    weighted = present.reduce((sum, s) => sum + sourceScores[s] * weights[s], 0) / totalWeight;
  }
  const nonzero = present.length;
  // Corroboration bonus: reward venues confirmed by many sources, but gently
  // so already-high weighted averages don't all saturate at 100.
  const bonus = Math.min(Math.max(nonzero - 2, 0) * 2, 8);
  const composite = Math.min(Math.max(weighted + bonus, 0), 100);
  return { composite: Math.round(composite * 10) / 10, sourceScores };
}

// ── Helpers ──────────────────────────────────────────────────────────
function slug(s) {
  return String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

function displayRating(source, data) {
  if (['michelin', 'eater', 'conde_nast'].includes(source)) {
    return AWARD_LABELS[data.award] ?? data.award ?? '';
  }
  if (source === 'google') return `${Number(data.rating).toFixed(1)} ★`;
  return `${Number(data.rating).toFixed(1)}/10`;
}

// ── Load curated groups ──────────────────────────────────────────────
const groupFiles = process.argv.slice(2);
if (groupFiles.length === 0) {
  console.error('Usage: generate-seed.mjs <group1.json> [group2.json ...]');
  process.exit(1);
}

let raw = [];
for (const f of groupFiles) {
  if (!existsSync(f)) { console.error(`Missing: ${f}`); process.exit(1); }
  const arr = JSON.parse(readFileSync(f, 'utf8'));
  if (!Array.isArray(arr)) { console.error(`Not an array: ${f}`); process.exit(1); }
  raw.push(...arr);
  console.log(`Loaded ${arr.length} venues from ${f}`);
}

// ── Transform each venue ─────────────────────────────────────────────
const venues = [];
const seenIds = new Set();
for (const v of raw) {
  if (!v.name || !v.city || !v.entity_type) {
    console.warn('Skipping malformed venue:', JSON.stringify(v).slice(0, 80));
    continue;
  }
  const entityType = v.entity_type;
  let id = `${slug(v.city)}-${slug(v.name)}`;
  let n = 2;
  while (seenIds.has(id)) { id = `${slug(v.city)}-${slug(v.name)}-${n++}`; }
  seenIds.add(id);

  const { composite, sourceScores } = computeComposite(v.sources ?? {}, entityType);

  const recommendations = Object.entries(v.sources ?? {}).map(([source, data], i) => ({
    id: `${id}-rec-${i}`,
    source,
    source_label: SOURCE_LABELS[source] ?? source,
    source_url: data.url,
    title: SOURCE_LABELS[source] ?? source,
    snippet: data.snippet ?? displayRating(source, data),
    rating_display: displayRating(source, data),
    rating: data.rating,
    awards: data.award ? [data.award] : undefined,
    score: sourceScores[source] ?? rawSourceScore(source, data),
    weight: (entityType === 'restaurant' ? RESTAURANT_WEIGHTS : HOTEL_WEIGHTS)[source] ?? 0,
  })).sort((a, b) => (b.weight - a.weight) || (b.score - a.score));

  venues.push({
    id,
    entity_type: entityType,
    name: v.name,
    city: v.city,
    country: v.country ?? null,
    neighborhood: v.neighborhood ?? null,
    address: v.address ?? null,
    lat: v.lat ?? null,
    lng: v.lng ?? null,
    tags: entityType === 'restaurant' ? (v.cuisine_tags ?? []) : (v.hotel_brand ? [v.hotel_brand] : []),
    cuisine_tags: v.cuisine_tags ?? null,
    hotel_brand: v.hotel_brand ?? null,
    star_rating: v.star_rating ?? null,
    price_level: v.price_level ?? null,
    blurb: v.blurb ?? null,
    composite_score: composite,
    source_scores: sourceScores,
    recommendations,
    reservations: (v.reservations ?? []).map((r, i) => ({
      id: `${id}-res-${i}`,
      platform: r.platform,
      booking_url: r.url,
    })),
  });
}

// ── Rank per (city, entity_type) ─────────────────────────────────────
const byCityType = {};
for (const v of venues) {
  const key = `${v.city}|${v.entity_type}`;
  (byCityType[key] ??= []).push(v);
}
for (const key of Object.keys(byCityType)) {
  byCityType[key].sort((a, b) => b.composite_score - a.composite_score);
  byCityType[key].forEach((v, i) => { v.rank = i + 1; });
}

// ── City list ordered by total venue count (biggest first) ───────────
const cityCounts = {};
for (const v of venues) cityCounts[v.city] = (cityCounts[v.city] ?? 0) + 1;
const cities = Object.keys(cityCounts).sort((a, b) => cityCounts[b] - cityCounts[a] || a.localeCompare(b));

const out = {
  generated_at_note: 'Curated editorial dataset. Scores computed via the FoodGrump weighting model.',
  cities,
  venues,
};

const outPath = join(ROOT, 'lib', 'seed.json');
writeFileSync(outPath, JSON.stringify(out));
const restaurants = venues.filter(v => v.entity_type === 'restaurant').length;
const hotels = venues.filter(v => v.entity_type === 'hotel').length;
console.log(`\n✅ Wrote ${venues.length} venues (${restaurants} restaurants, ${hotels} hotels) across ${cities.length} cities`);
console.log(`   Cities: ${cities.join(', ')}`);
console.log(`   → ${outPath}`);
