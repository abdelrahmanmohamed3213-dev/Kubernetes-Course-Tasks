# Task 2: Kubernetes Web Application and MySQL

## Overview

This task deploys a two-tier application stack on Kubernetes:

- A FastAPI application exposed through a ClusterIP Service and Ingress.
- A single MySQL instance exposed only inside the cluster.
- A PersistentVolume and PersistentVolumeClaim for MySQL data.
- A Namespace for isolating all task resources.

The application image is intended to listen on port `8000` and provide an HTTP
health endpoint at `/health`. The MySQL image is intended to listen on port
`3306` and persist its data under `/var/lib/mysql`.

## Repository layout

```text
task-2/
|-- infra/
|   |-- namespace.yaml
|   |-- app/
|   |   |-- config.yaml
|   |   |-- deployment.yaml
|   |   |-- ingress.yaml
|   |   `-- service.yaml
|   `-- storage/
|       |-- deployment.yaml
|       |-- pvc.yaml
|       |-- pv.yaml
|       |-- sec.yaml
|       `-- service.yaml
|-- public/
`-- readme.md
```

## Resources

| Resource | Name | Namespace | Purpose |
|---|---|---|---|
| Namespace | `webapp-stack` | - | Isolates this task |
| ConfigMap | `webapp-config` | `webapp-stack` | Application and database settings |
| Secret | `mysql-secret` | `webapp-stack` | Demo MySQL credentials |
| Deployment | `webapp-api` | `webapp-stack` | Runs the application |
| Service | `webapp-api` | `webapp-stack` | Exposes the application internally on port 80 |
| Ingress | `webapp-ingress` | `webapp-stack` | Routes external HTTP traffic to the application |
| Deployment | `mysql` | `webapp-stack` | Runs MySQL |
| Service | `mysql` | `webapp-stack` | Exposes MySQL internally on port 3306 |
| PersistentVolume | `mysql-pv` | - | Provides 2 GiB storage at `/data/webapp-mysql` |
| PersistentVolumeClaim | `mysql-pvc` | `webapp-stack` | Requests 2 GiB for MySQL |

The application Deployment uses `webapp-api:task2`. The MySQL Deployment uses
`webapp-mysql:task2`. These are local learning images and must already be
available to the Kubernetes nodes.

The PersistentVolume uses `hostPath` and `storageClassName: manual`, so it is
not portable across clusters or nodes. Use a cluster-provisioned storage class
for a real deployment.

## Requirements

- A working Kubernetes cluster and `kubectl` context.
- An NGINX Ingress controller for the Ingress resource.
- Container images named `webapp-api:task2` and `webapp-mysql:task2` available
  to the cluster nodes.
- A node-local directory at `/data/webapp-mysql` for the hostPath volume.
- `curl` for optional HTTP verification.

Check cluster access before deployment:

```sh
kubectl cluster-info
kubectl get nodes
kubectl get storageclass
```

## Deploy

Run the commands from the `task-2` directory:

```sh
kubectl apply -f infra/namespace.yaml
kubectl apply -f infra/storage/pv.yaml
kubectl apply -f infra/storage/sec.yaml
kubectl apply -f infra/storage/pvc.yaml
kubectl apply -f infra/storage/deployment.yaml
kubectl apply -f infra/storage/service.yaml
kubectl apply -f infra/app/config.yaml
kubectl apply -f infra/app/deployment.yaml
kubectl apply -f infra/app/service.yaml
kubectl apply -f infra/app/ingress.yaml
```

The manifests can also be applied together in dependency order:

```sh
kubectl apply -f infra/namespace.yaml
kubectl apply -f infra/storage/
kubectl apply -f infra/app/
```

Wait for both workloads:

```sh
kubectl rollout status deployment/mysql -n webapp-stack --timeout=180s
kubectl rollout status deployment/webapp-api -n webapp-stack --timeout=180s
```

## Verify

List all task resources:

```sh
kubectl get all -n webapp-stack
kubectl get ingress -n webapp-stack
kubectl get pv,pvc -n webapp-stack
```

Check pod status and readiness:

```sh
kubectl get pods -n webapp-stack -o wide
kubectl describe pod -n webapp-stack -l app=webapp-api
kubectl describe pod -n webapp-stack -l app=mysql
```

Both pods should report `Running` and `Ready`.

View application logs:

```sh
kubectl logs -n webapp-stack deployment/webapp-api
kubectl logs -n webapp-stack deployment/mysql
```

Port-forward the application Service for a local HTTP check:

```sh
kubectl port-forward -n webapp-stack service/webapp-api 8080:80
```

In another terminal:

```sh
curl http://localhost:8080/
curl http://localhost:8080/health
```

The `/health` request should succeed only after the application and MySQL can
communicate.

## Configuration and credentials

The [ConfigMap](./infra/app/config.yaml) contains the application title,
environment, MySQL host, port, and database name.

The [Secret](./infra/storage/sec.yaml) is a demonstration only. It contains
plaintext demo values for a root password, application user, and application
password. Do not use these values in production.

For MySQL connection variables to reach the application pod, the application
deployment must receive `MYSQL_USER` and `MYSQL_PASSWORD` (and, if needed,
`MYSQL_DATABASE`) from the Secret or another secret source. The current
manifests load the ConfigMap into the application and the Secret into MySQL;
they do not configure a complete application-to-MySQL credential chain.

## Troubleshooting

### ImagePullBackOff or ErrImagePull

Make the `webapp-api:task2` and `webapp-mysql:task2` images available to every
node that may schedule the pods. For local clusters such as kind or Minikube,
load or build the images in the cluster's Docker/Containerd environment.

### Pending MySQL pod

Confirm that the PV and PVC are bound:

```sh
kubectl get pv mysql-pv
kubectl get pvc mysql-pvc -n webapp-stack
```

The PV is host-local and requires `/data/webapp-mysql` to exist on the
scheduling node.

### Application is not ready

Check probe results and pod events:

```sh
kubectl describe deployment webapp-api -n webapp-stack
kubectl get pods -n webapp-stack -l app=webapp-api
kubectl logs -n webapp-stack -l app=webapp-api --tail=100
```

The application has both liveness and readiness probes at `/health`.

## Cleanup

Deleting the namespace removes namespaced resources, including Deployments,
Services, the Ingress, ConfigMap, Secret, and PVC:

```sh
kubectl delete namespace webapp-stack
```

The cluster-scoped PersistentVolume is retained by its
`persistentVolumeReclaimPolicy: Retain` setting. Remove it separately:

```sh
kubectl delete pv mysql-pv
```