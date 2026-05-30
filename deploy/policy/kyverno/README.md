# Kyverno / Gatekeeper policy stubs (PS6.5 design note)

PS6.5 ships **NetworkPolicy, ResourceQuota, LimitRange, and namespace-scoped RBAC** in the Helm
chart. **Admission policy** (Kyverno or OPA Gatekeeper) is a **future optional layer** — not
required for PS6.5 Done.

## Recommended prod policies (implement in PS6.7+ or Phase 7)

| Policy | Goal |
|--------|------|
| **Disallow `:latest` image tags in `spaceops-prod`** | Reproducible rollbacks; force digest or semver tag |
| **Require `spaceops.io/environment` label on Namespace** | Prevent accidental deploy to wrong tenant |
| **Require resource requests/limits on Pods** | Complement LimitRange with admission deny |
| **Block `hostPath` volumes in prod** | Reduce node escape surface |

## Example Kyverno ClusterPolicy sketch (not applied by default)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: spaceops-prod-no-latest-tag
spec:
  validationFailureAction: Enforce
  rules:
    - name: disallow-latest
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaces: [spaceops-prod]
      validate:
        message: "prod pods must not use the :latest image tag"
        pattern:
          spec:
            containers:
              - image: "!*:latest"
```

## Gatekeeper equivalent

Use `k8sdisallowedtags` constraint template from Gatekeeper library with namespace selector
`spaceops-prod`.

## When to adopt

- **Stage:** optional dry-run (`validationFailureAction: Audit`) during PS6.7 GitOps bootstrap.
- **Prod:** enforce before first external demo with real keys.

See [k8s_environment_isolation.md](../../docs/runbooks/k8s_environment_isolation.md).
