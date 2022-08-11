#!/bin/sh

PYTHON_PATH="/usr/local/bin/"

if ! command -v cargo &> /dev/null; then
  echo "cargo could not be found, please install rust"
  exit
fi
if ! command -v $PYTHON_PATH/python3 &> /dev/null; then
  echo "python3 could not be found"
  exit
fi
if ! $PYTHON_PATH/python3 -c 'import pkgutil; exit(0) if pkgutil.find_loader("music21") else exit(1)'; then
  echo "music21 could not be found, please install via pip"
  exit
fi

git clone https://github.com/po-gl/ConstrainedHiddenMarkovModel

cd ConstrainedHiddenMarkovModel
cargo build --release
cd ..

mkdir cache/
$PYTHON_PATH/python3 bach.py --generate_indices --generate_datasets bach_data
