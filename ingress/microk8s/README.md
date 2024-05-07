[main index](../README.md)

# `microk8s` Ingress Setup

> [!TIP]
> Before running the command below, you need to select an IP address range on your LAN that the LoadBalancer can use.
>
> For a very simple personal LAN environments, like those used only with the Internet providers WiFi modem, consult the providers documentation on how the DHCP is configured on the modem. Typically not the entire available network is used and there are some IP addresses available for users to use as static IP addresses. These are the IP addresses of interest. Make sure you select a range, or individual IP addresses making up a total of around 10x IP Addresses.
>
> You will need the IP addresses you selected above to enter after you run the command below.

Enable MetalLB:

```shell
microk8s enable metallb
```

Create the ingress service:

```shell
kubectl apply -f ingress/microk8s/ingress-service.yaml
```

Afterwards, run the command `kubectl get all -n ingress` and you should see something like the following:

```text
NAME                                          READY   STATUS    RESTARTS      AGE
pod/nginx-ingress-microk8s-controller-5ktrd   1/1     Running   2 (26h ago)   2d1h

NAME              TYPE           CLUSTER-IP       EXTERNAL-IP     PORT(S)                      AGE
service/ingress   LoadBalancer   10.152.183.195   192.168.2.201   80:30865/TCP,443:32516/TCP   43s

NAME                                               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR   AGE
daemonset.apps/nginx-ingress-microk8s-controller   1         1         1       1            1           <none>          2d1h
```

Note the value of the `EXTERNAL-IP`. Your actual value may differ depending on your local LAN setup and the IP addresses you selected for `metallb`.

<hr />

[main index](../README.md)