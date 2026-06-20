# Grafana (Compose)

Dashboard and datasource provisioning for the **Grafana** service in `infra/docker-compose.yml`
(local port **3000**, default admin/admin — change before shared demos).

| Path | Role |
|------|------|
| **provisioning/dashboards/** | SpaceOps dashboard JSON + provider config. |
| **provisioning/datasources/** | Prometheus datasource pointing at compose Prometheus. |

Not deployed by Helm on stage/GKE (see PS7.4 analysis).
