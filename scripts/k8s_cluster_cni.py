"""Shared helpers for NetworkPolicy-capable CNI on local kind (PS6.5)."""

from __future__ import annotations

import os
import subprocess
import time
import urllib.request

CALICO_VERSION = os.getenv("K8S_CALICO_VERSION", "v3.27.3")
CALICO_MANIFEST_URL = f"https://raw.githubusercontent.com/projectcalico/calico/{CALICO_VERSION}/manifests/calico.yaml"
NETWORK_POLICY_CNI_HINTS = ("calico", "cilium", "antrea", "weave", "canal")
KINDNET_HINT = "kindnet"


def _run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def list_pod_names() -> str:
    proc = _run(
        [
            "kubectl",
            "get",
            "pods",
            "-A",
            "-o",
            'jsonpath={range .items[*]}{.metadata.namespace}/{.metadata.name}{"\\n"}{end}',
        ],
        check=False,
        capture=True,
    )
    return (proc.stdout or "").lower()


def network_policy_cni_present() -> bool:
    names = list_pod_names()
    return any(hint in names for hint in NETWORK_POLICY_CNI_HINTS)


def kindnet_without_policy_cni() -> bool:
    names = list_pod_names()
    return KINDNET_HINT in names and not network_policy_cni_present()


def wait_calico_ready(timeout_seconds: int = 300) -> None:
    deadline = time.time() + timeout_seconds
    selectors = (
        ("kube-system", "k8s-app=calico-node"),
        ("calico-system", "k8s-app=calico-node"),
    )
    while time.time() < deadline:
        for namespace, selector in selectors:
            proc = _run(
                [
                    "kubectl",
                    "get",
                    "pods",
                    "-n",
                    namespace,
                    "-l",
                    selector,
                    "-o",
                    "jsonpath={.items[*].status.conditions[?(@.type=='Ready')].status}",
                ],
                check=False,
                capture=True,
            )
            statuses = [s for s in (proc.stdout or "").split() if s]
            if statuses and all(s == "True" for s in statuses):
                print(f"Calico ready in namespace {namespace!r}")
                return
        time.sleep(5)
    raise SystemExit("Timed out waiting for Calico pods to become Ready")


def allow_workloads_on_control_plane() -> None:
    """Single-node kind: allow scheduling on control-plane after Calico install."""
    _run(
        [
            "kubectl",
            "taint",
            "nodes",
            "--all",
            "node-role.kubernetes.io/control-plane:NoSchedule-",
        ],
        check=False,
    )


def install_calico(*, manifest_url: str = CALICO_MANIFEST_URL) -> None:
    print(f"Installing Calico {CALICO_VERSION} from {manifest_url}")
    with urllib.request.urlopen(manifest_url, timeout=120) as resp:
        manifest = resp.read()
    proc = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=manifest,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit("kubectl apply Calico manifest failed")
    wait_calico_ready()
    allow_workloads_on_control_plane()
    print("Calico installed")


def ensure_calico_cni(*, skip: bool = False) -> None:
    if skip:
        print("Skipping Calico install (K8S_SKIP_CALICO / --skip-calico)")
        return
    if network_policy_cni_present():
        print("NetworkPolicy-capable CNI already present")
        return
    if kindnet_without_policy_cni():
        raise SystemExit(
            "This kind cluster uses kindnet, which does not enforce NetworkPolicy. "
            "Recreate the cluster: make k8s-down && make k8s-up "
            "(kind-config disables default CNI and installs Calico on create)."
        )
    install_calico()


def require_network_policy_cni_or_exit() -> None:
    if network_policy_cni_present():
        print("[ok] NetworkPolicy-capable CNI detected")
        return
    raise SystemExit(
        "No NetworkPolicy-capable CNI detected (expected one of: "
        + ", ".join(NETWORK_POLICY_CNI_HINTS)
        + "). Recreate the local cluster with `make k8s-down && make k8s-up`, "
        "or run with --skip-cross-ns for manifest/RBAC/quota-only checks."
    )
