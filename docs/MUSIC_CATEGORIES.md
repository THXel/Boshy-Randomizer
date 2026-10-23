# Optional soundtrack categories

The optional Kamilia 3 and WannaFest22 packs now use separate seeded level and boss bags. The original Boshy soundtrack retains its existing seeded mapping. Avoidances and miniboss battles count as bosses. Menu, opening, ending, victory and transition cues are not gameplay replacement music. Files without a verified category are excluded; a missing category produces an explicit error instead of mixing pools.

The runtime catalogue identifies each existing imported file by path AND SHA-256. Audio remains private and is not bundled. Existing pack manifests need no edits. Custom audio may declare `music_kind` as `level` or `boss`; this is explicit user metadata, not a filename heuristic.

## Evidence

The assignments were checked against the locally available original-game scripts extracted from the user's game copies:

- Kamilia 3: `init` binds numbered files to music variables; `TrackPlayer` selects them by room. Boss/avoidance controllers and `objMusicSync` identify battle playback. Stage 5 contains both platforming and avoidance sections, so its tracks are not all level music. `038` and `040` have no confirmed playback in this build and are excluded. `052` is the Piyo ending.
- WannaFest22: room instance creation code supplies stage music; `BossRushCtrl`, `GoemonFakeBoss`, `CatBat`, `GelgBolm`, `daisaku_part_2`, `smash_that_daisaku`, `TheManFinalCutscene` and `ParappaGameplayController` identify the corresponding sequences. Boss intro, preboss, title, clear and transition music is excluded. Stage 4's rhythm gameplay and the escape/platforming sections remain level music.
- Boshy: the literal sample cues were checked against frame event data in the supported executable. Classification follows the music cue, including Kracko's `Kirby Bos`, Dedede's `mountain stage kirby` and Sonic's Green Hill theme. This preserves native cue/channel timing and does not replace enemy sounds.

These are usage categories within the respective fangame, not genres or classifications inferred from the original commercial soundtrack's title.

## Imported tracks

### kamilia3

| File | Category |
| --- | --- |
| `001.ogg` | level |
| `002.ogg` | boss |
| `004.ogg` | level |
| `005.ogg` | boss |
| `006.ogg` | boss |
| `007.ogg` | level |
| `008.ogg` | level |
| `009.ogg` | boss |
| `010.ogg` | boss |
| `011.ogg` | level |
| `012.ogg` | level |
| `013.ogg` | level |
| `015.ogg` | boss |
| `016.ogg` | boss |
| `017.ogg` | boss |
| `018.ogg` | boss |
| `019.ogg` | level |
| `020.ogg` | boss |
| `021.ogg` | level |
| `022.ogg` | boss |
| `023.ogg` | level |
| `024.ogg` | boss |
| `025.ogg` | level |
| `026.ogg` | boss |
| `027.ogg` | level |
| `028.ogg` | boss |
| `029.ogg` | boss |
| `030.ogg` | level |
| `031.ogg` | boss |
| `032.ogg` | boss |
| `033.ogg` | boss |
| `034.ogg` | boss |
| `035.ogg` | boss |
| `036.ogg` | boss |
| `038.ogg` | excluded |
| `039.ogg` | boss |
| `040.ogg` | excluded |
| `041.ogg` | level |
| `043.ogg` | boss |
| `044.ogg` | boss |
| `045.ogg` | boss |
| `046.ogg` | level |
| `047.ogg` | level |
| `048.ogg` | boss |
| `049.ogg` | boss |
| `04B.ogg` | boss |
| `050.ogg` | boss |
| `052.ogg` | excluded |
| `053.ogg` | level |
| `054.ogg` | boss |
| `055.ogg` | boss |

### wannafest22

| File | Category |
| --- | --- |
| `music/musBackroom.ogg` | level |
| `music/musBackstage.ogg` | level |
| `music/musBossRush.ogg` | boss |
| `music/musBossRush2.ogg` | boss |
| `music/musEscape.ogg` | level |
| `music/musFinalBoss.ogg` | boss |
| `music/musSecret.ogg` | level |
| `music/musStage1Boss.ogg` | boss |
| `music/musStage1BossIntro.ogg` | excluded |
| `music/musStage1Cutscene.ogg` | excluded |
| `music/musStage1Fake.ogg` | boss |
| `music/musStage1Fortress.ogg` | level |
| `music/musStage1Lake.ogg` | level |
| `music/musStage1Woods.ogg` | level |
| `music/musStage2Boss.ogg` | boss |
| `music/musStage2Hurryup.ogg` | level |
| `music/musStage2Intro.ogg` | excluded |
| `music/musStage2Moon.ogg` | level |
| `music/musStage2Preboss.ogg` | excluded |
| `music/musStage2Puzzle.ogg` | level |
| `music/musStage3Boss.ogg` | boss |
| `music/musStage3Cave.ogg` | level |
| `music/musStage3ForestInside.ogg` | level |
| `music/musStage3ForestOutside.ogg` | level |
| `music/musStage3Windmill.ogg` | level |
| `music/musStage4Onion.ogg` | level |
| `music/musStage5Boss.ogg` | boss |
| `music/musStage5Future.ogg` | level |
| `music/musStage5Past.ogg` | level |
| `music/musStage5Title.ogg` | excluded |
| `music/musStage6Bonus.ogg` | level |
| `music/musStage6Clear.ogg` | excluded |
| `music/musStage6Grass.ogg` | level |
| `music/musStage6Mall.ogg` | level |
| `music/musStage6Sky.ogg` | level |
| `music/musStage6Storm.ogg` | level |
| `music/musStage6Title.ogg` | excluded |
| `music/musStage7Boss.ogg` | boss |
| `music/musStage7Daisaku.ogg` | boss |
| `music/musStage7Dice.ogg` | level |
| `music/musStage7Empire.ogg` | level |
| `music/musStage7Grass.ogg` | level |
| `music/musStage7Item.ogg` | level |
| `music/musStage7Minion.ogg` | level |
| `music/musStage7Rushngo.ogg` | level |
| `music/musStage7Title.ogg` | excluded |
| `music/musTransition.ogg` | excluded |

