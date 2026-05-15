---
name: uia-configure-target
description: "Primary entry point for configuring a UiPath target -- ensures the screen and element exist in the Object Repository, checking for existing entries before creating new ones. Returns the OR reference ID. Supports batch element configuration via pipe-separated list (e.g., --elements \"Five button | Plus button | Equals button\") to avoid redundant window captures and screen lookups. Use when asked to 'configure target', 'configure application', 'set up target', 'set up application', 'create target in OR', 'find or create target', 'get OR reference for an element', 'select application window', 'create window selector', 'create selector', 'get selector for', 'find selector', 'add target to object repository', or when an orchestrator agent needs an OR element reference for a UI element. Trigger this whenever building automation workflows that need reliable OR references."
argument-hint: "--window <description> [--elements <descriptions>] [--semantic] [--no-improve] [--activity <type>] [--project-dir <path>]"
allowed-tools: Bash, Read, Write, Agent, AskUserQuestion
---

Ensure a UI target (screen + elements) exists in the Object Repository. Checks for existing OR entries first -- creates new ones only when needed. Returns the OR reference ID(s).

`$ARGUMENTS` format: `--window <description> [--elements <descriptions>] [--semantic] [--no-improve] [--activity <type>] [--project-dir <path>]`

**IMPORTANT: Use forward slashes in ALL paths.**

**IMPORTANT: Follow the steps mechanically. Do NOT add commentary or analysis between steps.**

**IMPORTANT: For full details on Object Repository concepts (Application, Screen, Element) and the complete CLI command reference, see [`object-repository.md`](../../references/object-repository.md).**

## CLI

```
CLI="uip rpa uia"
```

If `$PROJECT_DIR` is set, append it: `CLI="uip rpa uia --project-dir \"$PROJECT_DIR\""`. All subsequent `"$CLI" ...` commands will automatically include it.

## Input Parsing

Extract from `$ARGUMENTS`:

- `--window <description>` -> `$WINDOW`. Window/tab description to target.
- `--elements <descriptions>` -> pipe-separated list of target element descriptions (optional). Also accepts `--element`. Use `|` to separate multiple elements (e.g., `"Five button | Plus button | Equals button"`). If omitted, run in **screen-only mode**.
- `--semantic` -> `$CONFIGURE_SEMANTIC=true` (default: `false`). Enable Semantic (NLP) secondary targeting. Ignored in screen-only mode.
- `--no-improve` -> `$NO_IMPROVE=true` (default: `false`). Skip selector improvement steps.
- `--activity <type>` -> `$ACTIVITY_TYPE` (default: `Click`). Valid values: `Click`, `GetText`, `SetText`, `TypeInto`, `Check`, `Hover`, `Highlight`, `SelectItem`, `GetAttribute`, `TakeScreenshot`, `KeyboardShortcut`, `MouseScroll`, `DragAndDrop`, `InjectJsScript`, `CheckState`, `FindElements`, `SetFocus`, `CheckElement`, `ElementScope`, `WindowOperations`.
- `--project-dir <path>` -> `$PROJECT_DIR` (optional). UiPath project directory. Passed through to all CLI commands and subagent prompts.

If `$WINDOW` is not provided, ask the user which application/window to target.

**Parse elements:** Split the `--elements` value on `|` and trim whitespace from each entry to produce `$ELEMENT_LIST` (array). Derive `$ELEMENT_NAMES` by converting each entry to Title Case (e.g., "add to cart button" -> `Add To Cart Button`).

Derive `$SCREEN_NAME` from `$WINDOW` by converting to Title Case (e.g., "google chrome" -> `Google Chrome`).

## Definition Files

- `WindowDefinition.json` -- window/screen definition. Created by `resolve-default-selector` in TARGET-2. Used for OR screen registration.
- `Target_N_Definition.json` -- per-element definitions. Created in TARGET-5 by copying `WindowDefinition.json` then overlaying element fields via `resolve-default-selector`. Used for OR element registration.

Fields: `WindowSelector`, `PartialSelector`, `SemanticSelector`, `ActivityType`, `SelectionStrategy`, `WindowNodeId`, `ElementNodeId`.

