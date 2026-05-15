# BroadRiver Workflows

Reusable UiPath workflow artifacts for the BroadRiver application.

## broadriver.create_user

`CreateUser.xaml` implements the BroadRiver create-user operation with Modern UIAutomation activities.

UI-map source:

- Workflow name: `CreateUser.xaml`
- Artifact status: implemented at `workflows/apps/broadriver/CreateUser.xaml`
- Navigation: open BroadRiver with `in_BaseUrl`, click Admin, click Create Users, enter user name, enter email address, select the requested group suggestion, enter manager email, submit, and verify the success message.
- Inputs: `in_BaseUrl`, `in_Fields`, `in_EntitlementDetails`, `in_UserName`, `in_EmployeeId`, `in_Email`, `in_Department`, `in_Region`, `in_UserType`, `in_Group`, `in_Duration`, `in_ManagerEmail`
- Success validation: `User created successfully`

Runtime arguments:

- `in_BaseUrl`: application URL from the queue item or config. Do not hardcode URLs in activities.
- `in_Fields`: queue item fields as `Newtonsoft.Json.Linq.JObject`.
- `in_EntitlementDetails`: entitlement metadata; `ui_value_to_select` is used for the group suggestion text when present.
- `in_UserName`: optional direct user name argument. When provided, it takes precedence over `in_Fields("user_name")`.
- `in_Email`: optional direct email argument. When provided, it takes precedence over `in_Fields("email")`.
- `in_EmployeeId`: optional direct employee ID argument. When provided, it takes precedence over `in_Fields("employee_id")`.
- `in_Department`: optional direct department argument. When provided, it takes precedence over `in_Fields("department")`.
- `in_Region`: optional direct region argument. When provided, it takes precedence over `in_Fields("region")`.
- `in_UserType`: optional direct user type argument. When provided, it takes precedence over `in_Fields("user_type")`.
- `in_Group`: optional direct requested group argument. When provided, it takes precedence over `in_Fields("requested_group")`.
- `in_Duration`: optional direct duration argument. When provided, it takes precedence over `in_Fields("duration")`.
- `in_ManagerEmail`: optional direct manager email argument. When provided, it takes precedence over `in_Fields("manager_email")`.

The workflow validates reusable inputs, scopes all UI activities inside `Use Application/Browser`, uses strict BroadRiver element IDs (`nav-admin`, `admin-create-user`, `input-name`, `input-employee-id`, `input-email`, `input-department`, `input-region`, `input-user-type`, `input-group`, `input-duration`, `input-manager-approval`, `input-manager-email`, `btn-create-user`, `toast-message`), and validates the success toast.

## broadriver.delete_user

`DeleteUser.xaml` implements the BroadRiver delete-user operation with Modern UIAutomation activities.

UI-map source:

- Workflow name: `DeleteUser.xaml`
- Artifact status: implemented at `workflows/apps/broadriver/DeleteUser.xaml`
- Navigation: open BroadRiver with `in_BaseUrl`, click Admin, click Delete User, enter the user email, click Search, click Delete, confirm delete, and verify the success message.
- Inputs: `in_BaseUrl`, `in_Fields`, `in_EntitlementDetails`, `in_Email`
- Success validation: `User deleted successfully`

Runtime arguments:

- `in_BaseUrl`: application URL from the queue item or config. Do not hardcode URLs in activities.
- `in_Fields`: queue item fields as `Newtonsoft.Json.Linq.JObject`.
- `in_EntitlementDetails`: accepted for router compatibility.
- `in_Email`: optional direct email argument. When provided, it takes precedence over `in_Fields("email")`.

The workflow validates reusable inputs, scopes all UI activities inside `Use Application/Browser`, uses strict BroadRiver element IDs (`nav-admin`, `nav-delete-user`, `input-email`, `btn-search-user`, `btn-delete-user`, `btn-confirm-delete`, `toast-message`), waits for key elements before acting, and validates that the rendered result contains `User deleted successfully`.

## Queue Data Asset

`Main.xaml` reads the queue JSON path from the Orchestrator Text asset `Prompt2Provision_QueueDataPath`, then reads the queue transaction JSON from that local path. The queue file path is not hardcoded in `Main.xaml`.

For this run, the generated transaction JSON was copied outside the UiPath project folder to:

`C:\Users\ravin\OneDrive\Documents\UiPathCodedAgentChallenge\Prompt2Provision\external_queue_data\pending_queue_item.json`

Create or update `Prompt2Provision_QueueDataPath` in the target Orchestrator folder and set it to a robot-local path for the copied queue JSON.

## Deployment Steps

1. Validate the workflow with `uip rpa get-errors --file-path "<project>\workflows\apps\broadriver\DeleteUser.xaml" --project-dir "<project>" --output json`.
2. Build the project with `uip rpa build "<project>" --output json`.
3. Package the project with `uip rpa pack "<project>" "<repo>\outputs\packages" --package-id Prompt2ProvisionUiPath --package-version <version> --output json`.
4. Upload the generated `.nupkg` with `uip or packages upload <nupkg> --output json`.
5. Create or update the `Prompt2ProvisionUiPath` process binding in the `Development` folder resolved by folder path/name.
6. Ensure the Text asset `Prompt2Provision_QueueDataPath` exists in the same folder.
7. Launch the process from UiPath Assistant or Orchestrator.

## Deployment and Test Status

- `CreateUser.xaml` exists at `uipath_project/workflows/apps/broadriver/CreateUser.xaml`.
- `Main.xaml` reads queue data from the `Prompt2Provision_QueueDataPath` Orchestrator asset.
- External queue data copy for this run: `external_queue_data/pending_queue_item.json`.
- Validation passed for `CreateUser.xaml`.
- Project build passed with `uip rpa build`.
- Current package version: `1.0.15`.
- The `Development` process `Prompt2ProvisionUiPath` was updated to package version `1.0.15`.
- Deployed repair testing reached form submit and read the toast. The asset-backed queue email already existed in BroadRiver, so the final observed failure was business validation data, not a selector or synchronization issue.
