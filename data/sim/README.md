# Sim profiles

Importable wowsims equipment sets, one file per spec per anchor, written by
`tools/export_sim_profiles.py`. The format is the tool's own,
`{"items": [{id, enchant, gems}, ...]}` with seventeen entries in `ItemSlot`
order, so a file pastes straight into the simulator rather than being
transcribed into it.

Forty-five sets: fourteen DPS specs across three anchors, plus three alternate
configurations the captures record. Tanks and healers are out of scope, and the
rulings behind that and behind the encounter, the buffs and the ignored race and
professions are in [`../judgments/capture-fidelity.yaml`](../judgments/capture-fidelity.yaml)
under `sim_profile_scope`.

## How a hit shortfall is closed

**With gems, never with an enchant.** Ruled by the guild lead on 10 August 2026,
and it reverses what this project did before: the throughput enchant a hit
enchant would displace is worth more than the throughput gem a hit gem
displaces, so the socket is the cheaper thing to give up. This guild does not
take hit enchants.

Enchants come from [`../facts/enchants-by-spec.yaml`](../facts/enchants-by-spec.yaml),
farmed from Wowhead per spec, and every spec keeps its throughput enchant in
every slot. Five anchors are short on items alone and close it with gems, which
`hit-captured.yaml` counts after capping them at the sockets the set carries:

| Spec | Anchor | Gap | Hit gems | Sockets |
|---|---|---|---|---|
| arcane_mage | tier_hands_only | 26 | 3 | 10 |
| arms_warrior | entry | 13 | 2 | 7 |
| balance_druid | entry | 7 | 1 | 6 |
| balance_druid | tier_hands_only | 19 | 2 | 8 |
| balance_druid | tier_hands_and_head | 8 | 1 | 7 |

Every one closes comfortably. The hit gems go in before the throughput ones and
skip the meta socket, because a shortfall is a constraint and throughput is not.

## One substitution, and it is the loudest divergence here

**Wolfshead Helm, item 8345, is not in the wowsims database**, and it is the
Feral Cat's head at every anchor. It is a level-40 leatherworking helm and the
database carries TBC items.

Ruled by the guild lead on 15 August 2026: *"put on the t6 helm on the case if
we must"*. **Thunderheart Cover, item 31039, stands in at both anchors, in the
profile only.** It is the head of the Thunderheart Harness, which
[`../facts/tokens.yaml`](../facts/tokens.yaml) gives this spec at tier 6, and
[`../facts/items.csv`](../facts/items.csv) resolves the set name to that id. The
compendium is unchanged. Two earlier answers stand behind this one: Cowl of
Defiance until 14 August 2026, then an empty head slot, which cost the Cat a
whole slot of stats.

**The card DECLINES that helm, and Wolfshead is the entire reason.** The EP
Workbook ranks Wolfshead first in the slot at 0.00 EPV, which is a refusal to
price an energy return rather than a score, and the capture records the head
slot as never tier at any anchor. So a run of this profile answers a question
the compendium refuses to answer. **A Feral Cat sim figure and a Feral Cat card
belong to two different characters and must not be compared.**

The warning is in three places, because a run scrolls away and a file does not:
the exporter prints it on every run, `SUBSTITUTIONS` in
[`../../tools/export_sim_profiles.py`](../../tools/export_sim_profiles.py)
carries the text, and each affected profile carries it under a `_divergence`
key. `tools/run_sims.py` drops that key before sending the request, rather than
trusting the simulator to ignore a field it does not declare.

The substituted head also has a meta socket that the profile leaves **empty**,
since [`../facts/enchants-by-spec.yaml`](../facts/enchants-by-spec.yaml) records
no meta gem for this spec on the ground that Wolfshead has none. The Cat is
short one meta gem on top of wearing the wrong helm.

**It does not make the spec runnable.** Measured 15 August 2026: with this head,
with an empty head, with the recorded talents, with no talents and with a
borrowed rotation, the Feral Cat panics the simulator every time and returns no
figure. The blocker is the parked feral port described below.

## What is still missing before a run

Gear, enchants, gems and talents are in place. A full `IndividualSimSettings`
also needs the raid buffs and debuffs encoded from `roster.yaml`, the encounter,
the spec options, and an APL rotation, all of which the simulator ships presets
for. **Go is not installed on this machine**, so nothing here has been run.

Nothing in this directory is a simulation result. No simulation has been run
against this roster's gear, which `sim-profiles.yaml` has said since it was
written and which stays true.

## Running a simulation

The simulator is not vendored here and is not committed, per the repository
rules. Build it once from the wowsims checkout:

```
go build -tags with_db -o /tmp/wowsimcli ./cmd/wowsimcli
```

**The `with_db` tag is not optional.** `sim/core/database_load.go` carries
`//go:build with_db`, and without it the item database is deliberately EMPTY.
The failure is not obvious: every profile, including the simulator's own
shipped presets, fails with "No item with id" for items that are plainly in
`db.json`.

Then:

```
python3 tools/run_sims.py --check              # every profile, cheaply
python3 tools/run_sims.py --iterations 10000   # a real run
```

## What was learned making it run

Recorded because each cost time and none of it is guessable from the proto.

**`classOptions` must be present, even empty.** Sending `options: {}` panics
the simulator with a nil dereference that names no field.

