# TargetSearchSteps

`UiPath.UIAutomationNext.Enums.TargetSearchSteps`

The selector types used to identify the target UI element. This is a `[Flags]` enum — values can be combined using bitwise OR.

## Values

| Value | Description |
|-------|-------------|
| `TargetSearchSteps.None` | No targeting method selected. |
| `TargetSearchSteps.Selector` | Strict selector. |
| `TargetSearchSteps.FuzzySelector` | Fuzzy selector. |
| `TargetSearchSteps.Image` | Image. |
| `TargetSearchSteps.TextOcr` | OCR text. |
| `TargetSearchSteps.TextNative` | Native text. |
| `TargetSearchSteps.CV` | Computer Vision. |
| `TargetSearchSteps.Semantic` | Semantic. |
| `TargetSearchSteps.SemanticSelector` | Semantic selector. |

## Usage

Reference values as `TargetSearchSteps.<Value>`, e.g. `TargetSearchSteps.FuzzySelector`. Combine flags with bitwise OR: `TargetSearchSteps.Selector | TargetSearchSteps.FuzzySelector`.
