# Version 1.0.0 verification

Release date: 2026-11-02. Playtester: THXel.

## Current package

- 489 maintained-runtime regression tests passed.
- 29 game-free current-source checks passed.
- Fresh isolated Windows Setup installation under Wine passed; all 2,167 application files and the patched game matched their expected SHA-256 values.
- The main-menu release card and history were rendered from the installed package in all five languages.
- DEB metadata and its embedded Windows Setup were checked. Debian epoch 1 ensures 1.0.0 upgrades the earlier date-numbered test packages.
- The original game remains a required input. The package contains a patch, not a full original or patched game executable.

## Gameplay evidence carried into this release

The compiled game is identical to the final tested development build (SHA-256 `64d299bdcc30b5875d4a91159e49e64a10f74f79e7b2ec5b56b119e8cd88c4a8`). The final release changes host presentation, version metadata and installer packaging.

On 2026-11-01, installed Windows 11 and Linux/Wine checks covered Tower arrival and three resets each without jumping, plus menu, item, character and restoration checks. Cheetahman's opening movement was compared with the original, including the corrected One-Hit behaviour. The internal tracker and personal adapter reported menu, Target Select, death/reset and Normal mode correctly.

## Boundaries

These checks do not establish that every seed, route or boss combination has been completed. Full natural victory/exit checks remain incomplete for Skeleton King, Mega Man, Shang Tsung, Bomberman, Ryu Dodge, Cheetahman, King Dedede and Kid Icarus. The personal OBS display itself was not verified in the final tracker check because its local service endpoint was unavailable.

The exact 1.0.0 installer was tested under Wine; its native Windows gameplay baseline is the identical game build tested on 2026-11-01. No new native Windows 1.0.0 installer test is claimed.

## Publication

The release manifest lists the exact EXE, DEB and SHA256SUMS assets. The publication workflow only accepts an existing reviewed draft whose tag matches the workflow commit and whose downloaded asset hashes and sizes match that manifest. It does not rebuild the earlier runtime or replace an already published release.
