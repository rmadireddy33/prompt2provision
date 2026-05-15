import json
import shutil
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

ROUTING_FILE = BASE_DIR / "outputs" / "routing_decision.json"
VALIDATION_FILE = BASE_DIR / "outputs" / "validation_result.json"
APPROVAL_FILE = BASE_DIR / "approvals" / "approval_status.json"
CODEX_PROMPT_FILE = BASE_DIR / "prompts" / "agent2_codex_builder_prompt.txt"


def run_python(relative_script):
    print(f"\n=== Running {relative_script} ===")
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / relative_script)],
        cwd=BASE_DIR,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"{relative_script} failed")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_codex_builder():
    print("\n=== Running Agent 2: Codex Builder ===")

    if not CODEX_PROMPT_FILE.exists():
        raise FileNotFoundError("Missing Codex builder prompt")

    prompt = CODEX_PROMPT_FILE.read_text(encoding="utf-8")

    print("\n--- Codex Prompt Preview ---")
    print(prompt[:1000])
    print("--- End Prompt Preview ---\n")

    codex_path = r"C:\Users\ravin\AppData\Roaming\npm\codex.cmd"

    result = subprocess.run(
        [
            codex_path,
            "exec",
            "--skip-git-repo-check",
            "-"
        ],
        cwd=BASE_DIR,
        input=prompt,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError("Codex Builder failed")


from datetime import datetime


def check_approval():
    print("\n=== Human Approval Required ===")

    validation = read_json(VALIDATION_FILE)
    workflow_key = validation.get("workflow_key", "UNKNOWN_WORKFLOW")

    print(f"Workflow Key: {workflow_key}")
    print(f"Validation Status: {validation.get('validation_status')}")
    print("Issues:")
    for issue in validation.get("issues", []):
        print(f"- {issue}")

    decision = input("\nApprove this generated workflow? (y/n): ").strip().lower()

    approved = decision in ["y", "yes"]

    approval = {
        "workflow_key": workflow_key,
        "approved": approved,
        "approved_by": "PowerShell Human Reviewer",
        "approval_reason": "Approved from interactive pipeline prompt" if approved else "Rejected from interactive pipeline prompt",
        "approved_at": datetime.utcnow().isoformat() + "Z"
    }

    APPROVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    APPROVAL_FILE.write_text(json.dumps(approval, indent=2), encoding="utf-8")

    if not approved:
        raise RuntimeError("Human approval rejected.")

    print("Human approval confirmed.")


def main():
    print("\nPrompt2Provision Autonomous Pipeline Started")

    run_python("agents/agent1_requirement_analysis.py")
    run_python("agents/agent4_router.py")

    routing = read_json(ROUTING_FILE)
    decision = routing.get("decision")

    print(f"\nRouter Decision: {decision}")

    if decision == "APP_ONBOARDING_REQUIRED":
        print("Application profile missing. Human must provide app URL, entitlement catalog, and operation metadata.")
        return

    if decision == "UI_MAP_REQUIRED":
        print("UI map missing. Human must provide operation navigation steps.")
        return

    if decision == "STOP_INVALID_REQUEST":
        print("Request validation failed. Check outputs/automation_contract.json.")
        return

    if decision == "BUILD_WORKFLOW":
        run_codex_builder()
        run_python("agents/agent3_validator.py")

        validation = read_json(VALIDATION_FILE)
        if validation.get("validation_status") != "PASSED":
            raise RuntimeError("Validation failed. Workflow will not be approved.")

        check_approval()
        run_python("agents/agent5_registry_update.py")
        #run_python("agents/executor_bot.py")
        run_python("agents/agent7_orchestrator_run_repair.py")

    elif decision == "EXECUTE_WORKFLOW":
        run_python("agents/executor_bot.py")
        run_python("agents/agent7_orchestrator_run_repair.py")

    else:
        raise RuntimeError(f"Unknown routing decision: {decision}")

    print("\nPrompt2Provision Pipeline Completed Successfully")


if __name__ == "__main__":
    main()
