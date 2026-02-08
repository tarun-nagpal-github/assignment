# CompanySearch – Kubernetes Deployment

Production-style deployment for **60 RPS** target and parallel search + filter load. See [README_INTERVIEWER.md](../README_INTERVIEWER.md#scaling-design) for capacity design.

## Prerequisites

- Kubernetes cluster (e.g. GKE, EKS, AKS, minikube)
- `kubectl` configured
- OpenSearch available (in-cluster or external); set `OPENSEARCH_HOST` in ConfigMap/Secret
- Container images: build and push `companysearch-backend` and `companysearch-frontend` (see below)

## Quick Deploy

```bash
# From project root
kubectl apply -f kubernetes/namespace.yaml
cp kubernetes/secret.yaml.example kubernetes/secret.yaml
# Edit kubernetes/secret.yaml with real OPENSEARCH_INITIAL_ADMIN_PASSWORD and OPENSEARCH_HOST if needed
kubectl apply -f kubernetes/secret.yaml
kubectl apply -f kubernetes/configmap.yaml
# Update configmap with your OpenSearch URL (e.g. internal service or managed OpenSearch endpoint)
kubectl apply -f kubernetes/backend-deployment.yaml
kubectl apply -f kubernetes/frontend-deployment.yaml
kubectl apply -f kubernetes/hpa-backend.yaml
kubectl apply -f kubernetes/pdb-backend.yaml
kubectl apply -f kubernetes/ingress.yaml   # adjust ingressClassName and host for your cluster
```

## Building Images

From project root:

```bash
docker build -t companysearch-backend:latest .
docker build -f docker/Dockerfile.frontend -t companysearch-frontend:latest .
# For a registry:
# docker tag companysearch-backend:latest <registry>/companysearch-backend:latest
# docker push <registry>/companysearch-backend:latest
```

Then set `image` in `backend-deployment.yaml` / `frontend-deployment.yaml` to your registry URL, and `imagePullPolicy` as needed.

## Scaling

- **Backend**: 3 replicas baseline; HPA scales 3–20 on CPU (70%) and memory (80%).
- **Frontend**: 2 replicas (stateless; scale as needed).
- OpenSearch: run as a separate cluster or use a managed service; scale data nodes independently.

## Files

| File | Purpose |
|------|--------|
| `namespace.yaml` | `companysearch` namespace |
| `configmap.yaml` | OPENSEARCH_HOST, OPENSEARCH_USER |
| `secret.yaml.example` | Template for OpenSearch password (copy to `secret.yaml`) |
| `backend-deployment.yaml` | API Deployment + Service, 3 replicas, probes, resources |
| `frontend-deployment.yaml` | UI Deployment + Service |
| `hpa-backend.yaml` | HorizontalPodAutoscaler 3–20, CPU/memory |
| `pdb-backend.yaml` | PodDisruptionBudget minAvailable 2 |
| `ingress.yaml` | Ingress (customize host and class) |

## Validate 60 RPS

See [load-test/](../load-test/README.md) for k6 scripts to drive 60 RPS search and 60 RPS filter (tags) in parallel.
