[main index](../../README.md) | back to: [autoscaling topic index](../README.md)

> [!WARNING]
> Work in Progress... This section is still in development and may see various changes from the current state of the content

<!--
TODO - Add metrics monitoring...
-->

# Preparation - Monitor Current Performance

You will need two separate terminal windows for monitoring. Something like [tmux](https://github.com/tmux/tmux/wiki) could help with this by [splitting the window](https://tmuxcheatsheet.com/).

> [!TIP]
> For the experiment, I find it best to have a 3-window spit. First split horisontally with `CTRL+B "`. Then move to the top window and split again vertically with `CTRL+B %`. I use the top two windows for monitoring or watching stuff and the bottom window for entering commands.

In one window, run the following command to get a live view of the nginx ingress:

```shell
# Delete the old Ingress pod in order to get fresh logs
kubectl delete pod $(kubectl get pod -n ingress --output jsonpath='{.items[0].metadata.name}') -n ingress

# Monitor the logs
kubectl logs -f $(kubectl get pod -n ingress --output jsonpath='{.items[0].metadata.name}') -n ingress | ngxtop
```

> [!TIP]
> Wait a couple of minutes for the monitor to settle down. Alternatively delete the ingress Pod to force a fresh new one with empty logs before running the command above.

In the other window, run the following command to monitor the Pod performance: 

```shell
watch kubectl top pod -l name=fastapi-test -n example003
```

> [!NOTE]
> Alternatives to monitor cluster and application performance include:
> 
> * Kubernetes Dashboard, included with [microk8s](https://microk8s.io/docs/addon-dashboard) or [installed separately](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/)
> * Another command line tool, [k9s](https://k9scli.io/)
> * Dedicated monitoring application, for example [kube-prometheus](https://github.com/prometheus-operator/kube-prometheus), which uses Grafana, Prometheus and friends 

# Basic Benchmark

Apply example 3 and start the load test:

```shell
# Deploy the example with no autoscaling
kubectl apply -f autoscaling/horizontal_pod_autoscaling/deployment-no-autoscaling.yaml

# Get the ingress IP
export INGRESS=`kubectl get service ingress -n ingress -o yaml | yq ".status.loadBalancer.ingress[0].ip"`

# Start the load test
locust -f autoscaling/horizontal_pod_autoscaling/loadtest.py -H http://$INGRESS
```

In a separate terminal you can open your web browser:

```shell
# Get the ingress IP
xdg-open http://127.0.0.1:8089
```

In many cases using just 1 user should be enough to force a failure. You can increase the user count if this does not happen.

How will you know there are failures:

* In the locust UI you can observe the error rate
* In a terminal you can verify by doing `curl` requests and monitoring Pod restarts

```shell
# Curl request - working:
$ curl http://$INGRESS/example003  
{"message":"ok"}%

# Failure (at some point)
$ curl http://$INGRESS/example003 
<html>
<head><title>503 Service Temporarily Unavailable</title></head>
<body>
<center><h1>503 Service Temporarily Unavailable</h1></center>
<hr><center>nginx</center>
</body>
</html>

$ kubectl get pods -n example003
NAME                            READY   STATUS    RESTARTS      AGE
fastapi-test-85ff8d5cf5-262k7   1/1     Running   7 (75s ago)   33m
```

## Add a CPU based autoscaler

TODO - Complete section

# References

* [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)

<hr />

[main index](../../README.md) | back to: [autoscaling topic index](../README.md)
