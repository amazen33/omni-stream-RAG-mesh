#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update -qq
sudo apt-get install -y python3-venv openssh-client curl
python3 -m venv /home/ubuntu/ansible-venv
/home/ubuntu/ansible-venv/bin/pip install --no-cache-dir ansible-core==2.20.1
install -d -m 700 /home/ubuntu/.ssh
if [ ! -f /home/ubuntu/.ssh/rag_cluster ]; then
  ssh-keygen -t ed25519 -N '' -C rag-ansible-controller -f /home/ubuntu/.ssh/rag_cluster
fi
chmod 600 /home/ubuntu/.ssh/rag_cluster
install -d -m 755 /home/ubuntu/rag-mesh/ansible
