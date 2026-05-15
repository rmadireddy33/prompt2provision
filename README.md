# Prompt2Provision UiPath Execution Layer

`uipath_project/Main.xaml` is the generic queue router. It reads the `Prompt2Provision_QueueDataPath` Orchestrator Text asset, reads the queue transaction JSON from that external local path, deserializes it into a `JObject`, and extracts `application_id`, `operation`, `base_url`, `fields`, and optional `entitlement_details`.

The generated transaction JSON for this run was copied outside the UiPath project folder to:

`C:\Users\ravin\OneDrive\Documents\UiPathCodedAgentChallenge\Prompt2Provision\external_queue_data\pending_queue_item.json`

Workflow selection is dynamic:

- `create_user` -> `CreateUser.xaml`
- `modify_user` -> `ModifyUser.xaml`
- `delete_user` -> `DeleteUser.xaml`

For `broadriver.create_user`, `Main.xaml` resolves `workflows/apps/broadriver/CreateUser.xaml` and passes `in_BaseUrl`, `in_Fields`, and `in_EntitlementDetails`. The child workflow can also accept explicit field arguments such as `in_UserName`, `in_EmployeeId`, `in_Email`, `in_Department`, `in_Region`, `in_UserType`, `in_Group`, `in_Duration`, and `in_ManagerEmail`; when supplied directly, those values take precedence over `in_Fields`.

## BroadRiver Create User

`uipath_project/workflows/apps/broadriver/CreateUser.xaml` implements the BroadRiver create-user operation with Modern UIAutomation:

- Opens BroadRiver using `in_BaseUrl`
- Clicks Admin
- Clicks Create Users
- Enters user name
- Enters email address
- Selects the group from the suggestion dropdown
- Enters manager email
- Clicks Submit
- Reads `toast-message`
- Validates the success text contains `User created successfully`

The workflow uses strict BroadRiver selectors from the app operation surface: `nav-admin`, `admin-create-user`, `input-name`, `input-employee-id`, `input-email`, `input-department`, `input-region`, `input-user-type`, `input-group`, `input-duration`, `input-manager-approval`, `input-manager-email`, `btn-create-user`, and `toast-message`. Request-specific queue values are not hardcoded in XAML.

## BroadRiver Delete User

`uipath_project/workflows/apps/broadriver/DeleteUser.xaml` implements the BroadRiver delete-user operation with Modern UIAutomation:

- Opens BroadRiver using `in_BaseUrl`
- Clicks Admin
- Clicks Delete User
- Searches by email
- Clicks Delete
- Confirms delete using the current BroadRiver delete action
- Reads `toast-message`
- Validates the success text contains `User deleted successfully`

The workflow uses strict BroadRiver selectors from the app operation surface: `nav-admin`, `admin-delete-user`, `input-email`, `btn-delete-user`, and `toast-message`. Request-specific queue values are not hardcoded in XAML.

## Deployment

Validation and packaging completed for create-user:

- `uip rpa get-errors` passed for `CreateUser.xaml`
- `uip rpa get-errors` passed for `Main.xaml`
- `uip rpa build` succeeded
- Package created: `outputs/packages/Prompt2ProvisionUiPath.1.0.15.nupkg`
- Package `Prompt2ProvisionUiPath` version `1.0.15` is present in the Orchestrator tenant feed
- The stable process `Prompt2ProvisionUiPath` was updated only in the `Development` Orchestrator folder. The folder was resolved dynamically by path/name and no folder IDs or GUIDs are hardcoded in the project.

Required Orchestrator setup:

1. Create or update a Text asset named `Prompt2Provision_QueueDataPath`.
2. Set its value to the external queue JSON path above, or another local path available on the robot machine.
3. Ensure the target folder has a configured runtime template.
4. Launch the process from UiPath Assistant or Orchestrator.

Notes from this environment:

- The resource/asset CLI extension was unavailable and could not be installed because `@uipath/resource-tool` fetch failed.
- Direct REST calls from the shell could not connect to Orchestrator, but the existing asset was verified through robot logs.
- The deployed `Development` run used the asset value `C:\Prompt2ProvisionData\pending_queue_item.json`.
- The first run attempt with `--runtime-type Development` failed because no Development runtimes are configured on folder templates; rerunning with the folder default launched as Unattended on `LAPTOP-PPQDF7UL`.
- Deployed execution reached the BroadRiver create-user UI, filled the form, clicked Submit, and read `toast-message`.
- The app returned `A user with this email already exists` for the asset-backed queue email. Selector/synchronization repair stopped because the remaining failure is business data, not UI automation. The repo external queue copy has a unique test email, but this sandbox could not write to `C:\Prompt2ProvisionData\pending_queue_item.json`.

Execution details are saved in `outputs/execution_test_result.json`; repair history is saved in `outputs/repair_history.json`.

## Repair Notes - 2026-05-12

- Repaired `broadriver.create_user` after Orchestrator job `c77652c7-738f-4657-af8b-75db82932b21` faulted at `NClick "Click Admin"` on the deployed stale selector `<webctrl id='nav-adn' tag='BUTTON' />`.
- Reconfirmed `app_profiles/broadriver.json` and `app_profiles/broadriver_ui_map.json`; they define operation fields and step labels only, with no stale `nav-adn` selector to update.
- Kept `CreateUser.xaml` on the current Admin selector `<webctrl id='nav-admin' tag='BUTTON' />`, with `NCheckState` waiting for the Admin button before click and for `admin-create-user` after navigation.
- Removed the fixed `DelayBefore` from `NClick "Click Admin"` so synchronization is handled by Modern UIAutomation waits and target timeouts instead of a static sleep.
- Repaired `broadriver.create_user` after Orchestrator job `0fe05730-4657-4531-9938-4eeadf0efcb4` faulted at `NClick "Click Admin"` due to the stale strict selector `<webctrl id='nav-adn' tag='BUTTON' />` in the deployed package.
- Confirmed the active workflow file targets the current BroadRiver Admin selector `<webctrl id='nav-admin' tag='BUTTON' />`; no runtime request values were hardcoded.
- Added Modern UIAutomation `Check App State` waits before clicking Admin and before clicking Create Users, both waiting for visible target elements with `WaitForReady=Interactive`.
- Widened the BroadRiver browser scope selector from the exact title `BroadRiver Admin Portal` to `BroadRiver*` throughout `CreateUser.xaml` so navigation does not break child target resolution when the page title varies.
- Repaired `broadriver.create_user` after Orchestrator job `ffe4f947-df87-493e-a8ca-9fc5135857b6` faulted at `NClick "Click Admin"` due to strict selector `<webctrl id='nav-adn' tag='BUTTON' />`.
- Updated `uipath_project/workflows/apps/broadriver/CreateUser.xaml` to target the current BroadRiver Admin button selector `<webctrl id='nav-admin' tag='BUTTON' />`, matching the nearest runtime selector and the BroadRiver workflow documentation.
- Aligned the Employee ID field selector with the app operation metadata by using `<webctrl id='input-employee-id' tag='INPUT' />`.
- Kept runtime request values dynamic through workflow arguments and `in_Fields` / `in_EntitlementDetails`; no queue-specific user data was hardcoded.
- The workflow remains on Modern UIAutomation (`NApplicationCard`, `NClick`, `NTypeInto`, `NSelectItem`, `NGetText`) with UIA target timeouts and `WaitForReady=Interactive` used for synchronization.