**A caster with no rotation returns exactly 0.0 DPS.** Rotation type Auto
produces a plausible figure for every physical spec and zero for all six
casters, so the failure looks like a result. `tools/run_sims.py` loads the
action priority list each spec's own preset ships.

**A warlock with no armor, pet or curse returns about 65 DPS**, a tenth of the
real figure. Class options are taken from each preset's `DefaultOptions`.

Because all three of those failures produce a NUMBER rather than an error, the
runner enforces a floor: any result under 300 DPS fails the run. The floor is
deliberately low, since a Balance Druid lands near 420 unbuffed and that is a
real TBC Moonkin figure rather than a failure. It catches collapse, not
weakness.

## Varying an item

`--swap` replaces one slot and runs the result beside the unchanged profile, so
the answer is a difference between two runs identical in every other respect.
Several `--swap` arguments run several candidates against the same baseline.

```
python3 tools/run_sims.py --profile combat-rogue.tier-hands-only \
    --slot trinket_1 --swap 32505 --swap 30627 --swap 29383
```

```
combat-rogue.tier-hands-only, varying trinket_1, 500 iterations

  baseline               1103.5        Dragonspine Trophy
  Bloodlust Brooch       1087.5    -15.9
  Tsunami Talisman       1083.0    -20.4
  Madness of the Betrayer 1078.3   -25.1
```

**The baseline runs with the same seed as every candidate.** Two runs of the
same gear on different seeds differ by a few DPS, and an item worth a few DPS is
exactly the kind this gets asked about.

**Item id 0 empties the slot**, which is what a two-hander needs: taking one
means the off hand holds nothing, and leaving the old off hand in place would
credit the two-hander with a weapon it displaces.

**A swapped slot is bare**, carrying no enchant and no gems. They belonged to
the item they were on, and moving them to a different item would silently add
stats it does not have. What a candidate should be enchanted and gemmed with is
a separate question from what the item is worth.

## What cannot be simulated in this build

### The engine choice, settled 10 August 2026

Two wowsims lineages exist for TBC and they are NOT versions of each other.
The guild lead ruled: stay on the fork we have and drop the Feral Cat.

| | Mainline `wowsims/tbc` | Our vendored fork |
|---|---|---|
| Go | 1.18 | 1.25 |
| Headless CLI | **none**, web and wasm only | `wowsimcli` |
| Action priority lists | **0** | 21 |
| Feral Cat | **works** | parked mid-port |

Mainline has the Feral Cat and nothing else we need: no headless runner, so
every one of these 45 profiles would have to go through a web server, and no
APL, so rotations would be whatever it hardcodes. It is the 2021-era codebase.

**The trade is one spec against the entire automation surface**, which is why
the answer is to lose the spec. Reopening this means re-running everything on
an engine with no command line.

**The Feral Cat, and the reason is in the simulator rather than in our data.**
Go excludes any file whose name begins with an underscore, and in this snapshot
**11 of the 14 files in `sim/druid/feralcat` are prefixed that way**, along with
13 in `sim/druid` including Mangle, Rake, Rip, Ferocious Bite, Lacerate and
Swipe. Shred, Savage Roar, Tiger's Fury and the whole cat rotation are not
compiled into the binary. By contrast `sim/rogue` and `sim/warlock` have none
disabled.

**Enabling them is not a port, it is an implementation.** Measured: 64 compile
errors across 7 files, and the causes are not TBC problems. The parked code
wants `Spec_SpecGuardianDruid`, which is a Wrath spec; `SoulOfTheForest`, a
Cataclysm talent; `BerserkBearAura`, a Wrath talent; and `ClassSpellScaling`, a
Cataclysm scaling system. **These files came from a LATER expansion's
simulator**, dropped in as a starting point for a migration nobody finished,
which is also why the package was renamed from `feral` to `feralcat` and left
half-done. Fixing it means removing mechanics TBC does not have and rewriting
the cat against TBC rules, with nothing to validate the result against.

It used to return 171 DPS, a cat auto-attacking with no abilities, which is
about a fifth of a real melee spec. **It now returns nothing at all.** Measured
15 August 2026 on `wowsimcli` v0.0.116: every request for this spec ends in
`runtime error: invalid memory address or nil pointer dereference`, with or
without a rotation and with or without talents. Feral is a
work-in-progress port parked mid-migration in this snapshot. Fixing it means
updating the vendored wowsims to a newer commit, which would move every other
spec's numbers too, so it is a decision rather than a chore.

`tools/run_sims.py` skips the spec by name and says why, rather than letting a
threshold decide, because a threshold cannot tell a weak spec from a broken one.

## A wrong rotation does not just lower a number, it reorders items

Worth its own heading, because it is the most dangerous failure here.

The Combat Rogue's action priority list is named `swords.apl.json`, and the map
pointed at `default.apl.json`. The file did not exist, the code fell back to
rotation type Auto, and the spec read 521 DPS against 880 for the warriors,
which reads as a spec being weak.

It was not only the total that was wrong. Running the same three trinkets
against both rotations reversed the order completely:

| Candidate | On Auto | On the real rotation |
|---|---|---|
| Madness of the Betrayer | best | **worst** |
| Bloodlust Brooch | worst | **best** |

A missing rotation file now stops the run instead of falling back.
