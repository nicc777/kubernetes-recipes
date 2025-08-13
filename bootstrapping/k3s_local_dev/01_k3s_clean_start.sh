#!/usr/bin/env bash

ask() {
  while true; do
    read -p "$1 [Y/n/a] " answer
    case $(echo "$answer" | tr "[A-Z]" "[a-z]") in
    y | yes | "")
      echo "true"
      return 0
      ;;
    n | no)
      echo "false"
      return 1
      ;;
    a | abort)
      echo "abort"
      exit 1
      ;;
    esac
  done
}

function check_command() {
  # if ! command -v "$1" >/dev/null 2>&1; then
  #   echo "$1 could not be found"
  #   exit 1
  # fi

  if type "$1" >/dev/null 2>&1; then
    echo "Command '$1' found..."
  else
    echo "The command '$1' does not exist. Cannot continue!"
    exit 1
  fi

}

function uninstall_k3s() {
  check_command "kubectl"
  check_command "ssh"
  ssh $SERVER /usr/local/bin/k3s-uninstall.sh
  echo "[INFO] K3s uninstalled"
}

function install_k3s() {
  cat <<EOF >/tmp/k3s_install.sh
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server" sh -s - --disable=traefik --kubelet-arg="node-ip=0.0.0.0"
sudo cp -vf /etc/rancher/k3s/k3s.yaml /tmp/k3s.yaml
sudo chown $USER:$USER /tmp/k3s.yaml
EOF

  scp /tmp/k3s_install.sh $SERVER:/tmp/

  ssh $SERVER "chmod 700 /tmp/k3s_install.sh && sudo /tmp/k3s_install.sh"
  echo "[INFO] K3s installed"
}

function get_kubernetes_config() {
  scp $SERVER:/tmp/k3s.yaml ~/
  sed -i "s/127.0.0.1/${SERVER}/g" $HOME/k3s.yaml
}

function validate_phase_1() {
  kubectl get namespaces >/dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "✅ Successfully connected to the Kubernetes cluster."
  else
    echo "❌ Error: Could not connect to the Kubernetes cluster."
    echo "Please check your kubectl configuration and network connectivity."
    exit 1
  fi
}

function port_forward_message() {
  echo
  echo "----------------------------------------"
  echo
  echo "You can now add a port-forwarding session in order to open the Tekton Web UI:"
  echo
  echo "        kubectl port-forward service/tekton-dashboard --address 0.0.0.0 -n tekton-pipelines 9097:9097"
  echo
  echo "----------------------------------------"
  echo
}

function deploy_tekton() {
  kubectl apply -f https://storage.googleapis.com/tekton-releases/operator/latest/release.yaml
  sleep 60
  kubectl apply --filename https://storage.googleapis.com/tekton-releases/pipeline/latest/release.yaml
  sleep 60
  kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/latest/release.yaml
  sleep 60
  kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/latest/interceptors.yaml
  sleep 60
  kubectl apply --filename https://storage.googleapis.com/tekton-releases/dashboard/latest/release-full.yaml
  sleep 10
}

function run_provisioning_pipeline() {

  echo
  echo "----------------------------------------"
  echo
  echo "Applying Primary Provisioning Pipeline..."
  echo
  echo "        NOTE: This could take 15 to 20 minutes."
  echo
  echo "        You can monitor the progress in Tekton."
  echo
  echo "----------------------------------------"
  echo
  kubectl apply -f bootstrapping/tekton/tasks/k3s_local_development/02_provision_k3s_local.yaml
}

function prep_for_main_deployment() {
  cat <<EOF >/tmp/task_env
SERVER=$SERVER
LE_R53_KEY=$LE_R53_KEY
LE_R53_SECRET=$LE_R53_SECRET
ROUTE_53_ZONEID=$ROUTE_53_ZONEID
ROUTE_53_DOMAIN=$ROUTE_53_DOMAIN
ROUTE_53_RESOURCE_ID=$ROUTE_53_RESOURCE_ID
KUBECONFIG=$KUBECONFIG
NFS_SERVER=$NFS_SERVER
NFS_PATH=$NFS_PATH
EMAIL=$EMAIL
ROUTES=$ROUTES
EOF
  kubectl apply -f bootstrapping/tekton/tasks/k3s_local_development/01_bootstrapping_rbac.yaml
  kubectl create secret generic env-secret --from-env-file=/tmp/task_env -n bootstrapping
}

REQUIRED_VARS=("SERVER" "LE_R53_KEY" "LE_R53_SECRET" "ROUTE_53_ZONEID" "ROUTE_53_DOMAIN" "ROUTE_53_RESOURCE_ID" "KUBECONFIG" "NFS_SERVER" "NFS_PATH" "EMAIL" "ROUTES")

# Loop through each variable name in the list
for var in "${REQUIRED_VARS[@]}"; do
  # Check if the variable is set and not empty
  if [ -z "${!var}" ]; then
    echo "Error: Required environment variable '$var' is not set." >&2
    exit 1
  fi
done

echo
echo "!!! WARNING !!!"
echo
echo "Data loss may occur !!"
echo
answer=$(ask "This script will UNINSTALL the previos version of K3s. Continue?")
echo "Your answer was: ${answer}"
echo

if "$answer"; then
  uninstall_k3s
  install_k3s
  get_kubernetes_config
  validate_phase_1
  deploy_tekton
  port_forward_message
  prep_for_main_deployment
  run_provisioning_pipeline
else
  echo "Ok - not doing anything!"
fi