## Error Handling

After every CLI command, check the exit code. If non-zero, show the CLI's stderr/stdout to the user and stop. Common failures:
- **snapshot capture**: application not running, window minimized, or not visible on screen
- **snapshot filter**: tree file missing (prior capture may have failed)
- **resolve-default-selector**: invalid ref or element not found in tree

## TARGET-1: Prepare Working Folder

Always start from a clean folder -- never reuse a previous run's folder. Stale artifacts from a prior run may reference a different window or app state.

```bash
rm -rf .local/.uia/.configure-target
mkdir -p .local/.uia/.configure-target
```

Set `$WORK_FOLDER` to the **absolute path** of `.local/.uia/.configure-target` (the CLI requires absolute paths).

## TARGET-2: Create Window Selector

Capture the top-level tree (the definition file doesn't exist yet -- the CLI treats this as empty selectors):

```bash
"$CLI" snapshot capture --folder-path "$WORK_FOLDER" --definition-file-path "$WORK_FOLDER/WindowDefinition.json"
```

This produces `TopLevelNodeTreeInfo.json`.

View the window tree:

```bash
"$CLI" snapshot filter --folder-path "$WORK_FOLDER" --definition-file-path "$WORK_FOLDER/WindowDefinition.json" --source window
```

Read the output file. Match `$WINDOW` against window titles and app names (partial, case-insensitive). Browser tabs are labeled `BrowserTab` with `b` prefix refs (e.g., `b3`) -- prefer those over native browser windows for web apps. Regular windows use `w` prefix refs (e.g., `w3`).

Save the matching ref as `$WREF`. If no match, present the list and ask the user.

Get the window selector (the CLI creates `WindowDefinition.json` and writes `WindowSelector` + `WindowNodeId` into it):

```bash
"$CLI" selector-intelligence resolve-default-selector --folder-path "$WORK_FOLDER" --refs "$WREF:$WORK_FOLDER/WindowDefinition.json" --from-snapshot
```

**Stabilize title if needed:** Read `$WORK_FOLDER/WindowDefinition.json` and inspect the `WindowSelector`'s `title` attribute (if present). The `title` often reflects the current page content (e.g., article headline, search query, email subject) rather than just the application identity. If the title contains volatile page-specific content beyond the app name, simplify it — keep only the stable app-identifying portion with wildcards (e.g., `title='*10 Unread - dan@ - Outlook*'` → `title='*Outlook*'`). The kept portion must be a substring of the original title value (ignoring wildcards) so it still matches the current window. If the title already looks stable (e.g., a desktop app like `title='Calculator'`), leave it as-is. If a change is needed, use the CLI to write it back:

```bash
"$CLI" target-app update-definition \
  --definition-file-path "$WORK_FOLDER/WindowDefinition.json" \
  --window-selector "$STABILIZED_WINDOW_SELECTOR"
```

**If `$ELEMENT_LIST` is not empty**, capture the app-level tree now (window selector is set):

```bash
"$CLI" snapshot capture --folder-path "$WORK_FOLDER" --definition-file-path "$WORK_FOLDER/WindowDefinition.json"
```

This produces `ApplicationLevelNodeTreeInfo.json`, `ApplicationLevelApplicationMetadata.json`, and `ApplicationScreenshot.jpg`.

## TARGET-3: Search for Screen in Object Repository

```bash
"$CLI" object-repository get-screens --definition-file-path "$WORK_FOLDER/WindowDefinition.json"
```

Initialize `$SCREEN_REF_ID` to empty.

**If the table has rows:** compare each row against `$WINDOW` to find the best match:

- **Name match** (case-insensitive): strong signal.
- **Selector match**: if the stored window selector targets the same application and window title, strong signal.

**Confident match found:** save the screen's `ReferenceId` as `$SCREEN_REF_ID`.

**Multiple plausible matches:** list the candidates and ask the user to pick.

**If the table is empty or the command fails** -- leave `$SCREEN_REF_ID` empty.

**Screen-only mode** (no `--elements`): skip to TARGET-6.

## TARGET-4: Search for Existing Elements in Object Repository

**Skip if `$SCREEN_REF_ID` is empty** (no screen found -- elements can't exist). Mark all elements as needing creation and proceed to TARGET-5.

```bash
"$CLI" object-repository get-elements --screen-reference-id "$SCREEN_REF_ID"
```

**If elements exist:** compare each row against EVERY element in `$ELEMENT_LIST` to find matches:

- **Name match** (case-insensitive, allowing minor wording differences): strong signal.
- **Semantic selector match**: if the stored semantic description refers to the same UI element, strong signal.
- **Selector match**: if the stored selector targets the same control type with similar identifying attributes, supporting signal.
- If a screenshot file path is present and the match is uncertain, read the screenshot for visual confirmation.

For each element: **confident match** -> record `{$ELEMENT_NAME, $ELEMENT_REF_ID, found}` (skips TARGET-5 through TARGET-8). **No match** -> mark as needing creation.

Collect elements needing creation into `$ELEMENTS_TO_CREATE` (list of `{$INDEX, $ELEMENT, $ELEMENT_NAME}`).

If `$ELEMENTS_TO_CREATE` is empty, skip to **Output**.

## TARGET-5: Create Element Selectors

Search for elements using `--query`:

- **Multi-word query** (e.g., `"add to cart"`) — matches elements containing at least 51% of the words. So `"add to cart"` matches an element labeled `"Add to cart"` or `"Cart add item"`.
- **Comma-separated queries** (e.g., `"username,password,login"`) — OR logic, matches elements containing any of the terms.

Combine both to search for multiple elements at once:

```bash
"$CLI" snapshot filter --folder-path "$WORK_FOLDER" --definition-file-path "$WORK_FOLDER/WindowDefinition.json" --query "username,password,login"
```

Refine with role filters if needed (also comma-separated OR):

```bash
"$CLI" snapshot filter --folder-path "$WORK_FOLDER" --definition-file-path "$WORK_FOLDER/WindowDefinition.json" --query "username,password,login" --role "edit,button"
```

Narrow to a specific subtree using `--subtree` with an element ref (e.g., a container found in a prior filter). This uses that element as the root instead of the full tree:

```bash
"$CLI" snapshot filter --folder-path "$WORK_FOLDER" --definition-file-path "$WORK_FOLDER/WindowDefinition.json" --subtree e5 --query "username"
```

Use `--subtree` when the full tree is large and you already know which container holds the target elements.

The tree format shows each matched element as:
```
  ✓ Button [ref=e42] "Add to cart" 
```

Some elements may have an additional `[sap]` tag after the ref:
```
  ✓ Input [ref=e15] [sap] "Username"
```

The `[sap]` tag indicates the element belongs to a SAP web framework (Fiori/UI5, Web GUI, or Ariba). SAP framework elements carry richer, more stable attributes that produce more reliable selectors.

**SAP element selection rule:** Before saving `$EREF`, check the query results for elements tagged `[sap]`. If both a plain HTML element and a `[sap]` element match the target description, always pick the `[sap]` element — even if the plain element looks like a more direct match (e.g., a plain `INPUT` vs a SAP-tagged `InputBox` wrapping it).

Full tree to browse manually:

```bash
"$CLI" snapshot filter --folder-path "$WORK_FOLDER" --definition-file-path "$WORK_FOLDER/WindowDefinition.json" --max-depth 40
```

Match each element description to a tree result and save its ref as `$EREF_N`.

### Retry capture with UIA framework

If any element could not be confidently matched in the tree (no results from filter queries, or results exist but none correspond to the described element), the default capture framework may have produced a tree that lacks those elements. Before retrying, check whether a different framework would help:

1. Read `$WORK_FOLDER/ApplicationLevelApplicationMetadata.json` and check the `"subsystem"` field.
2. **Only retry if `subsystem` is `"aa"`** (Active Accessibility) — UIA queries a different accessibility provider and may surface elements that AA missed. For any other subsystem (`"uia"`, `"webctrl"`, `"html"`, `"java"`, etc.), the framework-specific tree is richer than what UIA would produce. Skip the retry and proceed to screenshot disambiguation.

To retry:

```bash
rm -f "$WORK_FOLDER/ApplicationLevelNodeTreeInfo.json" "$WORK_FOLDER/ApplicationLevelApplicationMetadata.json" "$WORK_FOLDER/ApplicationScreenshot.jpg"
"$CLI" snapshot capture --folder-path "$WORK_FOLDER" --definition-file-path "$WORK_FOLDER/WindowDefinition.json" --framework uia
```

Re-run the filter queries above against the new tree and continue matching.

**If any element has multiple candidates or no clear match from the tree alone**, read the screenshot once to disambiguate:

```
Read "$WORK_FOLDER/ApplicationScreenshot.jpg"
```

Cross-reference the screenshot (visual) with the tree results (structural) to resolve the ambiguity. If still ambiguous after checking the screenshot, list candidates and ask the user.

Create per-element definition files by copying the window definition:

```bash
cp "$WORK_FOLDER/WindowDefinition.json" "$WORK_FOLDER/Target_1_Definition.json"
cp "$WORK_FOLDER/WindowDefinition.json" "$WORK_FOLDER/Target_2_Definition.json"
# ... one per element
```

**Do NOT use `--from-snapshot` here.** Element selectors must probe the live element. Get all selectors in one CLI call with comma-separated `--refs` entries. The CLI parses the tree once, resolves each selector, and writes `PartialSelector`, `ElementNodeId`, and `ActivityType` into each definition file:

```bash
"$CLI" selector-intelligence resolve-default-selector --folder-path "$WORK_FOLDER" \
  --refs "$EREF_1:$WORK_FOLDER/Target_1_Definition.json,$EREF_2:$WORK_FOLDER/Target_2_Definition.json" \
  --activity-type $ACTIVITY_TYPE
```

## TARGET-6: Improve Selectors

**Skip if `$NO_IMPROVE` is true.** Proceed to TARGET-7.

### Assess selector reliability

**Screen-only mode:** Read `$WORK_FOLDER/WindowDefinition.json` and assess the `WindowSelector`.

**Element mode:** For each element in `$ELEMENTS_TO_CREATE`, read `$WORK_FOLDER/Target_${INDEX}_Definition.json` and assess the `PartialSelector`. Also assess the `WindowSelector` once (from the first element).

**Assessment criteria -- a selector is RELIABLE if ALL of the following hold:**

1. **Uses reliable attributes for its tag type.** Each tag has at least one developer-assigned or semantic identifier (e.g., `automationid`, `name`, `role`, `aria-label`, `id`, `app`, `cls`). Fragile if all identifying attributes are last-resort or unreliable for their tag type.

2. **Not positionally dependent.** The selector does NOT rely solely on `idx`, `tableRow` or `tableCol` without any stable identifier alongside them.

3. **Attribute values are stable.** Watch for auto-generated IDs (purely numeric like `id='89763184740'`), CSS-in-JS hashes (`class='css-1wq41pf'`), component-path IDs with 3+ dot-separated structural segments, or framework hashes in tag names.

4. **Activity-appropriate attributes.** For `GetText`/`SetText`/`TypeInto`: must NOT use content-reflecting attributes (`text`, `aaname`, `visibleinnertext`, `innertext`) as primary identifiers. For `Check`/`Uncheck`: must NOT rely on state attributes (`checked`, `aastate`). For `SelectItem`: must NOT rely on `selecteditem` or `value`.

5. **Good structure.** A typical selector has ~2 tags. Selectors with 4+ tags are over-specified and fragile. Each tag should have 2-3 meaningful attributes.

6. No `css-selector` attribute.

Mark each selector as `RELIABLE` or `NEEDS_IMPROVEMENT`.

**If all selectors are RELIABLE:** skip improvement entirely and proceed to TARGET-7.

### Retry with snapshot before improving

**Skip for the window selector** (window selectors always use `--from-snapshot` -- nothing different to try).

Collect all element refs marked `NEEDS_IMPROVEMENT`. Read each element's `Target_${INDEX}_Definition.json` to get its `ElementNodeId`.

**Batch the snapshot retry in a single CLI call** using comma-separated `--refs` entries. The CLI writes each new selector directly into the definition file:

```bash
"$CLI" selector-intelligence resolve-default-selector --folder-path "$WORK_FOLDER" \
  --refs "$EREF_1:$WORK_FOLDER/Target_1_Definition.json,$EREF_2:$WORK_FOLDER/Target_2_Definition.json" \
  --from-snapshot
```

Re-read each updated `Target_${INDEX}_Definition.json` and re-assess the new `PartialSelector` using the same criteria above.

If the new selector is `RELIABLE`, mark it as such and skip improvement for it.

**Restore live-probe selectors for all non-RELIABLE elements.** The `--from-snapshot` call overwrote the definition files. For every element that was NOT promoted to `RELIABLE` by the snapshot selector, call `resolve-default-selector` again **without** `--from-snapshot` to restore the original live-probe selector — the snapshot selector may look passable but is still worse than the live-probe default:

```bash
"$CLI" selector-intelligence resolve-default-selector --folder-path "$WORK_FOLDER" \
  --refs "$EREF_X:$WORK_FOLDER/Target_X_Definition.json,$EREF_Y:$WORK_FOLDER/Target_Y_Definition.json" \
  --activity-type $ACTIVITY_TYPE
```

**If all selectors are now RELIABLE:** skip improvement entirely and proceed to TARGET-7.

**IMPORTANT: Do NOT attempt to fix selectors yourself (e.g., by removing attributes or rewriting tags). Selectors still marked `NEEDS_IMPROVEMENT` MUST go through the uia-improve-selector subagent below -- it validates candidates against the live application to ensure correctness.**

### Run improvement on fragile selectors only

Collect only the elements marked `NEEDS_IMPROVEMENT` into `$ELEMENTS_TO_IMPROVE`. If the window selector is `NEEDS_IMPROVEMENT`, include it too.

**Screen-only mode (window needs improvement):** Spawn a single subagent. Use `$DEF_FILE = $WORK_FOLDER/WindowDefinition.json` and `$AGENT_FOLDER = $WORK_FOLDER` (no isolation needed -- only one agent runs).

**Element mode:** Spawn one `Agent` per element in `$ELEMENTS_TO_IMPROVE`, **all in a single message** so they run in parallel. Each improves window + element together. If the window selector is `RELIABLE` but some elements need improvement, the subagent still receives the window selector in the definition -- it will only change the element selector.

**Isolate per-agent artifacts.** The uia-improve-selector CLI writes fixed-name artifacts into its `--folder`. Parallel agents pointing at the same folder would overwrite each other. Give each agent its own subfolder, seeded with the already-captured snapshot so it skips re-capture:

```bash
# Element mode only -- run once before spawning agents
for INDEX in <indices of $ELEMENTS_TO_IMPROVE>; do
  SUBFOLDER="$WORK_FOLDER/improve_${INDEX}"
  mkdir -p "$SUBFOLDER"
  # All copies are best-effort -- if a snapshot step failed earlier, the missing file
  # will surface as a clearer error when the subagent tries to use it.
  cp "$WORK_FOLDER/ApplicationLevelNodeTreeInfo.json"        "$SUBFOLDER/" 2>/dev/null || true
  cp "$WORK_FOLDER/ApplicationLevelApplicationMetadata.json" "$SUBFOLDER/" 2>/dev/null || true
  cp "$WORK_FOLDER/ApplicationScreenshot.jpg"                "$SUBFOLDER/" 2>/dev/null || true
  cp "$WORK_FOLDER/TopLevelNodeTreeInfo.json"                "$SUBFOLDER/" 2>/dev/null || true
  cp "$WORK_FOLDER/TopLevelApplicationMetadata.json"         "$SUBFOLDER/" 2>/dev/null || true
done
```

The definition files stay in `$WORK_FOLDER` (each `Target_${INDEX}_Definition.json` is already unique). The subagent updates its definition file in place, so TARGET-7/8 pick up improved selectors with no copy-back step.

**IMPORTANT: Each agent must be a separate, self-contained `Agent` tool call. Use `model: "sonnet"` for each.**

Use the prompt below for each, with these substitutions:
- `$DEF_FILE` -> `$WORK_FOLDER/Target_${INDEX}_Definition.json` (element mode) or `$WORK_FOLDER/WindowDefinition.json` (screen-only mode)
- `$AGENT_FOLDER` -> `$WORK_FOLDER/improve_${INDEX}` (element mode) or `$WORK_FOLDER` (screen-only mode)

---

You are improving UiPath selectors to make them more robust. Follow the instructions in the skill file mechanically.

1. Read `../uia-improve-selector/SKILL.md` (relative to the directory this file is in) to learn the full procedure.
2. Execute the skill steps with these arguments: `$DEF_FILE --folder $AGENT_FOLDER --mode improve --quiet` (add `--project-dir $PROJECT_DIR` if `$PROJECT_DIR` is set).
3. The definition file contains the current selectors. Improve whatever is present -- window selector only or window + element selector together.

---

Wait for all agents to complete.

**Element mode only:** if the window selector was improved, read the `WindowSelector` from the first improved element's definition and update `$WORK_FOLDER/WindowDefinition.json` with it (so TARGET-8 screen creation uses the improved window selector).

## TARGET-7: Configure Semantic Targeting

**Skip if `$CONFIGURE_SEMANTIC` is `false` or screen-only mode.** Proceed to TARGET-8.

For each element in `$ELEMENTS_TO_CREATE`:

Derive a natural-language description of the element from `$ELEMENT` (e.g., `"Submit button in the order form"`). Save as `$SEMANTIC_SELECTOR`.

Read `$WORK_FOLDER/Target_${INDEX}_Definition.json`, set `"SemanticSelector": "$SEMANTIC_SELECTOR"`. Write back.

## TARGET-8: Register in Object Repository

**If `$SCREEN_REF_ID` is empty** (no matching screen found in TARGET-3), create it. First, write the screen name and description into the definition file. Compose a description that captures what the screen represents in the application — include the app name, the purpose of the screen/page, and any distinguishing context (e.g., `"The main login page of the Acme HR portal"`, `"Calculator application main window"`):

```bash
"$CLI" target-app update-definition \
  --definition-file-path "$WORK_FOLDER/WindowDefinition.json" \
  --name "$SCREEN_NAME" \
  --description "$SCREEN_DESCRIPTION"
```

Then register:

```bash
"$CLI" object-repository create-screen --definition-file-path "$WORK_FOLDER/WindowDefinition.json"
```

Save stdout as `$SCREEN_REF_ID`. If the command fails, show the error and stop.

**Screen-only mode:** skip to **Output**.

**Update each element definition file with name and description** before registration. For each element in `$ELEMENTS_TO_CREATE`, compose a description that explains the element's role and location within the screen — include what type of control it is, what it does, and where it sits in the UI (e.g., `"The Submit Order button at the bottom of the checkout form"`, `"Username text input field in the login panel"`):

```bash
"$CLI" target-anchorable update-definition \
  --definition-file-path "$WORK_FOLDER/Target_1_Definition.json" \
  --name "$ELEMENT_NAME_1" \
  --description "$ELEMENT_DESCRIPTION_1"
"$CLI" target-anchorable update-definition \
  --definition-file-path "$WORK_FOLDER/Target_2_Definition.json" \
  --name "$ELEMENT_NAME_2" \
  --description "$ELEMENT_DESCRIPTION_2"
# ... one per element
```

**Create all elements in a single batched CLI call** using comma-separated definition file paths:

```bash
"$CLI" object-repository create-elements \
  --screen-reference-id "$SCREEN_REF_ID" \
  --snapshot-folder-path "$WORK_FOLDER" \
  --definition-file-paths "$WORK_FOLDER/Target_1_Definition.json,$WORK_FOLDER/Target_2_Definition.json"
```

Each output line prints `$ELEMENT_NAME -> $ELEMENT_REF_ID` (or `FAILED: $ELEMENT_NAME (error)`). Parse the output to collect `{$ELEMENT_NAME, $ELEMENT_REF_ID, created}` for every element.

Present the results concisely: screen reference ID, element reference IDs (table if multiple). No observations, no quality notes, no suggestions.

**Important:** Follow the TARGET steps sequentially with discipline. If you get sidetracked by errors, retries, or user questions, always return to complete the remaining steps in the flow.
