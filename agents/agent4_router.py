import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
QUEUE_ITEM_PATH = ROOT_DIR / "queues" / "pending_queue_item.json"
REGISTRY_PATH = ROOT_DIR / "registry" / "workflow_registry.json"
APP_PROFILE_DIR = ROOT_DIR / "app_profiles"
OUTPUT_DIR = ROOT_DIR / "outputs"
PROMPTS_DIR = ROOT_DIR / "prompts"
TARGET_ORCHESTRATOR_FOLDER = "Development"
STABLE_PROCESS_NAME = "Prompt2ProvisionUiPath"
STABLE_PACKAGE_KEY = "Prompt2ProvisionUiPath"

ROUTING_DECISION_PATH = OUTPUT_DIR / "routing_decision.json"
BUILDER_PROMPT_PATH = PROMPTS_DIR / "agent2_codex_builder_prompt.txt"


def read_json(path):
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def get_registry_entry(registry, workflow_key):
    if not workflow_key:
        return None

    if isinstance(registry, dict):
        if workflow_key in registry:
            return registry[workflow_key]

        workflows = registry.get("workflows")
        if isinstance(workflows, dict):
            return workflows.get(workflow_key)

        if isinstance(workflows, list):
            for workflow in workflows:
                if workflow.get("workflow_key") == workflow_key:
                    return workflow

    return None


def is_approved_workflow(registry_entry):
    return (
        isinstance(registry_entry, dict)
        and registry_entry.get("status") == "approved"
    )


def build_decision(decision, queue_item, message):
    return {
        "decision": decision,
        "message": message,
        "application_id": queue_item.get("application_id"),
        "application_name": queue_item.get("application_name"),
        "operation": queue_item.get("operation"),
        "workflow_key": queue_item.get("workflow_key"),
    }


