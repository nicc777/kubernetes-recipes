# K3s with Nginx Gateway Fabric with TLS termination via Lets-Encrypt

This recipe was developed and tested early August 2025.

> [!IMPORTANT]
> The intent of this recipe is to get going quickly in a local development environment. For `lets-encrypt`, a staging certificate is used, which means the TLS certificate will not be trusted by a web browser.
>
> The recipe assumes DNS is maintained in AWS Route 53 - adjust the DNS related configuration (including registrar credentials) to suite your needs.

Basic features covered in this recipe:

* Uninstall a previous deployment
* Install a fresh cluster
* Install the Nginx Gateway Fabric
* Install `cert-manager`
* Configure TLS via `cert-manager` and `lets-encrypt` via AWS Route 53 DNS
* Test Web Server with TLS Gateway and normal unencrypted service (demo application)

![design](./design.png)

> [!IMPORTANT]
> This example does not make use of a Load Balancer. Instead, a `NodePort` is used and therefore every gateway will listen on it's own port.

## Preparations

### AWS Preparations

For this example, a public hosted zone on AWS must exist. Note down the `ZONE ID`.

In this domain zone, create an `A` record `test1` with the private IP address of your test server, for example `192.168.0.10`.

> [!NOTE]
> You can use any other name besides `test1`, but remember to then also update the manifests files accordingly!

Also create an IAM user with an inline policy attached. The content of the policy is in the file [`route53_policy.json`](./route53_policy.json)

You will need the credentials for the IAM user to update a `Secret` shown later.

### Local System Preparations

Consider using the `kubectl` [power tools](https://github.com/ahmetb/kubectx) for quick context and namespace switching.

Install Helm on the system(s) you wish  to use to interact with the cluster. To check what is currently installed on the cluster, you can then always run the following command:

```bash
helm repo update

# If you have an existing cluster, you can always check all the installed
# packages with the following command:
helm list --all-namespaces
```

Also remove any prior manifests and copy the current template manifests:

```bash
rm -vf /tmp/*.yaml

cp -vf ingress/k3s-nginx-gateway-tls/manifests/* /tmp/
```

Edit the files in `/tmp` to update the fields as indicated in the files.

## Uninstall Previous Version

Only required if you have a current `k3s` cluster. Ideally this experiment should be done on a fresh cluster.

Also refer to the [k3s documentation](https://docs.k3s.io/installation/uninstall) for the most up to date information.

Command:

```bash
/usr/local/bin/k3s-uninstall.sh
```

## Install a Fresh Cluster

> [!NOTE]
> First ensure the previous cluster is uninstalled - see previous section

Commands:

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server" sh -s - --disable=traefik --kubelet-arg="node-ip=0.0.0.0"

sudo cp -vf /etc/rancher/k3s/k3s.yaml ./k3s.yaml

sudo chown $USER:$USER ~/k3s.yaml
```

On any other system you need the `KUBECONFIG`, run:

```bash
export SERVER=...

scp $SERVER:~/k3s.yaml ~/
```

> [!NOTE]
> Once the `k3s.yaml` is copied, you need to update the IP address of the server in the file

Next, create a testing namespace and install a demo app to test the overall setup:

```bash
kubectl create namespace kuard

kubectl apply -f https://raw.githubusercontent.com/cert-manager/website/master/content/docs/tutorials/acme/example/deployment.yaml -n kuard
# expected output: deployment.extensions "kuard" created

kubectl apply -f https://raw.githubusercontent.com/cert-manager/website/master/content/docs/tutorials/acme/example/service.yaml -n kuard
# expected output: service "kuard" created
```

## Install the Nginx Gateway Fabric

Run the following commands:

```bash
kubectl kustomize "https://github.com/nginx/nginx-gateway-fabric/config/crd/gateway-api/standard?ref=v1.6.2" | kubectl apply -f -

helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric --create-namespace -n nginx-gateway --set nginx.service.type=NodePort
```

For basic testing, run the following commands:

```bash
# Set the domain 
export DOMAIN=...

cat <<EOF > /tmp/gateway.yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: gateway
spec:
  gatewayClassName: nginx
  listeners:
  - name: http
    port: 80
    protocol: HTTP
    hostname: "*.${DOMAIN}"
EOF

kubectl apply -f /tmp/gateway.yaml -n kuard

# Create the Route:
cat <<EOF > /tmp/routes.yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: kuard
spec:
  parentRefs:
  - name: gateway
    sectionName: http
  hostnames:
  - "test1.${DOMAIN}"
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: kuard
      port: 80
EOF

kubectl apply -f /tmp/routes.yaml -n kuard
```

In AWS Route 53, create a record `test1` that points to `192.168.2.13` (IP address of `sharky`).

Test connectivity by first getting the `NodePort`:

```bash
kubectl get services -n kuard
NAME            TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
gateway-nginx   NodePort    10.43.76.175   <none>        80:32223/TCP   5m22s
kuard           ClusterIP   10.43.76.19    <none>        80/TCP         19m
```

In the example output above, the port is 32223. You can then run the following:

```bash
open http://test1.toetzen.nl:32223/
```

The web page should open in a web browser.

> [!IMPORTANT]
> If the web page is not oening, you will need to troubleshoot this problem first before you can continue.

Post Test Cleanup:

```bash
kubectl delete -f /tmp/routes.yaml -n kuard

kubectl delete -f /tmp/gateway.yaml -n kuard
```
