#!/bin/bash

set -e

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
   build-essential git  \
   python-virtualenv curl yui-compressor python-dev \
   libpq-dev libxml2-dev libxslt-dev libffi-dev \
   libjpeg-dev screen \
   libyaml-dev >/dev/null


grep -qG 'cd /vagrant' "$HOME/.bashrc" ||
   cat <<'EOF' >> "$HOME/.bashrc"

export PATH="$HOME/yournextmp/gems/bin:$PATH"
export GEM_HOME="$HOME/yournextmp/gems"
source ~/yournextmp/venv/bin/activate
cd /vagrant
EOF
source "$HOME/.bashrc"

cd /vagrant
yournextmp-popit/bin/pre-deploy
