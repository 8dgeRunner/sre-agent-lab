# Contabo kind Safety Baseline

The deployed cluster is `kind-coagent-demo` (Kubernetes v1.32.2). Chaos Mesh
2.8.4 is installed in `chaos-mesh` with the kind containerd socket:

```bash
helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh \
  --version 2.8.4 --namespace chaos-mesh --create-namespace \
  --set clusterScoped=true \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock \
  --set dashboard.create=false
```

Apply these manifests only to the dedicated lab cluster:

```bash
kubectl apply -f namespace.yaml
kubectl apply -f networkpolicy.yaml
kubectl apply -f observer-rbac.yaml
```

Chaos Mesh's controller is cluster scoped because the 2.8.4 namespace-scoped
installation did not reconcile PodChaos on this cluster. Only administrators may
create Chaos Mesh resources, and all approved experiment manifests must target
`chaos-lab`. Host-level chaos remains prohibited.

The smoke workload and PodChaos manifests are in `manifests/`. A successful test
must show `AllInjected=True`, a replacement workload Pod, successful deletion of
the PodChaos resource, and the Deployment returning to `ready=1/1`.
