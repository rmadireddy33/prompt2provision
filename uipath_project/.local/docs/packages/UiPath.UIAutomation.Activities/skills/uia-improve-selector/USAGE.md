# uia-improve-selector — standalone invocation

The skill is invoked by an agent (not via the CLI). Each recipe below shows (1) the CLI commands the caller runs to stage the folder, (2) the arguments to pass when invoking the skill, and (3) the CLI command to write the improved result back to its source.

## Modes

Pass `--mode <recover|improve>` to tell the skill what kind of fix you want:

- **`recover`** — the selector is *broken* (element not found, selector stopped working, runtime failure). The skill assumes the original selector no longer matches and rewrites it against the current DOM. Use this for failure-triggered fixes.
- **`improve`** — the selector still *works* but is fragile (positional, auto-generated IDs, content-reflecting attributes, etc.). The skill produces a more robust rewrite that still targets the same element.

If `--mode` is omitted, the skill infers from the invocation phrasing ("fix", "stopped working", "element not found" → `recover`; "improve", "robust", "harden" → `improve`). Pass it explicitly for non-interactive callers where no natural-language prompt is available.

## Form 1 — raw selector strings (quickest, least context)

Use when you only have selector strings (from an error log, clipboard, etc.). The skill will synthesize `$FOLDER/Target_Definition.json` from the flags. Defaults `--activity-type` to `Click` unless overridden.

**Stage:**
```bash
FOLDER="/tmp/.uia/.improve-selector-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$FOLDER"
# app must be running on the target screen, or pre-populate $FOLDER (see "Preparing the folder")
```

**Invoke the skill with:**
```
--window-selector "<wnd app='chrome.exe' />"
--partial-selector "<webctrl tag='INPUT' aaname='Email' />"
--activity-type GetText
--folder "$FOLDER"
--mode recover
```

Pass `--activity-type` whenever the target activity isn't `Click`; it shapes the improvement rules (e.g., `GetText` avoids content-reflecting attributes like `innertext`). Valid values: `Click`, `GetText`, `SetText`, `TypeInto`, `Check`, `Hover`, `Highlight`, `SelectItem`, `GetAttribute`, `TakeScreenshot`, `KeyboardShortcut`, `MouseScroll`, `DragAndDrop`, `InjectJsScript`, `ExtractData`, `CheckState`, `FindElements`, `SetFocus`, `CheckElement`.

**Write back:** read the improved selectors from the skill's output; nothing to persist automatically.

## Form 2 — XAML activity (recommended when you have activity + workflow)

**Stage:**
```bash
uip rpa uia target-anchorable get-definition \
  --folder-path "$FOLDER" \
  --definition-file-path "$FOLDER/Target_Definition.json" \
  --activity-id "$ACT_REF" \
  --workflow-file-path "$XAML_REL_PATH"
```

**Invoke the skill with:**
```
"$FOLDER/Target_Definition.json"
--folder "$FOLDER"
--mode recover
```

**Write back:**
```bash
uip rpa uia target-anchorable link \
  --definition-file-path "$FOLDER/Target_Definition.json" \
  --workflow-file-path "$XAML_REL_PATH" \
  --activity-id "$ACT_REF"
```

## Form 3 — Object Repository reference (recommended when you have an OR ref)

**Stage:**
```bash
uip rpa uia object-repository get-element-definition \
  --folder-path "$FOLDER" \
  --definition-file-path "$FOLDER/Target_Definition.json" \
  --reference-id "$OR_REF"
```

**Invoke the skill with:**
```
"$FOLDER/Target_Definition.json"
--folder "$FOLDER"
--mode recover
```

**Write back:** `object-repository update-element` (when available).

**Prefer Form 2/3 over Form 1 when a ref exists.** The `get-definition` commands pull `ActivityType` from source automatically, so the improve run uses accurate rules for that activity (e.g., `GetText` avoids content-reflecting attributes, `Check` avoids state attributes). Form 1 requires the caller to pass `--activity-type` explicitly -- it defaults to `Click` if omitted, which produces suboptimal selectors for other activity types.

## Preparing the folder

The skill runs `snapshot capture` automatically when tree files are missing, so you only need to pre-stage anything for offline or recover scenarios. The table below covers every situation — pick the one that matches your state:

| Mode | Situation | Pre-stage in `$FOLDER` | Def file `WindowSelector` | Capture |
|---|---|---|---|---|
| **(a) Offline, full runtime data** | App not reachable; runtime data shipped from another machine | `ApplicationLevelNodeTreeInfo.json` (+ screenshot, metadata) | as-received | skip |
| **(b.1) Failure dump available** | Runtime dumped trees at the failure moment | `ApplicationLevelNodeTreeInfo.json` from the dump | as-received | skip |
| **(b.2) Live, window selector works** | Element search failed; the window itself is still findable | nothing | keep valid `WindowSelector` | `snapshot capture` → produces app-level tree |
| **(c) Live, window selector broken** | Window itself can't be found at runtime | nothing | leave as-is (even broken) | `snapshot capture` → writes top-level tree first, then fails at finding the app; the top-level tree on disk is what's needed |

**Mode (c) note:** `snapshot capture` with a broken `WindowSelector` returns a non-zero exit and stderr like "Could not find application window". That's expected — before failing, it writes `TopLevelNodeTreeInfo.json` to `$FOLDER`. The skill picks that up and recovers the window selector from it. If you pre-stage a top-level tree yourself, the capture is skipped entirely.
