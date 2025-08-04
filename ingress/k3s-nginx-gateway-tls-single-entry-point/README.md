[main index](../../README.md) | [ingress index](../README.md)

# K3s with Nginx Gateway Fabric with TLS termination via Lets-Encrypt Using a Single Point of Entry

> [!IMPORTANT]
> This is a variation on the [original k3s gateway recipe](../k3s-nginx-gateway-tls/README.md) which still serves as a base for installing the cluster and other elements.

The differences from the previous recipe is listed below:

* The `Gateway` is now deployed in the `nginx-gateway` namespace and serves as the single entry point for the cluster.
* Namespaces containing user deployments get an added label to whitelist them for `Gateway` eligibility when `HTTPRoute` resources are deployed.
* The `cert-manager` is now configured to issue a wild-card certificate for a single domain. The `HTTPRoute` resources will include more specific domain based routing.
* Also, `cert-manager` is updated to obtain signed certificates from Lets Encrypt production end-point, meaning that our web browsers will now trust the issued certificates.
* Manifests has been updated

The original recipe was a good introduction, but I include this one as it feels perhaps a little more practical and more closely aligned to what would serve even more people's needs.

The updated design is shown below, and the updated commands below that.

TODO - Add updated design

## Preparation

### Initial Steps

Follow the sections in the [original recipe](../k3s-nginx-gateway-tls/README.md) under the following section headings:

* Preparations
* Uninstall Previous Version
* Install a Fresh Cluster

### Install the Nginx Gateway Fabric

Run the following commands:

```bash
# The following is the Helm values for our Nginx Gateway Fabric deployment
cat <<EOF > /tmp/values.yaml
nginx:
  service:
    type: NodePort
    nodePorts:
    - port: 30080
      listenerPort: 80
    - port: 30443
      listenerPort: 443
EOF

# Deploy the Nginx Gateway Fabric:
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric --create-namespace -n nginx-gateway -f /tmp/values.yaml
```

The final effect will be to have a single gateway listening on well known pre-defined `NodePort` TCP ports: 30080 and 30443 respectively.

### Installing `cert-manager`

```bash
rm -vf /tmp/*.yaml

cp -vf ingress/k3s-nginx-gateway-tls-single-entry-point/manifests/* /tmp/

# Edit the manifests copied in /tmp to suite your needs.
# THEN:

# Enable the namesapce "kuard" running the example application to host
# HTTPRoute resources that will add routes to the Gateway
kubectl label namespace kuard shared-gateway-access="true" --overwrite

# Install cert-manager
helm install \
  cert-manager oci://quay.io/jetstack/charts/cert-manager \
  --version v1.18.2 \
  --namespace cert-manager \
  --create-namespace \
  --set crds.enabled=true

# Create a secret with the AWS IAM credentials required for updating Route 53
# (lets-encrypt feature for verifying you own the domain)
kubectl apply -f /tmp/01_aws_route53_creds.yaml -n cert-manager

# Deploy the Cluster Issuer 
kubectl apply -f /tmp/02_cluster_issuer.yaml -n cert-manager

# This next step is no longer required....
# Deploy policy to allow other namespaces access to the required Secrets
# kubectl apply -f /tmp/03_cert_read_grant.yaml -n cert-manager
```

## Provisioning the Initial Gateway

And the rest is pretty mush the same as previously:

```bash
# Create a certificate
# More info at https://cert-manager.io/docs/usage/certificate/
kubectl apply -f /tmp/04_certificate.yaml -n nginx-gateway

# This may take a couple of minutes - wait until the `READY` field shows `True`
kubectl get certificates -n nginx-gateway
# Example of when the certificate is ready:
# NAME                            READY   SECRET                         AGE
# test1-example-tld-certificate   True    test1-example-tld-tls-secret   3m

# Once the certificate is ready, deploy the Gateway:
kubectl apply -f /tmp/05_gateway.yaml -n nginx-gateway

# And finally, add routes to the Gateway to link up with hte application
kubectl apply -f /tmp/06_routes.yaml -n kuard
```

## Testing

Once again, the correct `NodePort` for both HTTP and HTTPS needs to be obtained:

```bash
kubectl get services -n nginx-gateway
# Expected Output (example only)
# -----------------------------------------------------------------------------
# NAME                       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                      AGE
# gateway-nginx              NodePort    10.43.32.213    <none>        80:30080/TCP,443:30443/TCP   75m
# ngf-nginx-gateway-fabric   ClusterIP   10.43.115.108   <none>        443/TCP                      96m

# set your application domain:
export APP_DOMAIN="kuard.${DOMAIN}"

# Test the HTTP port
curl -vvv http://${APP_DOMAIN}:30080/

# Test the HTTPS port
# (ignore the certificate check because we are using a staging certificate)
curl -vvv https://${APP_DOMAIN}:30443/
```

In addition, you could now use a tool like `socat` to permanently listen on the host on port 80 and 443 and forward that to port 30080 and 30443 respectively. In this way, tou would not have to specific the ports. An example is shown below:

```bash
# Run this on the K3s HOST:

cat <<EOF > ~/web-forward-into-k3s.sh
#!/usr/bin/env bash

nohup socat tcp-listen:80,fork tcp:192.168.2.13:30080 &
nohup socat tcp-listen:443,fork tcp:192.168.2.13:30443 &
EOF

chmod 700 ~/web-forward-into-k3s.sh
sudo ~/web-forward-into-k3s.sh

# Back on your personal system
# Test the HTTP port
curl -vvv http://${APP_DOMAIN}/

# Test the HTTPS port
# (ignore the certificate check because we are using a staging certificate)
curl -vvv https://${APP_DOMAIN}/
```

## References

* [`k3s` Documentation](https://docs.k3s.io/)
* [Nginx Gateway Fabric Documentation](https://docs.nginx.com/nginx-gateway-fabric/)
* [`cert-manager` Documentation](https://cert-manager.io/docs/)
* [Gateway API Specification Documentation](https://gateway-api.sigs.k8s.io/)

<hr />

[main index](../../README.md) | [ingress index](../README.md)
