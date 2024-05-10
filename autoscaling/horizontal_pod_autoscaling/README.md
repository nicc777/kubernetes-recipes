[main index](../../README.md) | back to: [autoscaling topic index](../README.md)

> [!WARNING]
> Work in Progress... This section is still in development and may see various changes from the current state of the content

<!--
TODO - Add metrics monitoring...
-->

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
