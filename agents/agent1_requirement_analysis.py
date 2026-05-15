import json
import re
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
REQUEST_PATH = ROOT_DIR / "data" / "jml_request.txt"
APP_PROFILE_DIR = ROOT_DIR / "app_profiles"
OUTPUT_DIR = ROOT_DIR / "outputs"
QUEUE_DIR = ROOT_DIR / "queues"

ONBOARDING_REQUIRED_PATH = OUTPUT_DIR / "onboarding_required.json"
AUTOMATION_CONTRACT_PATH = OUTPUT_DIR / "automation_contract.json"
PENDING_QUEUE_ITEM_PATH = QUEUE_DIR / "pending_queue_item.json"

# External queue data location for UiPath Assistant / Studio execution.
# UiPath Main.xaml can read this path from Orchestrator Asset:
# Asset Name: Prompt2Provision_QueueDataPath
EXTERNAL_QUEUE_DIR = Path(r"C:\Prompt2ProvisionData")
EXTERNAL_QUEUE_FILE = EXTERNAL_QUEUE_DIR / "pending_queue_item.json"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_all_application_profiles():
    """
    Dynamically load application profiles instead of hardcoding application maps.

    Each app profile should contain:
    - application_id
    - application_name
    - optional aliases
    """
    applications = []

    if not APP_PROFILE_DIR.exists():
        return applications

    for profile_path in APP_PROFILE_DIR.glob("*.json"):
        # Skip UI map files like broadriver_ui_map.json
        if profile_path.name.endswith("_ui_map.json"):
            continue

        try:
            with profile_path.open(encoding="utf-8") as profile_file:
                profile = json.load(profile_file)
        except Exception:
            continue

        application_id = profile.get("application_id")
        application_name = profile.get("application_name")

        if not application_id or not application_name:
            continue

        aliases = profile.get("aliases", [])
        if not isinstance(aliases, list):
            aliases = []

        applications.append(
            {
                "application_id": application_id,
                "application_name": application_name,
                "aliases": aliases,
                "profile_path": profile_path,
            }
        )

    return applications


def detect_application(text):
    """
    Detect application from request text using app profile metadata.

    This avoids hardcoding:
    SUPPORTED_APPLICATIONS = {"broadriver": ...}

    Add aliases in app profile if needed:
    "aliases": ["broad river", "br app", "broadridge demo"]
    """
    lower_text = text.lower()
    applications = load_all_application_profiles()

    for app in applications:
        possible_names = [
            app["application_id"],
            app["application_name"],
            *app.get("aliases", []),
        ]

        for name in possible_names:
            if name and name.lower() in lower_text:
                return app

    return None


def profile_path_for(application_id):
    return APP_PROFILE_DIR / f"{application_id}.json"


def load_profile(profile_path):
    with profile_path.open(encoding="utf-8") as profile_file:
        return json.load(profile_file)


def detect_operation(text, app_profile):
    lower_text = text.lower()

    for operation, operation_metadata in app_profile.get("operations", {}).items():
        for phrase in operation_metadata.get("phrases", []):
            if phrase.lower() in lower_text:
                return operation

    return None


def extract_field(text, display_name):
    pattern = rf"^\s*{re.escape(display_name)}\s*:\s*(.+?)\s*$"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)

    if not match:
        return None

    value = match.group(1).strip()
    return value or None


def extract_required_fields(text, required_fields):
    fields = {}
    missing_information = []

    for field_metadata in required_fields:
        field_name = field_metadata["field_name"]
        display_name = field_metadata["display_name"]

        value = extract_field(text, display_name)
        fields[field_name] = value

        if not value:
            missing_information.append(
                {
                    "field_name": field_name,
                    "message": "Required field missing",
                }
            )

    return fields, missing_information


def find_entitlement(app_profile, entitlement_name):
    if not entitlement_name:
        return None

    for entitlement in app_profile.get("entitlements", []):
        if entitlement.get("name", "").lower() == entitlement_name.lower():
            return entitlement

    return None


def validate_entitlements(app_profile, required_fields, fields):
    missing_information = []
    entitlement_details = None

    for field_metadata in required_fields:
        if field_metadata.get("type") != "entitlement":
            continue

        field_name = field_metadata["field_name"]
        requested_entitlement = fields.get(field_name)

        if not requested_entitlement:
            continue

        entitlement = find_entitlement(app_profile, requested_entitlement)

        if entitlement is None:
            missing_information.append(
                {
                    "field_name": field_name,
                    "message": "Entitlement not found in application profile",
                    "value": requested_entitlement,
                }
            )
            continue

        entitlement_details = {
            "requested_entitlement": entitlement.get("name"),
            "ui_value_to_select": entitlement.get("ui_value"),
            "risk_level": entitlement.get("risk_level"),
            "requires_manager_approval": entitlement.get(
                "requires_manager_approval", False
            ),
            "requires_app_owner_approval": entitlement.get(
                "requires_app_owner_approval", False
            ),
        }

    return entitlement_details, missing_information


