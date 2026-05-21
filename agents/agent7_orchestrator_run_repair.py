import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).resolve().parents[1]

QUEUE_ITEM_PATH = ROOT_DIR / "queues" / "pending_queue_item.json"
REGISTRY_PATH = ROOT_DIR / "registry" / "workflow_registry.json"
OUTPUT_DIR = ROOT_DIR / "outputs"
PROMPTS_DIR = ROOT_DIR / "prompts"

JOB_RESULT_PATH = OUTPUT_DIR / "orchestrator_job_result.json"
EXECUTION_TEST_RESULT_PATH = OUTPUT_DIR / "execution_test_result.json"
REPAIR_HISTORY_PATH = OUTPUT_DIR / "repair_history.json"
REPAIR_PROMPT_PATH = PROMPTS_DIR / "agent8_selector_repair_prompt.txt"

PROJECT_PATH = ROOT_DIR / "uipath_project"
PACKAGE_OUTPUT_DIR = ROOT_DIR / "outputs" / "packages"

MAX_REPAIR_ATTEMPTS = 2
DEFAULT_ORCHESTRATOR_FOLDER_PATH = "Development"
DEFAULT_PROCESS_NAME = "Prompt2ProvisionUiPath"
DEFAULT_RUNTIME_TYPE = ""
DEFAULT_PACKAGE_KEY = "Prompt2ProvisionUiPath"
VALID_RUNTIME_TYPES = {
    "Unattended",
    "Headless",
    "Serverless",
    "NonProduction",
    "Development",
    "TestAutomation",
}


