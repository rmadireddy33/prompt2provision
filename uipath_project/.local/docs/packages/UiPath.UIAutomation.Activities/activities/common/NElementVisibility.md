# NElementVisibility

`UiPath.UIAutomationNext.Enums.NElementVisibility`

Controls whether the activity also checks that the UI element is visible before performing the action.

## Values

| Value | Description |
|-------|-------------|
| `NElementVisibility.None` | No visibility checks will be performed. |
| `NElementVisibility.Interactive` | Ensures that the element is present and not hidden by other elements from the target application, ignoring page scroll and obstructions by other apps, or the fact that the application is minimized. This applies to the Fuzzy selector targeting method. |
| `NElementVisibility.Visible` | Ensures that the element is visible on the screen. |
| `NElementVisibility.Legacy` | Ensures that the element is visible on the screen. (Legacy mode) |

## Usage

Reference values as `NElementVisibility.<Value>`, e.g. `NElementVisibility.Interactive`.
