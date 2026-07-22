#!/usr/bin/env node
/**
 * Rebuilds the design prototype (design/foodgrump-prototype.html) from the
 * committed template + the real dataset (../lib/seed.json). The prototype is a
 * self-contained HTML design study, published as a Claude Artifact.
 *
 *   node design/build-prototype.mjs
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const tpl = readFileSync(join(here, 'foodgrump-prototype.template.html'), 'utf8');
const seed = JSON.parse(readFileSync(join(here, '..', 'lib', 'seed.json'), 'utf8'));

const slim = {
  cities: seed.cities,
  venues: seed.venues.map((v) => ({
    id: v.id, entity_type: v.entity_type, name: v.name, city: v.city, neighborhood: v.neighborhood,
    lat: v.lat, lng: v.lng, price_level: v.price_level, cuisine_tags: v.cuisine_tags,
    hotel_brand: v.hotel_brand, tags: v.tags, blurb: v.blurb,
    composite_score: v.composite_score, rank: v.rank,
    reservations: (v.reservations || []).map((r) => ({ platform: r.platform })),
    recommendations: (v.recommendations || []).map((r) => ({
      source: r.source, source_label: r.source_label, snippet: r.snippet,
      rating_display: r.rating_display, weight: r.weight,
    })),
  })),
};

const out = tpl.replace('__SEED_DATA__', JSON.stringify(slim));
writeFileSync(join(here, 'foodgrump-prototype.html'), out);
console.log(`Built foodgrump-prototype.html (${(out.length / 1024).toFixed(0)}KB, ${slim.venues.length} venues)`);
