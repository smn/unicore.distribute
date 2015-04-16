#!/bin/bash

set -e

pip="${VENV}/bin/pip"
cd $INSTALLDIR/$REPO
$pip install -e .
