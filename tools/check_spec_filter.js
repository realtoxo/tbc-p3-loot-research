// Exercise the spec filter's logic against the markup the build actually wrote.
//
// The filter is the one piece of behavior on this site that a reader can get a
// wrong answer from. Every other component renders once and is either right or
// visibly broken; this one hides claimants, and a claimant hidden while the
// count still says "all" is how the feature causes a wrong loot decision.
//
// It reads site/conventions.html rather than a fixture, so the attribute names
// are checked too: a filter that renamed `data-spec-member` and forgot the
// script would pass a fixture and fail the page.
//
// The functions below are the same shape as the ones in theme/template.html. A
// browser is not required to check the logic, and there is no browser in CI.
//
// Usage:
//     just build && node tools/check_spec_filter.js [PAGE]

'use strict';

const fs = require('fs');

const page = process.argv[2] || 'site/conventions.html';
if (!fs.existsSync(page)) {
  console.error(`${page} not found. Run \`just build\` first.`);
  process.exit(2);
}
const html = fs.readFileSync(page, 'utf8');

const region = /<div class="spec-filter-groups">([\s\S]*?)<\/fieldset>/.exec(html);
if (!region) {
  console.error(`${page} holds no spec filter, so there is nothing to check.`);
  process.exit(2);
}
const markup = region[1];

const GROUPS = [...markup.matchAll(/data-spec-group="([^"]+)"/g)].map((m) => m[1]);
const GROUP_NAMES = [...markup.matchAll(
  /spec-filter-group-name">([^<]+)</g)].map((m) => m[1]);
const MEMBERS = [...markup.matchAll(
  /data-spec-card="([^"]+)"[^>]*data-spec-member="([^"]+)"/g)].map((m) => [m[1], m[2]]);

// A stand-in for a checkbox, carrying only what the script reads off one.
function box(attrs) {
  return {
    checked: true,
    indeterminate: false,
    getAttribute(key) { return attrs[key] || null; },
  };
}
const boxes = MEMBERS.map(([id, key]) =>
  box({ 'data-spec-card': id, 'data-spec-member': key }));
const groups = GROUPS.map((key) => box({ 'data-spec-group': key }));

function membersOf(group) {
  const key = group.getAttribute('data-spec-group');
  return boxes.filter((b) => b.getAttribute('data-spec-member') === key);
}

function apply() {
  groups.forEach((group) => {
    const members = membersOf(group);
    const on = members.filter((b) => b.checked).length;
    group.checked = on === members.length;
    group.indeterminate = on > 0 && on < members.length;
  });
  return boxes.filter((b) => b.checked).length;
}

function toggleGroup(index, state) {
  groups[index].checked = state;
  membersOf(groups[index]).forEach((b) => { b.checked = state; });
  return apply();
}

function state() {
  return groups.map((g, i) =>
    `${GROUPS[i]}:${g.indeterminate ? 'partial' : g.checked ? 'on' : 'off'}`).join(' ');
}

let failures = 0;
function is(label, got, want) {
  const ok = String(got) === String(want);
  if (!ok) {
    failures++;
    console.log(`FAIL  ${label}\n        got ${got}\n       want ${want}`);
  }
}

if (!GROUPS.length || !MEMBERS.length) {
  console.error('the filter carries no groups or no members, so it filters nothing.');
  process.exit(1);
}

// THE PARTITION IS THE TWO-LEVEL STANDING AND NOTHING ELSE. BIS first where
// both appear, Upgrade after it, and no third label exists: a group named
// anything else means the filter is grouping on retired vocabulary.
is('every group is BIS or Upgrade', GROUP_NAMES.filter(
  (n) => n === 'BIS' || n === 'Upgrade').length, GROUP_NAMES.length);
is('no standing appears twice', new Set(GROUP_NAMES).size, GROUP_NAMES.length);
if (GROUP_NAMES.length === 2) {
  is('BIS comes before Upgrade', GROUP_NAMES.join(' '), 'BIS Upgrade');
}

// EVERY CARD BELONGS TO EXACTLY ONE GROUP. A card in no group can never be
// reached by a group control, and a card in two would be toggled twice.
is('every group covers its members', boxes.length,
  groups.reduce((n, g) => n + membersOf(g).length, 0));
is('the page starts with every card shown', apply(), boxes.length);

boxes.forEach((b) => { b.checked = false; });
is('cleared shows nothing', apply(), 0);
is('cleared leaves every group off', state(),
  GROUPS.map((k) => `${k}:off`).join(' '));

is('one group on shows only its own members', toggleGroup(0, true),
  membersOf(groups[0]).length);

// THE POINT OF THE FEATURE. The partition is additive, so every BIS and every
// Upgrade claimant can be on screen together. Skipped where the page carries
// one group, which is an item whose claimants all share one standing.
if (groups.length > 1) {
  toggleGroup(1, true);
  is('groups are additive', apply(),
    membersOf(groups[0]).length + membersOf(groups[1]).length);
} else {
  console.log('note  one group on this page, so the additive check is skipped');
}

// A group of one is either on or off and can never be partial, so the partial
// state needs a group with at least two members to be shown at all.
const partial = groups.find((g) => membersOf(g).length > 1);
if (partial) {
  const at = groups.indexOf(partial);
  const members = membersOf(partial);
  members.forEach((b) => { b.checked = false; });
  members[0].checked = true;
  apply();
  is('a partly selected group reads partial', state().split(' ')[at],
    `${GROUPS[at]}:partial`);
  members.forEach((b) => { b.checked = true; });
  apply();
  is('a fully selected group reads on', state().split(' ')[at],
    `${GROUPS[at]}:on`);
} else {
  console.log('note  every group holds one card, so the partial check is skipped');
}

if (failures) {
  console.log(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log(`spec filter: ${GROUPS.length} group(s), ${MEMBERS.length} card(s), `
  + 'every check passes');
