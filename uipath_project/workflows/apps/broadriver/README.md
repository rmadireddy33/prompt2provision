# BroadRiver Workflows

## broadriver.delete_user

`DeleteUser.xaml` implements the BroadRiver delete-user operation with Modern UIAutomation activities.

UI-map source:

- Workflow name: `DeleteUser.xaml`
- Artifact status: implemented at `workflows/apps/broadriver/DeleteUser.xaml`
- Navigation: open BroadRiver with `in_BaseUrl`, click Admin, click Delete User, enter the user email, click Search, click Delete, confirm delete, and verify the result.
- Inputs: `in_BaseUrl`, `in_Fields`, `in_EntitlementDetails`, `in_Email`
- Success validation: `User deleted successfully`

Runtime arguments:

- `in_BaseUrl`: application URL from the queue item or config. The workflow explicitly navigates to this argument.
- `in_Fields`: queue item fields as `Newtonsoft.Json.Linq.JObject`.
- `in_EntitlementDetails`: accepted for router compatibility.
- `in_Email`: optional direct email argument. When provided, it takes precedence over `in_Fields("email")`.

Captured UIAutomation target evidence is stored in `DeleteUser.xaml` and the Object Repository:

- Application card: `hE-3mc5q3kSnc1nDJYPVPQ/3taf9CyHLkOidvDLIasL3g`
- Admin button: `hE-3mc5q3kSnc1nDJYPVPQ/9h9RMgzkAEG-9MlH2FFOGg`
- Delete User button: `hE-3mc5q3kSnc1nDJYPVPQ/IaNikuxDFEm36a8PtPVsTQ`
- Delete email input: `hE-3mc5q3kSnc1nDJYPVPQ/0HWDDK2UJEmKf9gfS14PEQ`
- Search button: `hE-3mc5q3kSnc1nDJYPVPQ/O2qIVLuTu0Ko_Mmc8ePbNw`
- Mark User Deleted button: `hE-3mc5q3kSnc1nDJYPVPQ/ufDXXqxxtUmiKrbBvbSiXA`
- Delete status cell: `hE-3mc5q3kSnc1nDJYPVPQ/ijeQa7KhPk-QEJNfPElfAA`

Captured selector IDs include `nav-admin`, `nav-delete-user`, `input-delete-email-search`, `btn-search-delete-user`, and `btn-delete-user`. Browser confirm dialogs are accepted through the `Use Application/Browser` dialog handling configuration.

Repair note 2026-05-20: Orchestrator job `9862f92a-8775-4070-afef-ce46b66c7db1` faulted at `NClick "Click Admin"` because the Admin button target referenced stale selector `<webctrl id='nav-test' tag='BUTTON' />`. Live UIA capture from the restored Edge tab confirmed the Admin button as `id=nav-admin`, `tag=BUTTON`, `title=BroadRiver Admin Portal`, `url=http://localhost:4000/`, rectangle `{X=20,Y=316,Width=232,Height=42}`. The `DeleteUser.xaml` target and matching OR content for reference `hE-3mc5q3kSnc1nDJYPVPQ/9h9RMgzkAEG-9MlH2FFOGg` now both use `<webctrl id='nav-admin' tag='BUTTON' />`.

## Queue Data Asset

`Main.xaml` reads the queue JSON path from the Orchestrator Text asset `Prompt2Provision_QueueDataPath`, then reads the queue transaction JSON from that local path. The queue file path is not hardcoded in `Main.xaml`.

For this run, the generated transaction JSON was copied outside the UiPath project folder to:

`C:\Users\ravin\OneDrive\Documents\UiPathCodedAgentChallenge\Prompt2Provision\external_queue_data\pending_queue_item.json`

The deployed Development job used the existing asset value `C:\Prompt2ProvisionData\pending_queue_item.json`.

## Deployment

Validation and deployment for this delete-user implementation completed with package version `1.0.39`:

1. `uip rpa get-errors` returned no diagnostics for `DeleteUser.xaml`.
2. `uip rpa build` succeeded.
3. The `Development` process and tenant feed were queried before packaging; highest current version was `1.0.38`.
4. `project.json` `projectVersion` was set to `1.0.39`.
5. Package created: `outputs/packages/Prompt2ProvisionUiPath.1.0.39.nupkg`.
6. Package uploaded to the Orchestrator tenant feed.
7. `Prompt2ProvisionUiPath` in `Development` was updated to package version `1.0.39`.
8. The deployed job `9cfe2e05-2c75-440c-843f-c14791ea959b` ran successfully from `Development`; results are saved in `outputs/execution_test_result.json`.
