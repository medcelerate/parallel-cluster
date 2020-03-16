#!/bin/bash

for num in {1..100}
do 
cmd="export STRESS_MINS=10 && python stress_test.py && echo ""$num"" finished. >> /efs/homes/waleed.osman/burn_outputs.txt"
sbatch -e /efs/homes/waleed.osman/burn.txt -o /efs/homes/waleed.osman/burn.txt --exclusive --wrap="$cmd"
done