def resolve_command(command):
    name = command[0]

    if os.name == "nt" and name == "uip":
        npm_uip_cmd = Path.home() / "AppData" / "Roaming" / "npm" / "uip.cmd"
        if npm_uip_cmd.exists():
            return [str(npm_uip_cmd), *command[1:]]

        npm_uip_ps1 = Path.home() / "AppData" / "Roaming" / "npm" / "uip.ps1"
        if npm_uip_ps1.exists():
            return [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(npm_uip_ps1),
                *command[1:]
            ]

    resolved = shutil.which(name)
    if resolved:
        return [resolved, *command[1:]]

    return command


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_text_any_encoding(path):
    for encoding in ("utf-8", "utf-16"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    return None


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_command(command):
    resolved_command = resolve_command(command)
    print(f"\nRunning command: {' '.join(command)}")

    try:
        result = subprocess.run(
            resolved_command,
            cwd=ROOT_DIR,
            text=True,
            capture_output=True
        )
    except FileNotFoundError as exc:
        return {
            "returncode": 127,
            "stdout": "",
            "stderr": f"Executable not found: {command[0]} ({exc})"
        }

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


def parse_command_json(result):
    output = (result.get("stdout") or "").strip()
    if not output:
        return None

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def package_upload_succeeded(result):
    if result.get("returncode") == 0:
        return True

    text = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
    return "package already exists" in text


def command_output_text(result):
    if not result:
        return ""

    parts = [
        result.get("stderr", ""),
        result.get("stdout", ""),
    ]

    result_json = parse_command_json(result)
    if isinstance(result_json, dict):
        data = result_json.get("Data")
        if isinstance(data, dict):
            parts.extend([
                str(data.get("Info") or ""),
                str(data.get("ErrorCode") or ""),
                str(data.get("State") or ""),
            ])
            job_error = data.get("JobError")
            if isinstance(job_error, dict):
                parts.extend(str(value) for value in job_error.values() if value)
        parts.extend([
            str(result_json.get("Code") or ""),
            str(result_json.get("Result") or ""),
            str(result_json.get("Message") or ""),
        ])

    return "\n".join(part for part in parts if part)


def job_error_text(job_result):
    return "\n".join(
        part for part in [
            command_output_text(job_result.get("command_result")),
            command_output_text(job_result.get("fallback_result")),
            str(job_result.get("terminal_state") or ""),
        ]
        if part
    )


def registry_workflow_path(workflow_key):
    registry = read_json(REGISTRY_PATH)
    return registry.get(workflow_key, {}).get("workflow_path")


def workflow_object_references(workflow_path):
    if not workflow_path:
        return []

    path = ROOT_DIR / workflow_path
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    references = re.findall(r'Reference="([^"]+)"', text)
    return sorted(set(references))


def object_repository_files_for_references(references):
    objects_dir = PROJECT_PATH / ".objects"
    if not references or not objects_dir.exists():
        return []

    matched_files = []
    reference_set = set(references)
    for path in objects_dir.rglob("*"):
        if not path.is_file():
            continue

        content = None
        content = read_text_any_encoding(path)

        if content and any(reference in content for reference in reference_set):
            matched_files.append(path)
            if path.name == ".metadata":
                data_dir = path.parent / ".data"
                if data_dir.exists():
                    matched_files.extend(
                        sibling
                        for sibling in data_dir.rglob("*")
                        if sibling.is_file()
                    )

    return sorted(
        str(path.relative_to(ROOT_DIR)).replace("\\", "/")
        for path in set(matched_files)
    )


def parse_xml_attributes(attribute_text):
    return dict(re.findall(r'([A-Za-z_:][\w:.-]*)="([^"]*)"', attribute_text))


def referenced_workflow_targets(workflow_path):
    if not workflow_path:
        return []

    path = ROOT_DIR / workflow_path
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    targets = []
    for match in re.finditer(r"<uix:(TargetAnchorable|TargetApp)\s+([^>]*)/>", text):
        target_type, attribute_text = match.groups()
        attributes = parse_xml_attributes(attribute_text)
        reference = attributes.get("Reference")
        if reference:
            targets.append({
                "type": target_type,
                "reference": reference,
                "attributes": attributes,
            })

    return targets


def object_repository_reference_map():
    objects_dir = PROJECT_PATH / ".objects"
    if not objects_dir.exists():
        return {}

    references = {}
    for metadata_path in objects_dir.rglob("*"):
        if not metadata_path.is_file() or metadata_path.name != ".metadata":
            continue

        try:
            metadata = read_json(metadata_path)
        except (json.JSONDecodeError, UnicodeError):
            continue

        reference = metadata.get("Reference")
        if reference:
            references[reference] = {
                "metadata_path": metadata_path,
                "object_dir": metadata_path.parent,
                "type": metadata.get("Type"),
            }

    return references


def object_repository_content_path(object_dir, target_type):
    if target_type == "TargetApp":
        return object_dir / ".data" / "ObjectRepositoryScreenData" / ".content"

    return object_dir / ".data" / "ObjectRepositoryTargetData" / ".content"


def object_repository_target_attributes(content, target_type):
    if not content:
        return {}

    match = re.search(rf"<{target_type}\s+([^>]*)>", content)
    if not match:
        return {}

    return parse_xml_attributes(match.group(1))


def validate_object_repository_consistency(workflow_path):
    targets = referenced_workflow_targets(workflow_path)
    if not targets:
        return []

    reference_map = object_repository_reference_map()
    issues = []
    comparable_attributes = {
        "TargetApp": ("Selector", "Url", "BrowserType"),
        "TargetAnchorable": ("FullSelectorArgument", "ScopeSelectorArgument", "SearchSteps", "Version"),
    }

    for target in targets:
        reference = target["reference"]
        repository_entry = reference_map.get(reference)
        if not repository_entry:
            issues.append(f"{reference}: missing Object Repository metadata entry")
            continue

        content_path = object_repository_content_path(repository_entry["object_dir"], target["type"])
        if not content_path.exists():
            issues.append(
                f"{reference}: missing Object Repository content file {content_path.relative_to(ROOT_DIR)}"
            )
            continue

        content = read_text_any_encoding(content_path)
        repository_attributes = object_repository_target_attributes(content, target["type"])
        if not repository_attributes:
            issues.append(f"{reference}: could not read {target['type']} attributes from Object Repository content")
            continue

        for attribute in comparable_attributes[target["type"]]:
            workflow_value = target["attributes"].get(attribute)
            repository_value = repository_attributes.get(attribute)
            if workflow_value and repository_value != workflow_value:
                issues.append(
                    f"{reference}: Object Repository {attribute} does not match workflow target"
                )

    return issues


def target_folder_path():
    return os.environ.get("PROMPT2PROVISION_FOLDER_PATH", DEFAULT_ORCHESTRATOR_FOLDER_PATH)


def target_folder_option():
    return ["--folder-path", target_folder_path()]


def list_target_processes(process_name=None):
    command = [
        "uip",
        "or",
        "processes",
        "list",
        *target_folder_option(),
    ]
    if process_name:
        command.extend(["--name", process_name])
    command.extend(["--output", "json"])
    return run_command(command)


def find_process(process_name, package_key):
    process_lookup = list_target_processes(process_name)
    process_lookup_json = parse_command_json(process_lookup)
    processes = (process_lookup_json or {}).get("Data") or []
    matching_processes = [
        process for process in processes
        if process.get("Name") == process_name or process.get("ProcessKey") == package_key
    ]
    return (matching_processes[0] if matching_processes else None), process_lookup


def parse_version(value):
    if not value:
        return None

    parts = str(value).strip().split(".")
    if len(parts) < 3 or not all(part.isdigit() for part in parts):
        return None

    return tuple(int(part) for part in parts)


def max_version(versions):
    numeric_versions = [version for version in versions if parse_version(version) is not None]
    if not numeric_versions:
        return None

    return max(numeric_versions, key=parse_version)


def next_patch_version(version):
    parsed = parse_version(version)
    if parsed is None:
        raise ValueError(f"Cannot bump non-numeric version: {version}")

    parts = list(parsed)
    parts[-1] += 1
    return ".".join(str(part) for part in parts)


def list_package_versions(package_key):
    result = run_command([
        "uip",
        "or",
        "packages",
        "list",
        "--search",
        package_key,
        "--limit",
        "100",
        "--all-fields",
        "--output",
        "json"
    ])

    result_json = parse_command_json(result)
    packages = (result_json or {}).get("Data") or []
    versions = []
    if isinstance(packages, list):
        for package in packages:
            if not isinstance(package, dict):
                continue
            package_id = (
                package.get("Id")
                or package.get("id")
                or package.get("Title")
                or package.get("title")
                or package.get("PackageId")
                or package.get("packageId")
            )
            package_key_value = package.get("Key") or package.get("key") or ""
            if package_id == package_key or str(package_key_value).startswith(f"{package_key}:"):
                versions.append(package.get("Version") or package.get("version"))

    return versions, result


def resolve_deployment_target():
    desired_process_name = os.environ.get("PROMPT2PROVISION_PROCESS_NAME", DEFAULT_PROCESS_NAME)
    desired_package_key = os.environ.get("PROMPT2PROVISION_PACKAGE_KEY", DEFAULT_PACKAGE_KEY)

    process, process_lookup = find_process(desired_process_name, desired_package_key)
    if process:
        return {
            "process": process,
            "process_lookup": process_lookup,
            "process_name": process.get("Name", desired_process_name),
            "package_key": process.get("ProcessKey", desired_package_key),
        }

    folder_processes_result = list_target_processes()
    folder_processes_json = parse_command_json(folder_processes_result)
    folder_processes = (folder_processes_json or {}).get("Data") or []
    if len(folder_processes) == 1:
        existing_process = folder_processes[0]
        return {
            "process": existing_process,
            "process_lookup": folder_processes_result,
            "process_name": existing_process.get("Name", desired_process_name),
            "package_key": existing_process.get("ProcessKey", desired_package_key),
        }

    return {
        "process": None,
        "process_lookup": process_lookup,
        "process_name": desired_process_name,
        "package_key": desired_package_key,
    }


def is_uip_interceptor_failure(result):
    text = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
    return "interceptors did not return an alternative response" in text


def find_uirobot_executable():
    studio_root = Path.home() / "AppData" / "Local" / "Programs" / "UiPathPlatform" / "Studio"
    preferred = studio_root / "26.0.192-cloud.22848" / "UiRobot.exe"
    if preferred.exists():
        return str(preferred)

    if not studio_root.exists():
        return None

    candidates = [
        path / "UiRobot.exe"
        for path in studio_root.iterdir()
        if path.is_dir() and (path / "UiRobot.exe").exists()
    ]
    if not candidates:
        return None

    return str(max(candidates, key=lambda path: path.stat().st_mtime))


def powershell_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def run_local_robot_process(process_name, folder_path):
    uirobot = find_uirobot_executable()
    if not uirobot:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": "UiRobot.exe was not found under the local UiPathPlatform Studio installation."
        }

    script = (
        f"& {powershell_quote(uirobot)} execute "
        f"--process-name {powershell_quote(process_name)} "
        f"--folder {powershell_quote(folder_path)}"
    )
    print(f"\nRunning command: {uirobot} execute --process-name {process_name} --folder {folder_path}")

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script
        ],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


