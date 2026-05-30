# Local Kubernetes (PS6.3)

Default tool: **kind** (`infra/k8s/local/kind-config.yaml`).

Operator entrypoints:

```bash
make k8s-up      # create cluster, load images, helm install minimal dev profile
make k8s-status  # pods in spaceops-dev
make k8s-smoke   # port-forward + GET /health
make k8s-down    # helm uninstall + kind delete cluster
```

Full runbook: [docs/runbooks/local_k8s_dev.md](../../../docs/runbooks/local_k8s_dev.md).
