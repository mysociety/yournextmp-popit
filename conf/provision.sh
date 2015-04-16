#!/bin/bash

set -e

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
   build-essential git  \
   python-virtualenv curl yui-compressor python-dev \
   libpq-dev libxml2-dev libxslt-dev libffi-dev \
   libjpeg-dev screen \
   libyaml-dev >/dev/null

grep -qG 'cd /vagrant' "$HOME/.bashrc" || echo '' >> "$HOME/.bashrc" && echo 'export PATH="/home/vagrant/yournextmp/gems/bin:$PATH"' >> "$HOME/.bashrc" && echo 'export GEM_HOME="/home/vagrant/yournextmp/gems"' >> "$HOME/.bashrc" && echo 'source ~/yournextmp/venv/bin/activate' >> "$HOME/.bashrc" && echo "cd /vagrant" >> "$HOME/.bashrc" && echo "source $HOME/.bashrc"

cd /vagrant
yournextmp-popit/bin/pre-deploy
