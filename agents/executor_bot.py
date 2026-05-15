import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
QUEUE_ITEM_PATH = ROOT_DIR / "queues" / "pending_queue_item.json"
REGISTRY_PATH = ROOT_DIR / "registry" / "workflow_registry.json"
OUTPUT_DIR = ROOT_DIR / "outputs"

EXECUTION_RESULT_PATH = OUTPUT_DIR / "execution_result.json"


def read_json(path):
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def get_registry_entry(registry, workflow_key):
    if not workflow_key:
        return None

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


def build_failure_result(workflow_key, message):
    return {
        "workflow_key": workflow_key,
        "execution_status": "FAILED",
        "message": message,
        "execution_mode": "ORCHESTRATOR_READY",
        "next_action": "START_ORCHESTRATOR_JOB",
    }


def build_success_result(workflow_key):
    return {
        "workflow_key": workflow_key,
        "execution_status": "SUCCESS",
        "message": "Reusable workflow executed with dynamic queue data",
        "execution_mode": "ORCHESTRATOR_READY",
        "next_action": "START_ORCHESTRATOR_JOB",
    }


def print_execution_context(queue_item, workflow_entry):
    print(f"workflow path: {workflow_entry.get('workflow_path')}")
    print(f"application name: {queue_item.get('application_name')}")
    print(f"operation: {queue_item.get('operation')}")
    print(f"base_url: {queue_item.get('base_url')}")
    print("fields dictionary:")
    print(json.dumps(queue_item.get("fields", {}), indent=2))
    print("entitlement_details:")
    print(json.dumps(queue_item.get("entitlement_details", {}), indent=2))
    print("execution_mode: ORCHESTRATOR_READY")
    print("next_action: START_ORCHESTRATOR_JOB")


def main():
    queue_item = read_json(QUEUE_ITEM_PATH)
    registry = read_json(REGISTRY_PATH)
    workflow_key = queue_item.get("workflow_key")
    workflow_entry = get_registry_entry(registry, workflow_key)

    if workflow_entry is None:
        result = build_failure_result(
            workflow_key,
            "Workflow key does not exist in registry",
        )
        write_json(EXECUTION_RESULT_PATH, result)
        return

    if workflow_entry.get("status") != "approved":
        result = build_failure_result(
            workflow_key,
            "Workflow is not approved",
        )
        write_json(EXECUTION_RESULT_PATH, result)
        return

    print_execution_context(queue_item, workflow_entry)
    write_json(EXECUTION_RESULT_PATH, build_success_result(workflow_key))


if __name__ == "__main__":
    main()