def build_transaction(
    status,
    app_profile,
    operation,
    workflow_key,
    fields,
    entitlement_details,
    missing_information,
):
    transaction = {
        "status": status,
        "application_id": app_profile.get("application_id"),
        "application_name": app_profile.get("application_name"),
        "operation": operation,
        "workflow_key": workflow_key,
        "base_url": app_profile.get("base_url"),
        "fields": fields,
    }

    if entitlement_details is not None:
        transaction["entitlement_details"] = entitlement_details

    transaction["validation"] = {
        "status": "PASSED" if status == "READY_FOR_ROUTING" else "FAILED",
        "missing_information": missing_information,
    }

    return transaction


def build_failed_transaction(
    application_id,
    application_name,
    message,
    operation=None,
    base_url=None,
):
    missing_information = [
        {
            "field_name": "operation" if operation is None else "application",
            "message": message,
        }
    ]

    workflow_key = f"{application_id}.{operation}" if application_id and operation else None

    return {
        "status": "FAILED",
        "application_id": application_id,
        "application_name": application_name,
        "operation": operation,
        "workflow_key": workflow_key,
        "base_url": base_url,
        "fields": {},
        "validation": {
            "status": "FAILED",
            "missing_information": missing_information,
        },
    }


def copy_queue_item_to_external_path(transaction):
    """
    Copy queue JSON to external local path.

    UiPath Main.xaml should not rely on project-folder files.
    Instead:
    1. Create Orchestrator Asset: Prompt2Provision_QueueDataPath
    2. Asset value: C:\\Prompt2ProvisionData\\pending_queue_item.json
    3. Main.xaml gets asset, reads file, deserializes JSON, executes workflow.
    """
    EXTERNAL_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(EXTERNAL_QUEUE_FILE, transaction)


def analyze_request(request_text):
    app = detect_application(request_text)

    if app is None:
        return build_failed_transaction(
            application_id=None,
            application_name=None,
            message="Application could not be detected",
        )

    application_id = app["application_id"]
    application_name = app["application_name"]
    app_profile_path = profile_path_for(application_id)

    if not app_profile_path.exists():
        onboarding_required = {
            "status": "APP_ONBOARDING_REQUIRED",
            "application_name": application_name,
            "application_id": application_id,
            "message": "Application profile missing",
        }
        write_json(ONBOARDING_REQUIRED_PATH, onboarding_required)
        return None

    app_profile = load_profile(app_profile_path)

    operation = detect_operation(request_text, app_profile)

    if operation is None:
        return build_failed_transaction(
            application_id=app_profile.get("application_id", application_id),
            application_name=app_profile.get("application_name", application_name),
            message="Operation could not be detected",
            base_url=app_profile.get("base_url"),
        )

    operation_metadata = app_profile["operations"][operation]
    required_fields = operation_metadata.get("required_fields", [])

    fields, missing_information = extract_required_fields(request_text, required_fields)

    entitlement_details, entitlement_errors = validate_entitlements(
        app_profile,
        required_fields,
        fields,
    )

    missing_information.extend(entitlement_errors)

    status = "FAILED" if missing_information else "READY_FOR_ROUTING"
    workflow_key = f"{app_profile.get('application_id', application_id)}.{operation}"

    return build_transaction(
        status=status,
        app_profile=app_profile,
        operation=operation,
        workflow_key=workflow_key,
        fields=fields,
        entitlement_details=entitlement_details,
        missing_information=missing_information,
    )


def main():
    request_text = REQUEST_PATH.read_text(encoding="utf-8")
    transaction = analyze_request(request_text)

    if transaction is None:
        return

    # Local pipeline copy
    write_json(PENDING_QUEUE_ITEM_PATH, transaction)

    # Output/debug copy
    write_json(AUTOMATION_CONTRACT_PATH, transaction)

    # External copy for UiPath Assistant / Studio execution
    copy_queue_item_to_external_path(transaction)

    print("Agent 1 completed.")
    print(f"Local queue item: {PENDING_QUEUE_ITEM_PATH}")
    print(f"Automation contract: {AUTOMATION_CONTRACT_PATH}")
    print(f"External UiPath queue data file: {EXTERNAL_QUEUE_FILE}")


if __name__ == "__main__":
    main()