# Target System

The target system defines how UI Automation activities locate application windows and UI elements at runtime. There are two main target types used across activities: **TargetAnchorable** (for locating UI elements within an application) and **TargetApp** (for locating the application window itself). Together, they form a hierarchical targeting model: TargetApp identifies the application, while TargetAnchorable identifies specific elements within it.

## TargetAnchorable

`TargetAnchorable` is used by most UI element activities (Click, Type Into, Get Text, etc.) to locate a specific element within an application window. It supports selectors, anchors, fuzzy matching, and offset configurations.

**Inherits from: `Target`**
**Latest version: V6**

### Own Properties

| Property | Display Name | Type | Description |
|----------|-------------|------|-------------|
| `PointOffset` | Click offset | [`PointOffset`](#pointoffset) | The offset values used to perform the click. The default is the center of the target. |
| `RegionOffset` | Area | [`RegionOffset`](#regionoffset) | The offset values for the area used to perform the action. |
| `ElementVisibilityArgument` | Visibility check | `InArgument<NElementVisibility>` | When enabled, the activity also checks whether the UI element is visible or not. |
| `IsResponsive` | Responsive websites | `bool` | Enable responsive websites layout. Default: `false`. |
| `ScopeSelectorArgument` | Window selector (Application instance) | `InArgument<string>` | Selector for the application window. Only applicable when Window attach mode is set to Application instance. |
| `WaitForReadyArgument` | Wait for page load | `InArgument<NWaitForReady>` | Before performing the action, wait for the application to become ready to accept input. The options are: None - does not wait for the target to be ready; Interactive - waits until only a part of the app is loaded; Complete - waits for the entire app to be loaded. **Project setting.** |
| `SemanticSelectorArgument` | Semantic selector | `InArgument<string>` | A semantic description that defines the target. |

### Inherited Properties (from Target)

| Property | Display Name | Type | Description |
|----------|-------------|------|-------------|
| `FullSelectorArgument` | Strict selector | `InArgument<string>` | The strict selector generated for the target UI element. |
| `FuzzySelectorArgument` | Fuzzy selector | `InArgument<string>` | The fuzzy selector parameters. |
| `SearchSteps` | Targeting methods | [`TargetSearchSteps`](TargetSearchSteps.md) | The selector types to use for identifying the element. It can be set to any combination of Strict selector, Fuzzy selector, or Image. Default: `TargetSearchSteps.None`. |
| `ImageAccuracyArgument` | Image accuracy | `InArgument<double>` | Indicates the accuracy level for image matching. Default value is 0.8. |
| `ImageOccurrenceArgument` | Image occurrence | `InArgument<int>` | Indicates a specific occurrence to be used, when multiple matches are found. A value greater than 0 indicates the nth occurrence (1-based index). Default value is 0, meaning no specific occurrence will be used. |
| `ImageFindModeArgument` | Image find mode | `InArgument<NImageFindMode>` | Indicates the algorithm used for image matching. Default value is Find enhanced all. |
| `NativeTextArgument` | Native text | `InArgument<string>` | The text to find to identify the UI element. |
| `NativeTextOccurrenceArgument` | Native text occurrence | `InArgument<int>` | Indicates a specific occurrence to be used, when multiple matches are found. Default value is 0, meaning no specific occurrence will be used. |
| `IsNativeTextCaseSensitive` | Native text case-sensitive | `bool` | Indicates whether text matching is case-sensitive. Default: `false`. |
| `SemanticElementType` | Semantic element type | [`NSemanticElementType`](NSemanticElementType.md) | Indicates the semantic element type. Default: `NSemanticElementType.None`. |
| `SemanticTextArgument` | Semantic Text | `InArgument<string>` | Indicates the text identified using AI-based capabilities. |
| `CvType` | CV Control type | [`UIVisionCategoryType`](UIVisionCategoryType.md) | Indicates the type of control identified using Computer Vision. Default: `UIVisionCategoryType.None`. |
| `CvTextArgument` | CV Text | `InArgument<string>` | Indicates the text identified using Computer Vision. |
| `CvTextOccurrenceArgument` | CV Text occurrence | `InArgument<int>` | Indicates a specific occurrence to be used, when multiple matches are found. Default value is 0, meaning no specific occurrence will be used. |
| `CvTextAccuracyArgument` | CV Text accuracy | `InArgument<double>` | Indicates the accuracy level for OCR text matching. Default value is 0.7. |

### XAML Syntax

```xml
<uix:TargetAnchorable Version="V6">
  <uix:TargetAnchorable.PointOffset>
    <uix:PointOffset />
  </uix:TargetAnchorable.PointOffset>
  <uix:TargetAnchorable.RegionOffset>
    <uix:RegionOffset />
  </uix:TargetAnchorable.RegionOffset>
  <uix:TargetAnchorable.ElementVisibilityArgument>
    <InArgument x:TypeArguments="uix:NElementVisibility" />
  </uix:TargetAnchorable.ElementVisibilityArgument>
  <uix:TargetAnchorable.WaitForReadyArgument>
    <InArgument x:TypeArguments="uix:NWaitForReady" />
  </uix:TargetAnchorable.WaitForReadyArgument>
  <uix:TargetAnchorable.SemanticSelectorArgument>
    <InArgument x:TypeArguments="x:String" />
  </uix:TargetAnchorable.SemanticSelectorArgument>
  <uix:TargetAnchorable.FullSelectorArgument>
    <InArgument x:TypeArguments="x:String">[selector]</InArgument>
  </uix:TargetAnchorable.FullSelectorArgument>
  <uix:TargetAnchorable.FuzzySelectorArgument>
    <InArgument x:TypeArguments="x:String">[fuzzySelector]</InArgument>
  </uix:TargetAnchorable.FuzzySelectorArgument>
  <uix:TargetAnchorable.ImageAccuracyArgument>
    <InArgument x:TypeArguments="x:Double">0.8</InArgument>
  </uix:TargetAnchorable.ImageAccuracyArgument>
  <uix:TargetAnchorable.NativeTextArgument>
    <InArgument x:TypeArguments="x:String">[text]</InArgument>
  </uix:TargetAnchorable.NativeTextArgument>
</uix:TargetAnchorable>
```

## TargetApp

`TargetApp` is used by the **Use Application/Browser** activity to identify and connect to the target application window or browser tab.

**Latest version: V2**

| Property | Display Name | Type | Description |
|----------|-------------|------|-------------|
| `Selector` | Selector | `InArgument<string>` | List of attributes used to find a particular application window. |
| `FilePath` | File path | `InArgument<string>` | The full path to the executable file that starts the application. Used only when opening a new application instance. |
| `Arguments` | Arguments | `InArgument<string>` | Parameters to pass to the target application at startup. Used only when opening a new application or browser instance. |
| `Url` | URL | `InArgument<string>` | The URL of the web page to open. |
| `WorkingDirectory` | Working directory | `InArgument<string>` | Path of the current working directory. |

### XAML Syntax

```xml
<uix:TargetApp Version="V2">
  <uix:TargetApp.Selector>
    <InArgument x:TypeArguments="x:String">[selector]</InArgument>
  </uix:TargetApp.Selector>
  <uix:TargetApp.FilePath>
    <InArgument x:TypeArguments="x:String">[filePath]</InArgument>
  </uix:TargetApp.FilePath>
  <uix:TargetApp.Arguments>
    <InArgument x:TypeArguments="x:String">[arguments]</InArgument>
  </uix:TargetApp.Arguments>
  <uix:TargetApp.Url>
    <InArgument x:TypeArguments="x:String">[url]</InArgument>
  </uix:TargetApp.Url>
  <uix:TargetApp.WorkingDirectory>
    <InArgument x:TypeArguments="x:String">[workingDirectory]</InArgument>
  </uix:TargetApp.WorkingDirectory>
</uix:TargetApp>
```

## PointOffset

`UiPath.UIAutomationNext.PointOffset`

The offset values used to perform the click. The default is the center of the target.

| Property | Display Name | Type | Description |
|----------|-------------|------|-------------|
| `Position` | Anchoring point | `NPosition` | Describes the starting point of the cursor to which offsets from `OffsetX` and `OffsetY` are added. Available options: `TopLeft`, `TopRight`, `BottomLeft`, `BottomRight`, `Center`. Default: `Center`. |
| `X` | Offset X | `InArgument<int>` | Horizontal displacement of the cursor position according to the option selected in the Anchoring point field. |
| `Y` | Offset Y | `InArgument<int>` | Vertical displacement of the cursor position according to the option selected in the Anchoring point field. |

### XAML Syntax

```xml
<uix:PointOffset Position="Center">
  <uix:PointOffset.X>
    <InArgument x:TypeArguments="x:Int32">10</InArgument>
  </uix:PointOffset.X>
  <uix:PointOffset.Y>
    <InArgument x:TypeArguments="x:Int32">5</InArgument>
  </uix:PointOffset.Y>
</uix:PointOffset>
```

## RegionOffset

`UiPath.UIAutomationNext.RegionOffset`

The offset values for the area used to perform the action.

| Property | Display Name | Type | Description |
|----------|-------------|------|-------------|
| `Position` | Anchoring point | `NPosition` | Describes the starting point of the region to which offsets from `OffsetX` and `OffsetY` are added. Available options: `TopLeft`, `TopRight`, `BottomLeft`, `BottomRight`, `Center`. Default: `TopLeft`. |
| `X` | Offset X | `InArgument<int>` | Horizontal displacement of the region according to the option selected in the Anchoring point field. |
| `Y` | Offset Y | `InArgument<int>` | Vertical displacement of the region according to the option selected in the Anchoring point field. |
| `Width` | Width | `InArgument<int>` | Width of the offset region. |
| `Height` | Height | `InArgument<int>` | Height of the offset region. |

### XAML Syntax

```xml
<uix:RegionOffset Position="TopLeft">
  <uix:RegionOffset.X>
    <InArgument x:TypeArguments="x:Int32">0</InArgument>
  </uix:RegionOffset.X>
  <uix:RegionOffset.Y>
    <InArgument x:TypeArguments="x:Int32">0</InArgument>
  </uix:RegionOffset.Y>
  <uix:RegionOffset.Width>
    <InArgument x:TypeArguments="x:Int32">100</InArgument>
  </uix:RegionOffset.Width>
  <uix:RegionOffset.Height>
    <InArgument x:TypeArguments="x:Int32">50</InArgument>
  </uix:RegionOffset.Height>
</uix:RegionOffset>
```

## Configure a TargetAnchorable

To configure a TargetAnchorable for an activity (replace `$VARIABLES` with actual values):

> Read the skill file at `uia-configure-target/SKILL.md` (resolve relative to this file's directory: `../../skills/uia-configure-target/SKILL.md`) and execute it with these arguments: `--window $WINDOW --elements $ELEMENTS --semantic`

To configure multiple elements on the same screen in a single invocation, separate them with `|`. This captures the window once and reuses it for all elements:

> `--window $WINDOW --elements "element one | element two | element three" --semantic`

## Configure a TargetApp

To configure a TargetApp (window only, no elements):

> Read the skill file at `uia-configure-target/SKILL.md` (resolve relative to this file's directory: `../../skills/uia-configure-target/SKILL.md`) and execute it with these arguments: `--window $WINDOW`

## Notes

- **Version attributes**: Always specify the latest version in XAML. `TargetAnchorable` uses `Version="V6"` and `TargetApp` uses `Version="V2"`. Omitting the version or using an older version may result in legacy behavior or missing features.
- **TargetAnchorable** is embedded as a sub-object (named `Target`) in activities that interact with UI elements. It is not set directly as an activity property in the Properties panel; instead, its sub-properties appear under the Target category.
- **TargetApp** is embedded as a sub-object (named `TargetApp`) in the Use Application/Browser activity. It configures the application window identification.
- **Anchors**: `TargetAnchorable` supports up to three anchors for improved element identification accuracy. Anchors are sibling sub-objects alongside the target and are used to disambiguate elements that share similar selectors.
- **Semantic selectors** (in `TargetAnchorable`) enable AI-powered element identification using natural language descriptions, providing resilience against UI layout changes.
- **Project settings**: Properties marked with `isProjectSetting: true` (such as `WaitForReadyArgument`) can have their defaults configured at the project level.
