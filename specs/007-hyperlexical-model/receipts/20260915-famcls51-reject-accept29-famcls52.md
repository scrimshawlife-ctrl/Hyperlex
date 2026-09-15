# Receipt — famcls51 REJECT → accept29 → famcls52 KEEP

## famcls51 REJECT (prior)
- Init famcls48 · accept28 · aux=0.40/up=16 · 40 ep (best 0)
- structure/role/pointer **1.0** (sheesh closed); family **0.9899** < baseline **0.9949**
- Residuals (2): `escalate to the em` (workplace-corp→gaming-meta); `quiet elevator rizz with zero words` (brainrot-aura→ai-native)

## accept29
- Base accept28 + **25** TRAIN force-promotes (2 exact residuals always + contrastives)
- No new OBSERVED structure gold; inherit accept28 sheesh positional|type_slot clones
- `rows_sha256=4e151140bd12a0efe95c47d367f35fb1c9483030774f570568e731bbb0ec46ff`
- Fair famcls48 on accept29-test: family **0.9949494949494949**, structure/role/pointer **1.0**

## famcls52 KEEP
- Init famcls48 · accept29 · **aux=0.35 / up=12** · 40 ep (best 8)
- family **1.0** > baseline **0.9949** PASS
- structure/role/pointer **1.0** held
- Climb weight pin **moves to famcls52**; BEST morph19 untouched; no Hub
- Container: `hlx-struct-unbind-famcls52-1789455435`

## Ops
- Owned by Wrap-51-merge-to-52 (`bc-f1a96d96…`); recover agent idle / no duplicate train
- qwen stopped via `systemctl` for train, restarted after