def detect_selector_issue(text):
    if not text:
        return False

    lower = text.lower()

    selector_keywords = [
        "selector",
        "ui element not found",
        "target not found",
        "element not found",
        "activity timeout",
        "timeout",
        "could not find ui element",
        "failed to find element",
        "element no longer valid",
        "check state",
        "ncheckstate",
        "did not appear before clicking",
        "navigation did not appear",
        "navigation missing",
        "admin navigation missing",
    ]

    return any(keyword in lower for keyword in selector_keywords)


def start_orchestrator_job(queue_item):
    """
    Start the deployed Orchestrator process for this pipeline run.
    """

    deployment_target = resolve_deployment_target()
    process_name = deployment_target["process_name"]
    package_key = deployment_target["package_key"]
    folder_path = target_folder_path()
    requested_runtime_type = os.environ.get("PROMPT2PROVISION_RUNTIME_TYPE", DEFAULT_RUNTIME_TYPE).strip()
    runtime_type = requested_runtime_type if requested_runtime_type in VALID_RUNTIME_TYPES else ""

    process = deployment_target.get("process")
    process_lookup = deployment_target.get("process_lookup")
    if not process:
        job_result = {
            "timestamp": utc_timestamp(),
            "workflow_key": queue_item.get("workflow_key"),
            "application_id": queue_item.get("application_id"),
            "operation": queue_item.get("operation"),
            "process_name": process_name,
            "folder": folder_path,
            "runtime_type": runtime_type or "folder_default",
            "requested_runtime_type": requested_runtime_type,
            "process_lookup_result": process_lookup,
            "command_result": {
                "returncode": 1,
                "stdout": "",
                "stderr": f"No process matching '{process_name}' found in folder '{folder_path}'."
            },
            "status": "FAILED"
        }
        write_json(JOB_RESULT_PATH, job_result)
        write_json(EXECUTION_TEST_RESULT_PATH, job_result)
        return job_result

    process_key = process.get("Key")
    process_name = process.get("Name", process_name)
    process_version = process.get("ProcessVersion")

    command = [
        "uip",
        "or",
        "jobs",
        "start",
        process_key,
        *target_folder_option(),
    ]
    if runtime_type:
        command.extend(["--runtime-type", runtime_type])
    command.extend([
        "--run-as-me",
        "--wait-for-completion",
        "--timeout",
        os.environ.get("PROMPT2PROVISION_JOB_TIMEOUT_SECONDS", "300"),
        "--output",
        "json"
    ])

    result = run_command(command)
    fallback_result = None

    if result["returncode"] != 0 and is_uip_interceptor_failure(result):
        print("UiPath CLI Orchestrator call failed in Python context. Falling back to local UiRobot execution.")
        fallback_result = run_local_robot_process(process_name, folder_path)
        if fallback_result["returncode"] == 0:
            result = fallback_result

    result_json = parse_command_json(result)
    job_data = (result_json or {}).get("Data") or {}
    jobs = job_data.get("Jobs") if isinstance(job_data, dict) else None
    first_job = jobs[0] if isinstance(jobs, list) and jobs else {}
    terminal_state = (
        job_data.get("State")
        or job_data.get("state")
        or first_job.get("State")
        or first_job.get("state")
    )
    failed_states = {"Faulted", "Stopped"}
    succeeded = (
        result["returncode"] == 0
        and (result_json or {}).get("Result") != "Failure"
        and terminal_state not in failed_states
    )

    job_result = {
        "timestamp": utc_timestamp(),
        "workflow_key": queue_item.get("workflow_key"),
        "application_id": queue_item.get("application_id"),
        "operation": queue_item.get("operation"),
        "process_name": process_name,
        "process_version": process_version,
        "folder": folder_path,
        "runtime_type": runtime_type or "folder_default",
        "requested_runtime_type": requested_runtime_type,
        "terminal_state": terminal_state,
        "process_lookup_result": process_lookup,
        "command_result": result,
        "fallback_result": fallback_result,
        "status": "SUCCESS" if succeeded else "FAILED"
    }

    write_json(JOB_RESULT_PATH, job_result)
    write_json(EXECUTION_TEST_RESULT_PATH, job_result)
    return job_result


