# Task 1: Kubernetes Web Application

## Target and description

Deploy a small web application to Kubernetes and verify its pod lifecycle,
container logs, processes, and HTTP response.

The [deployment.yaml](./deployment.yaml) manifest creates:

- The `webapp` namespace.
- A `web-deployment` Deployment with three replicas.
- An `nginx` container serving HTTP on port 80.
- An `init-done` init container that runs `echo done` and exits successfully.
- A restartable `time-updater` sidecar, declared under `initContainers`, that
  waits for NGINX and updates its index page with the current time every five
  seconds. The pod shares its process namespace so the helper can find NGINX.

The sidecar uses `SYS_PTRACE` and writes into the NGINX container's filesystem
through `/proc`. This is a learning example, not a recommended production
security pattern.

## Requirements

- A Kubernetes cluster and a working `kubectl` context.
- A cluster version/configuration that supports restartable init containers
  (native sidecars).
- Network access from the cluster to pull `nginx:1.27` and `busybox:1.36`.
- `curl` for the optional local HTTP check.

Check cluster access and version:

```sh
kubectl cluster-info
kubectl version
```

## Deploy

Run these commands from the `task-1` directory, or adjust the manifest path:

```sh
kubectl apply -f deployment.yaml
kubectl rollout status deployment/web-deployment -n webapp
```

## Verification

### Confirm the namespace, deployment, and pods

```sh
kubectl get namespace webapp
kubectl get deployment web-deployment -n webapp
kubectl get pods -n webapp -l app=web -o wide
```

The deployment should report three desired, updated, and available replicas.
Pods should eventually reach `Running` and `Ready`.

### Inspect the containers and events

```sh
kubectl get pods -n webapp -l app=web \
  -o jsonpath='{.items[0].spec.initContainers[*].name}{"\n"}{.items[0].spec.containers[*].name}{"\n"}'
kubectl describe pods -n webapp -l app=web
```

The init-container names should include `init-done` and `time-updater`; the
application container is `nginx`. The `time-updater` remains running as a
restartable init-container sidecar while the pod is running.

### Read container logs

Pod names change when Kubernetes replaces a pod. Select a current pod rather
than copying a name from an earlier run:

```sh
POD=$(kubectl get pods -n webapp -l app=web \
  -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n webapp "$POD" -c init-done
kubectl logs -n webapp "$POD" -c time-updater --tail=20
```

The `init-done` logs should contain `done`. The `time-updater` logs should
contain its startup and update messages.

### Inspect processes and the generated page

```sh
kubectl exec -n webapp deploy/web-deployment -c time-updater -- ps
kubectl exec -n webapp deploy/web-deployment -c nginx -- \
  cat /usr/share/nginx/html/index.html
```

Because the pod shares its process namespace, `ps` in the helper container can
show processes from NGINX too. The page should include the
`Hello in MLOPS MENA COMMUNITY` text and a timestamp.

### Verify the HTTP response

In one terminal, start port forwarding:

```sh
kubectl port-forward -n webapp deployment/web-deployment 8080:80
```

In another terminal:

```sh
curl http://localhost:8080/
```

Refresh or repeat the request after five seconds to see the timestamp change.
Stop port forwarding with `Ctrl-C` when finished.

## Troubleshooting command syntax

- Use `-n webapp` to specify the namespace; `-webapp` is not a valid namespace
  option.
- `kubectl logs` takes a pod or supported workload resource, followed by
  `-c <container-name>` when selecting a container. Do not include an extra
  `pod` or `pods` word before the pod name.
- `kubectl describe` needs a resource type, for example
  `kubectl describe pod -n webapp "$POD"`.
- For commands executed in a container, place `--` before the command, for
  example `kubectl exec -n webapp "$POD" -c time-updater -- ps`.
- Use `kubectl get pods -n webapp` to list pods; do not assume an old pod name
  is still present.

## Cleanup

The manifest creates the namespace and all resources in it. Delete the
namespace to remove this task's resources:

```sh
kubectl delete namespace webapp
```