def create_builder_prompt(application_id):
    profile_path = f"app_profiles/{application_id}.json"
    ui_map_path = f"app_profiles/{application_id}_ui_map.json"

    queue_item = read_json(QUEUE_ITEM_PATH)
    operation = queue_item.get("operation")
    workflow_key = queue_item.get("workflow_key")
    application_name = queue_item.get("application_name", application_id)

    ui_map = read_json(APP_PROFILE_DIR / f"{application_id}_ui_map.json")
    operation_map = ui_map.get("operations", {}).get(operation, {})

    workflow_name = operation_map.get("workflow_name", f"{operation}.xaml")
    workflow_output_path = f"uipath_project/workflows/apps/{application_id}/{workflow_name}"

    steps = operation_map.get("steps", [])
    success_validation = operation_map.get("success_validation", [])

    steps_text = "\n".join([f"   - {step}" for step in steps])

    if isinstance(success_validation, list):
        success_text = "\n".join([f"   - {item}" for item in success_validation])
    else:
        success_text = f"   - {success_validation}"

    return f"""
Build, deploy, test, and repair the {application_name} {operation.replace("_", "-")} UiPath workflow artifact.

Source files:
- queues/pending_queue_item.json
- {profile_path}
- {ui_map_path}

Workflow key:
{workflow_key}

Application ID:
{application_id}

Operation:
{operation}

Output workflow:
{workflow_output_path}

Requirements:
1. Read the {application_name} UI map and use the {operation} operation only.
2. Build a reusable UiPath XAML workflow using Modern UIAutomation activities.
3. Scope all UI activities inside Use Application/Browser.
4. Open the application from in_BaseUrl; do not hardcode URLs.
5. Resolve runtime field values from explicit arguments when provided, otherwise from in_Fields.
6. Do not hardcode request-specific queue values.
7. Use strict {application_name} selectors from the application source.
8. Workflow steps:
{steps_text}
9. Validate success when the result contains:
{success_text}
10. Add meaningful logs before major UI actions.
11. Keep the workflow reusable for future queue transactions.
12. Update README.md, test_data.json, and workflow_arguments.json to show {operation} is implemented.

Queue data and asset handling:
13. The generated queue transaction JSON should be copied to a local external path outside the UiPath project folder.
14. Add support for reading that external queue JSON path from a UiPath Orchestrator Asset.
15. Use an asset name such as Prompt2Provision_QueueDataPath.
16. Main.xaml should read the asset value, then read the queue JSON from that local path.
17. Do not hardcode the queue file path inside Main.xaml.

Deployment requirements:
18. After generating the workflow, prepare the UiPath project for deployment, project.json location is inside uipath_project/project.json.
19. Before packaging or deploying, query Orchestrator for the current `{STABLE_PACKAGE_KEY}` version by checking the `{TARGET_ORCHESTRATOR_FOLDER}` process version and the tenant feed with `uip or packages list --search {STABLE_PACKAGE_KEY} --all-fields --output json`.
20. Set uipath_project/project.json `projectVersion` and the package version to the next patch version after the highest current Orchestrator version. Do not reuse a local version that already exists in Orchestrator.
21. Package the UiPath project.
22. Upload the package to Orchestrator tenant feed with `uip or packages upload <nupkg> --output json`.
23. Create/update the process only in the `{TARGET_ORCHESTRATOR_FOLDER}` Orchestrator folder. Resolve the folder dynamically by name/path; do not hardcode folder IDs or GUIDs.
24. Use the stable process name `{STABLE_PROCESS_NAME}` and package key `{STABLE_PACKAGE_KEY}` when a new process binding is needed. If `{TARGET_ORCHESTRATOR_FOLDER}` already contains a process, update that process/package binding dynamically. Do not create operation-specific process names such as `{application_name}_{operation}` and do not deploy to any personal workspace folder.
25. Ensure the process can be launched from UiPath Assistant.
26. Document deployment steps in README.md.

Test execution requirements:
27. After deployment, run the deployed process from the `{TARGET_ORCHESTRATOR_FOLDER}` Orchestrator folder or UiPath Assistant where possible.
28. Capture execution result, logs, and any failure details.
29. Save test execution output under outputs/execution_test_result.json.

Autonomous repair loop:
30. If execution fails due to selector, UI element, timeout, or synchronization issues:
   - identify failed step
   - inspect workflow and selector
   - update selector or synchronization logic
   - add Check App State / Wait for Element Appear where needed
   - check the current Orchestrator version again, then rebuild / repackage with the next patch version
   - redeploy
   - rerun the test
31. Repeat repair loop until success or until max repair attempts is reached.
32. Save repair history under outputs/repair_history.json.

Important:
- Do not create placeholder-only workflows.
- Do not Hardcode queue item specific values inside workflow for validations
- Do not only explain.
- Actually create or update the files.
- If selector refinement is needed, add TODO comments, but still create real UiPath UIAutomation activity structure.
- Generated workflows must be reusable, deployable, and testable.
""".strip()


def route(queue_item, registry):
    if queue_item.get("status") != "READY_FOR_ROUTING":
        return build_decision(
            "STOP_INVALID_REQUEST",
            queue_item,
            "Queue item is not ready for routing",
        )

    application_id = queue_item.get("application_id")
    workflow_key = queue_item.get("workflow_key")
    app_profile_path = APP_PROFILE_DIR / f"{application_id}.json"
    ui_map_path = APP_PROFILE_DIR / f"{application_id}_ui_map.json"

    if not app_profile_path.exists():
        return build_decision(
            "APP_ONBOARDING_REQUIRED",
            queue_item,
            "Application profile missing",
        )

    if not ui_map_path.exists():
        return build_decision(
            "UI_MAP_REQUIRED",
            queue_item,
            "Application UI map missing",
        )

    registry_entry = get_registry_entry(registry, workflow_key)
    if is_approved_workflow(registry_entry):
        return build_decision(
            "EXECUTE_WORKFLOW",
            queue_item,
            "Approved reusable workflow found",
        )

    return build_decision(
        "BUILD_WORKFLOW",
        queue_item,
        "Approved reusable workflow not found",
    )


def main():
    queue_item = read_json(QUEUE_ITEM_PATH)
    registry = read_json(REGISTRY_PATH)
    routing_decision = route(queue_item, registry)

    write_json(ROUTING_DECISION_PATH, routing_decision)

    if routing_decision["decision"] == "BUILD_WORKFLOW":
        builder_prompt = create_builder_prompt(queue_item["application_id"])
        write_text(BUILDER_PROMPT_PATH, builder_prompt)


if __name__ == "__main__":
    main()