def create_repair_prompt(queue_item, job_result):
    workflow_key = queue_item.get("workflow_key")
    application_id = queue_item.get("application_id")
    application_name = queue_item.get("application_name") or application_id
    operation = queue_item.get("operation")
    base_url = queue_item.get("base_url")

    registry = read_json(REGISTRY_PATH)
    workflow_path = registry.get(workflow_key, {}).get("workflow_path")
    object_references = workflow_object_references(workflow_path)
    object_repository_files = object_repository_files_for_references(object_references)

    error_text = job_error_text(job_result)
    object_repository_section = "\n".join(
        f"- {path}" for path in object_repository_files
    ) or "- No matching Object Repository files were found for the workflow references."

    prompt = f"""
You are Agent 8: UiPath Selector Repair Agent.

The Orchestrator job failed for:

Workflow key:
{workflow_key}

Application ID:
{application_id}

Operation:
{operation}

Workflow path:
{workflow_path}

Source files:
- queues/pending_queue_item.json
- app_profiles/{application_id}.json
- app_profiles/{application_id}_ui_map.json
- {workflow_path}

Object Repository files currently referenced by this workflow:
{object_repository_section}

Base URL:
{base_url}

Error output:
{error_text}

Your task:
1. Inspect the failed workflow XAML.
2. Inspect app_profiles/{application_id}.json.
3. Inspect app_profiles/{application_id}_ui_map.json.
4. Identify the failed step from the Orchestrator error and workflow stack trace.
5. Fix selector, UIAutomation, timeout, or synchronization issues.
6. Use Modern UiPath UIAutomation activities.
7. Keep values dynamic; do not hardcode runtime request values.
8. Add Check App State / Wait for Element Appear where needed.
9. Update the workflow file.
10. Update the Object Repository files listed above for every repaired target whose workflow XAML keeps an Object Repository `Reference`.
11. Update README.md with repair notes.
12. Do not create placeholder-only workflows.

Fast repair scope:
- Do not perform a broad repository rewrite. Focus on the failed activity from the stack trace plus the immediately dependent targets needed to reach and validate that screen.
- Use the source files above as the starting set. Search elsewhere only when the failed workflow references another local file.
- Prefer patching the captured target for the failing OR element over recreating unrelated screens or elements.

Live UI target capture requirements:
- Match Agent 2's selector standard: use strict {application_name} selectors captured from the live browser/UI screen during repair.
- Do not read selectors from `app_profiles/*.json` or `app_profiles/*_ui_map.json`; profiles only define operations, fields, steps, and success text.
- Get repaired selectors from the browser/UI screen itself using UiPath UI Automation capture.
- Start with a UIA window baseline, then capture the failed interaction target and any dependent targets screen by screen.
- Use `uip rpa uia` / target configuration output as the source of truth for `NApplicationCard`, `NClick`, `NTypeInto`, `NGetText`, and related targets.
- Treat `uip rpa uia snapshot inspect` plus `uip rpa uia interact get-all <ref>` output from the live browser/UI as valid live capture evidence when it reports element attributes such as `id`, `tag`, `title`, `url`, and `app`.
- If `uip rpa uia snapshot capture` fails with a transient Studio named-pipe error such as `connect EPERM \\\\.\\pipe\\UiPathStudio_*`, do not infer selectors from the error output. Retry with `--log-level debug`; if it still fails, use `snapshot inspect` to identify the live browser tab and `interact get-all` on the relevant element refs before deciding live capture is blocked.
- A "closest selector matches" list in the runtime failure is diagnostic only. It can point to candidates to verify, but it is not selector evidence unless the same selector is confirmed through live UIA capture/inspection.
- Do not hand-write, guess, or persist selectors in the app profile.
- Store selector evidence only in the generated UiPath workflow/Object Repository artifacts and optional workflow README notes.
- If the browser is not already on the required screen, open the application from `in_BaseUrl` / queue base_url and navigate through the operation steps before capturing.
- If live capture cannot be completed, stop with a clear blocker instead of guessing selectors.

Object Repository repair requirements:
- If you change a `TargetAnchorable` or `TargetApp` in the XAML and it has a `Reference`, update the matching `.objects/**/ObjectRepositoryTargetData/.content` or `.objects/**/ObjectRepositoryScreenData/.content` file with the same captured selector, target metadata, and screenshot reference.
- Preserve existing Object Repository references when possible. If capture creates a replacement reference, update the workflow XAML, the matching `.metadata`, and any affected OR screen/element content so the project does not contain stale referenced targets.
- Do not leave a selector fixed only in XAML while the referenced Object Repository target still contains the old selector.
- Before finishing, verify that each changed XAML `Reference` value has a corresponding `.objects` metadata/content entry and that the selector in the OR content matches the selector in the workflow target.

Validation requirements before finishing repair:
- Run `uip rpa get-errors --file-path "{workflow_path}" --project-dir "uipath_project" --output json` and fix every diagnostic.
- Run `uip rpa build "uipath_project" --output json` and fix build failures before packaging or approval.
- Treat `get-errors` success alone as insufficient because build catches invalid activity members and enum values.

After repairing, the project will check the current Orchestrator package/process version,
package the next patch version, deploy it, and run again.
"""
    write_text(REPAIR_PROMPT_PATH, prompt.strip())


