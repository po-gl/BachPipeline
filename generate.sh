#!/bin/sh

PYTHON_PATH="/usr/local/bin/"
sequence_count=6
 
cd ConstrainedHiddenMarkovModel
cargo run --release -- --config ../chmm_config.yaml -n "$sequence_count" --out ../output/sequences.txt 
cd ..

echo "==="

OUTPUT_PATH="output/bach_pieces_$(date "+%d_%H-%M-%S")"
mkdir $OUTPUT_PATH

cp chmm_config.yaml "$OUTPUT_PATH/chmm_config_$(date "+%d_%H-%M-%S").yaml"

count=1
IFS=$'\n'
for line in `cat output/sequences.txt`; do
  mkdir $OUTPUT_PATH/piece_$count
  $PYTHON_PATH/python3 bach.py $OUTPUT_PATH/piece_$count/bach_$count "$line"
  ((count++))
done
