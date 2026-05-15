import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
VALIDATION_RESULT_PATH = ROOT_DIR / "outputs" / "validation_result.json"
APPROVAL_STATUS_PATH = ROOT_DIR / "approvals" / "approval_status.json"
REGISTRY_PATH = ROOT_DIR / "registry" / "workflow_registry.json"
QUEUE_ITEM_PATH = ROOT_DIR / "queues" / "pending_queue_item.json"
APP_PROFILE_DIR = ROOT_DIR / "app_profiles"


def read_json(path):
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def get_workflow_name(application_id, operation):
    ui_map_path = APP_PROFILE_DIR / f"{application_id}_ui_map.json"
    ui_map = read_json(ui_map_path)
    operation_metadata = ui_map.get("operations", {}).get(operation, {})
    return operation_metadata.get("workflow_name")


def should_update_registry(validation_result, approval_status, queue_item):
    return (
        validation_result.get("validation_status") == "PASSED"
        and approval_status.get("approved") is True
        and approval_status.get("workflow_key") == queue_item.get("workflow_key")
        and validation_result.get("workflow_key") == queue_item.get("workflow_key")
    )


def update_registry(registry, queue_item):
    application_id = queue_item["application_id"]
    operation = queue_item["operation"]
    workflow_key = queue_item["workflow_key"]
    workflow_name = get_workflow_name(application_id, operation)
    workflow_path = f"uipath_project/workflows/apps/{application_id}/{workflow_name}"

    registry[workflow_key] = {
        "status": "approved",
        "version": "1.0.0",
        "application_id": application_id,
        "operation": operation,
        "workflow_path": workflow_path,
    }

    return registry


def main():
    validation_result = read_json(VALIDATION_RESULT_PATH)
    approval_status = read_json(APPROVAL_STATUS_PATH)
    registry = read_json(REGISTRY_PATH)
    queue_item = read_json(QUEUE_ITEM_PATH)

    if not should_update_registry(validation_result, approval_status, queue_item):
        return

    updated_registry = update_registry(registry, queue_item)
    write_json(REGISTRY_PATH, updated_registry)


if __name__ == "__main__":
    main()
