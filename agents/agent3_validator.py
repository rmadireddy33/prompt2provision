import json
import os
import shutil
import subprocess
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


def resolve_command(command):
    name = command[0]

    if os.name == "nt" and name == "uip":
        npm_uip_cmd = Path.home() / "AppData" / "Roaming" / "npm" / "uip.cmd"
        if npm_uip_cmd.exists():
            return [str(npm_uip_cmd), *command[1:]]

    resolved = shutil.which(name)
    if resolved:
        return [resolved, *command[1:]]

    return command


def run_command(command):
    try:
        result = subprocess.run(
            resolve_command(command),
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        return {
            "returncode": 127,
            "stdout": "",
            "stderr": f"Executable not found: {command[0]} ({exc})",
        }

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def command_summary(result):
    text = "\n".join(
        part.strip()
        for part in [result.get("stderr", ""), result.get("stdout", "")]
        if part and part.strip()
    )
    return text[:4000]


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


def validate_profiles_do_not_store_selectors(ui_map, ui_map_path, issues):
    for operation, metadata in ui_map.get("operations", {}).items():
        if isinstance(metadata, dict) and "selectors" in metadata:
            add_issue(
                issues,
                "PROFILE_SELECTOR_STORAGE",
                "UI map must not store selectors; selectors must be captured from the live UI/browser during workflow generation",
                path=ui_map_path,
                value=operation,
            )


def validate_modern_uia_structure(workflow_path, issues):
    if not workflow_path.exists():
        return

    content = workflow_path.read_text(encoding="utf-8")
    required_fragments = [
        "uix:NApplicationCard",
        "uix:TargetApp",
        "uix:TargetAnchorable",
    ]
    missing_fragments = [
        fragment for fragment in required_fragments if fragment not in content
    ]
    if missing_fragments:
        add_issue(
            issues,
            "MISSING_MODERN_UIA_TARGETS",
            "Generated workflow does not contain captured Modern UIAutomation targets",
            path=workflow_path,
            value=", ".join(missing_fragments),
        )


def validate_uipath_workflow(workflow_path, issues):
    if not workflow_path.exists():
        return {
            "get_errors": None,
            "build": None,
        }

    get_errors = run_command([
        "uip",
        "rpa",
        "get-errors",
        "--file-path",
        str(workflow_path),
        "--project-dir",
        str(UIPATH_PROJECT_DIR),
        "--output",
        "json",
    ])
    if get_errors["returncode"] != 0:
        add_issue(
            issues,
            "UIPATH_GET_ERRORS_FAILED",
            "UiPath get-errors reported diagnostics for the generated workflow",
            path=workflow_path,
            value=command_summary(get_errors),
        )

    build = run_command([
        "uip",
        "rpa",
        "build",
        str(UIPATH_PROJECT_DIR),
        "--output",
        "json",
    ])
    if build["returncode"] != 0:
        add_issue(
            issues,
            "UIPATH_BUILD_FAILED",
            "UiPath project build failed after workflow generation",
            path=UIPATH_PROJECT_DIR,
            value=command_summary(build),
        )

    return {
        "get_errors": get_errors,
        "build": build,
    }


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
        return workflow_key, issues, {"get_errors": None, "build": None}

    ui_map = read_json(ui_map_path)
    validate_profiles_do_not_store_selectors(ui_map, ui_map_path, issues)
    workflow_name = get_workflow_name(ui_map, operation)
    expected_workflow_path = None
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
        return workflow_key, issues, {"get_errors": None, "build": None}

    if workflow_name:
        expected_workflow_path = workflow_folder / workflow_name
        if not expected_workflow_path.exists():
            add_issue(
                issues,
                "MISSING_WORKFLOW_FILE",
                "Expected workflow file is missing",
                path=expected_workflow_path,
            )
        else:
            validate_modern_uia_structure(expected_workflow_path, issues)

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
    uipath_validation = validate_uipath_workflow(expected_workflow_path, issues)

    return workflow_key, issues, uipath_validation


def main():
    queue_item = read_json(QUEUE_ITEM_PATH)
    workflow_key, issues, uipath_validation = validate_artifacts(queue_item)
    validation_result = {
        "workflow_key": workflow_key,
        "validation_status": "FAILED" if issues else "PASSED",
        "issues": issues,
        "uipath_validation": uipath_validation,
    }

    write_json(VALIDATION_RESULT_PATH, validation_result)


if __name__ == "__main__":
    main()
