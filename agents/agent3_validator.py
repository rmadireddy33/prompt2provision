import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
QUEUE_ITEM_PATH = ROOT_DIR / "queues" / "pending_queue_item.json"
APP_PROFILE_DIR = ROOT_DIR / "app_profiles"
UIPATH_PROJECT_DIR = ROOT_DIR / "uipath_project"
WORKFLOWS_DIR = UIPATH_PROJECT_DIR / "workflows" / "apps"
OUTPUT_DIR = ROOT_DIR / "outputs"

VALIDATION_RESULT_PATH = OUTPUT_DIR / "validation_result.json"
REQUIRED_ARTIFACTS = [
    "README.md",
    "test_data.json",
    "workflow_arguments.json",
]
SKIP_HARDCODE_SCAN = {
    "test_data.json",
}


def read_json(path):
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def add_issue(issues, code, message, path=None, value=None):
    issue = {
        "code": code,
        "message": message,
    }
    if path is not None:
        issue["path"] = str(path.relative_to(ROOT_DIR))
    if value is not None:
        issue["value"] = value
    issues.append(issue)


def get_runtime_values(queue_item):
    values = []
    for value in queue_item.get("fields", {}).values():
        if value is None:
            continue

        text_value = str(value).strip()
        if text_value:
            values.append(text_value)

    return sorted(set(values), key=len, reverse=True)


def get_workflow_name(ui_map, operation):
    operation_metadata = ui_map.get("operations", {}).get(operation, {})
    return operation_metadata.get("workflow_name")


def scan_for_hardcoded_values(workflow_folder, runtime_values, issues):
    if not workflow_folder.exists():
        return

    for file_path in workflow_folder.rglob("*"):
        if not file_path.is_file() or file_path.name in SKIP_HARDCODE_SCAN:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for runtime_value in runtime_values:
            if runtime_value in content:
                add_issue(
                    issues,
                    "HARDCODED_RUNTIME_VALUE",
                    "Generated workflow artifact contains a runtime queue value",
                    path=file_path,
                    value=runtime_value,
                )


def validate_artifacts(queue_item):
    issues = []
    application_id = queue_item.get("application_id")
    operation = queue_item.get("operation")
    workflow_key = queue_item.get("workflow_key")

    ui_map_path = APP_PROFILE_DIR / f"{application_id}_ui_map.json"
    if not ui_map_path.exists():
        add_issue(
            issues,
            "MISSING_UI_MAP",
            "Application UI map is missing",
            path=ui_map_path,
        )
        return workflow_key, issues

    ui_map = read_json(ui_map_path)
    workflow_name = get_workflow_name(ui_map, operation)
    if not workflow_name:
        add_issue(
            issues,
            "MISSING_WORKFLOW_NAME",
            "UI map does not define a workflow_name for the operation",
            path=ui_map_path,
        )

    workflow_folder = WORKFLOWS_DIR / application_id
    if not workflow_folder.exists():
        add_issue(
            issues,
            "MISSING_WORKFLOW_FOLDER",
            "Generated workflow folder is missing",
            path=workflow_folder,
        )
        return workflow_key, issues

    if workflow_name:
        expected_workflow_path = workflow_folder / workflow_name
        if not expected_workflow_path.exists():
            add_issue(
                issues,
                "MISSING_WORKFLOW_FILE",
                "Expected workflow file is missing",
                path=expected_workflow_path,
            )

    for artifact_name in REQUIRED_ARTIFACTS:
        artifact_path = workflow_folder / artifact_name
        if not artifact_path.exists():
            add_issue(
                issues,
                "MISSING_ARTIFACT",
                "Required generated artifact is missing",
                path=artifact_path,
            )

    runtime_values = get_runtime_values(queue_item)
    scan_for_hardcoded_values(workflow_folder, runtime_values, issues)

    return workflow_key, issues


def main():
    queue_item = read_json(QUEUE_ITEM_PATH)
    workflow_key, issues = validate_artifacts(queue_item)
    validation_result = {
        "workflow_key": workflow_key,
        "validation_status": "FAILED" if issues else "PASSED",
        "issues": issues,
    }

    write_json(VALIDATION_RESULT_PATH, validation_result)


if __name__ == "__main__":
    main()