def run_codex_repair():
    prompt = REPAIR_PROMPT_PATH.read_text(encoding="utf-8")

    # Update this path if needed.
    codex_path = r"C:\Users\ravin\AppData\Roaming\npm\codex.cmd"

    result = subprocess.run(
        [
            codex_path,
            "exec",
            "--skip-git-repo-check",
            "-"
        ],
        cwd=ROOT_DIR,
        input=prompt,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError("Codex repair failed")


def package_project(package_key=None):
    PACKAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    command = [
        "uip",
        "rpa",
        "pack",
        str(PROJECT_PATH),
        str(PACKAGE_OUTPUT_DIR),
        "--output",
        "json"
    ]
    if package_key:
        command.extend(["--package-id", package_key])
    command.extend([
        "--package-version",
        get_project_version(),
        "--include-sources",
    ])

    result = run_command(command)
    result["package_path"] = None
    result["source_verification"] = None

    if result.get("returncode") != 0:
        return result

    result_json = parse_command_json(result)
    packages = ((result_json or {}).get("Data") or {}).get("Packages") or []
    package_path = Path(packages[0]) if packages else expected_package_path(package_key)
    result["package_path"] = str(package_path)

    verification = verify_package_contains_project_sources(package_path)
    result["source_verification"] = verification
    if not verification["ok"]:
        result["returncode"] = 1
        result["stderr"] = "\n".join(
            part for part in [
                result.get("stderr", "").rstrip(),
                "Package source verification failed:",
                *[f"- missing {entry}" for entry in verification["missing_entries"]],
            ]
            if part
        )

    return result


def get_project_version():
    project_json = read_json(PROJECT_PATH / "project.json")
    return project_json.get("projectVersion")


def set_project_version(version):
    project_json_path = PROJECT_PATH / "project.json"
    project_json = read_json(project_json_path)
    previous_version = str(project_json.get("projectVersion") or "")
    project_json["projectVersion"] = version
    write_json(project_json_path, project_json)
    return previous_version, version


def expected_package_path(package_key=None):
    package_key = package_key or os.environ.get("PROMPT2PROVISION_PACKAGE_KEY", DEFAULT_PACKAGE_KEY)
    return PACKAGE_OUTPUT_DIR / f"{package_key}.{get_project_version()}.nupkg"


def verify_package_contains_project_sources(package_path):
    package_path = Path(package_path)
    if not package_path.exists():
        return {
            "ok": False,
            "package_path": str(package_path),
            "missing_entries": [str(package_path)],
        }

    expected_entries = [
        "content/" + str(path.relative_to(PROJECT_PATH)).replace("\\", "/")
        for path in PROJECT_PATH.rglob("*.xaml")
        if path.is_file()
    ]

    with zipfile.ZipFile(package_path) as package:
        package_entries = set(package.namelist())

    missing_entries = [
        entry for entry in expected_entries
        if entry not in package_entries
    ]

    return {
        "ok": not missing_entries,
        "package_path": str(package_path),
        "expected_entries": expected_entries,
        "missing_entries": missing_entries,
    }


def prepare_next_orchestrator_version(deployment_target):
    package_key = deployment_target["package_key"]
    process = deployment_target.get("process") or {}
    process_version = process.get("ProcessVersion")
    local_project_version = get_project_version()
    package_versions, package_lookup_result = list_package_versions(package_key)
    if package_lookup_result.get("returncode") != 0:
        if process_version and is_uip_interceptor_failure(package_lookup_result):
            package_versions = []
        else:
            raise RuntimeError(
                f"Could not check current Orchestrator package versions for '{package_key}'."
            )
    orchestrator_version = max_version([process_version, *package_versions])
    highest_known_version = max_version([
        local_project_version,
        process_version,
        *package_versions,
    ])

    if highest_known_version:
        next_version = next_patch_version(highest_known_version)
        if highest_known_version == local_project_version:
            source = "local_project"
        elif highest_known_version == process_version:
            source = "orchestrator_process"
        else:
            source = "package_feed"
    else:
        next_version = "1.0.0"
        source = "local_default"

    previous_version, project_version = set_project_version(next_version)
    return {
        "previous_project_version": previous_version,
        "package_version": project_version,
        "orchestrator_current_version": orchestrator_version,
        "highest_known_version": highest_known_version,
        "local_project_version": local_project_version,
        "version_source": source,
        "process_version": process_version,
        "package_feed_versions": package_versions,
        "package_lookup_result": package_lookup_result,
    }


def deploy_project(deployment_target=None, package_path=None):
    """
    Upload the package to the tenant feed and bind it only in Development.
    under the stable Prompt2Provision process name.
    """

    deployment_target = deployment_target or resolve_deployment_target()
    package_key = deployment_target["package_key"]
    package_path = Path(package_path) if package_path else expected_package_path(package_key)
    process_name = deployment_target["process_name"]
    package_version = get_project_version()
    folder_path = target_folder_path()

    expected_package = expected_package_path(package_key)
    if package_path.resolve() != expected_package.resolve():
        return {
            "returncode": 1,
            "package_path": str(package_path),
            "folder": folder_path,
            "process_name": process_name,
            "package_key": package_key,
            "package_version": package_version,
            "upload_status": "not_attempted",
            "upload_result": {
                "returncode": 1,
                "stdout": "",
                "stderr": (
                    f"Refusing to deploy {package_path}; expected freshly packed "
                    f"artifact {expected_package}."
                ),
            },
            "process_lookup_result": deployment_target.get("process_lookup"),
            "process_result": None,
        }

    upload_result = run_command([
        "uip",
        "or",
        "packages",
        "upload",
        str(package_path),
        "--output",
        "json"
    ])

    process_result = None
    process = deployment_target.get("process")
    process_lookup = deployment_target.get("process_lookup")

    if process:
        resolved_process_key = process.get("Key")
        process_result = run_command([
            "uip",
            "or",
            "processes",
            "update-version",
            resolved_process_key,
            *target_folder_option(),
            "--package-version",
            package_version,
            "--output",
            "json"
        ])
    else:
        process_result = run_command([
            "uip",
            "or",
            "processes",
            "create",
            *target_folder_option(),
            "--name",
            process_name,
            "--package-key",
            package_key,
            "--package-version",
            package_version,
            "--entry-point",
            "Main.xaml",
            "--visible-for-attended",
            "--description",
            "Reusable UiPath workflows generated by Prompt2Provision.",
            "--output",
            "json"
        ])

    upload_succeeded = package_upload_succeeded(upload_result)
    process_succeeded = process_result is not None and process_result["returncode"] == 0

    return {
        "returncode": 0 if upload_succeeded and process_succeeded else 1,
        "package_path": str(package_path),
        "folder": folder_path,
        "process_name": process_name,
        "package_key": package_key,
        "package_version": package_version,
        "upload_status": "uploaded_or_already_exists" if upload_succeeded else "failed",
        "upload_result": upload_result,
        "process_lookup_result": process_lookup,
        "process_result": process_result,
    }


def append_repair_history(entry):
    if REPAIR_HISTORY_PATH.exists():
        history = read_json(REPAIR_HISTORY_PATH)
    else:
        history = []

    if isinstance(history, list):
        history.append(entry)
    elif isinstance(history, dict):
        if not isinstance(history.get("attempts"), list):
            history["attempts"] = []
        history["attempts"].append(entry)
        history["timestamp"] = utc_timestamp()
        history["max_repair_attempts"] = MAX_REPAIR_ATTEMPTS
    else:
        history = [entry]

    write_json(REPAIR_HISTORY_PATH, history)


def main():
    queue_item = read_json(QUEUE_ITEM_PATH)

    print("\n=== Agent 7: Orchestrator Run / Repair ===")

    job_result = start_orchestrator_job(queue_item)

    if job_result["status"] == "SUCCESS":
        print("Orchestrator job started and executed successfully.")
        return

    error_text = job_error_text(job_result)

    if not detect_selector_issue(error_text):
        print("Job failed, but failure does not look like selector/UI issue.")
        print("Job failed, but was not classified as selector/UI issue.")
        print("Check outputs/orchestrator_job_result.json for details.")
        return

    print("Selector/UI issue detected. Starting repair loop.")

    for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
        print(f"\nRepair attempt {attempt} of {MAX_REPAIR_ATTEMPTS}")

        create_repair_prompt(queue_item, job_result)
        run_codex_repair()

        object_repository_issues = validate_object_repository_consistency(
            registry_workflow_path(queue_item.get("workflow_key"))
        )
        if object_repository_issues:
            raise RuntimeError(
                "Object Repository consistency check failed after repair:\n"
                + "\n".join(f"- {issue}" for issue in object_repository_issues)
            )

        deployment_target = resolve_deployment_target()
        version_info = prepare_next_orchestrator_version(deployment_target)
        package_result = package_project(deployment_target["package_key"])
        deploy_result = deploy_project(deployment_target, package_result.get("package_path"))
        if package_result["returncode"] != 0 or deploy_result["returncode"] != 0:
            repair_entry = {
                "attempt": attempt,
                "timestamp": utc_timestamp(),
                "workflow_key": queue_item.get("workflow_key"),
                **version_info,
                "package_result": package_result,
                "deploy_result": deploy_result,
                "rerun_result": None
            }
            append_repair_history(repair_entry)
            raise RuntimeError("Package/deploy step failed after repair.")

        rerun_result = start_orchestrator_job(queue_item)

        repair_entry = {
            "attempt": attempt,
            "timestamp": utc_timestamp(),
            "workflow_key": queue_item.get("workflow_key"),
            **version_info,
            "package_result": package_result,
            "deploy_result": deploy_result,
            "rerun_result": rerun_result
        }

        append_repair_history(repair_entry)

        if rerun_result["status"] == "SUCCESS":
            print("Repair successful. Job succeeded after redeploy.")
            return

        rerun_error_text = job_error_text(rerun_result)
        if not detect_selector_issue(rerun_error_text):
            print("Rerun failed, but the remaining failure does not look like a selector/UI issue.")
            print("Stopping repair loop to avoid changing selectors for a non-UI failure.")
            return

        job_result = rerun_result

    raise RuntimeError("Repair attempts exhausted. Job still failing.")


if __name__ == "__main__":
    main()
