#!/bin/sh

#SBATCH --mem=16G
#SBATCH --time=3200
#SBATCH --gres=gpu:1
#SBATCH --output=/home/s2063518/full-synth.log

source /home/${USER}/.bashrc
source activate fs2

python synthesize.py \
    --model-fs=Talromur-full \
    --model-g2p=ipd_clean_slt2018.mdl \
    --step=220000 \
    --mix_voices=True \
    --mix_method=subtract \
    -sids 1 5
