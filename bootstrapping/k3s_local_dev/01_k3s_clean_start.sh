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
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 could not be found"
    exit 1
  fi
}

function uninstall_k3s() {
  check_command "helm"
  check_command "curl"
  /usr/local/bin/k3s-uninstall.sh || true
  echo "[INFO] K3s uninstalled"
}

function install_k3s() {
  helm repo update
  curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server" sh -s - --disable=traefik --kubelet-arg="node-ip=0.0.0.0"
  sudo cp -vf /etc/rancher/k3s/k3s.yaml ./k3s.yaml
  sudo chown $USER:$USER ~/k3s.yaml
  echo "[INFO] K3s installed"
}

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
else
  echo "Ok - not doing anything!"
fi
