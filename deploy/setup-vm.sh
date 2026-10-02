#!/bin/sh
# One-time preparation of a fresh Ubuntu server for docker-compose.lite.yml (run with sudo).
# A 1 GB machine builds and runs the API comfortably only with swap.
set -eu

if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  sysctl -w vm.swappiness=20
  echo 'vm.swappiness=20' > /etc/sysctl.d/99-swappiness.conf
fi

if ! command -v docker >/dev/null; then
  apt-get update
  apt-get install -y ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# Only SSH and the web are reachable; repeated SSH guesses get banned; security updates
# install themselves. (Docker publishes 80/443 on its own; Postgres and Redis stay private.)
apt-get install -y ufw fail2ban unattended-upgrades
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
cat > /etc/fail2ban/jail.d/sshd.local <<'JAIL'
[sshd]
enabled = true
maxretry = 5
bantime = 1h
JAIL
systemctl enable --now fail2ban
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl reload ssh || systemctl reload sshd
dpkg-reconfigure -f noninteractive unattended-upgrades

# Logs must not fill the disk.
cat > /etc/docker/daemon.json <<'JSON'
{ "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "3" } }
JSON
systemctl restart docker
usermod -aG docker "${SUDO_USER:-$USER}"
echo "Ready. Log out and back in, then: docker compose -f docker-compose.lite.yml --env-file deploy/.env.lite up -d --build"
