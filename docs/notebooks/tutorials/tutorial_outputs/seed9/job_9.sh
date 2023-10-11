#!/bin/bash
#SBATCH -J 9
#SBATCH -o tutorial_outputs/seed9/out.9
#SBATCH -e tutorial_outputs/seed9/err.9
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH -t 0-01:00:00
#SBATCH --mem-per-cpu=5000
source /n/fs/ragr-data/users/uchitra/miniconda3/bin/activate base
conda activate gaston-package
gaston -i data/cerebellum/cerebellum_coords_mat.npy -o data/cerebellum/F_glmpca_penalty_10_rep1.npy --epochs 10000 -d tutorial_outputs --hidden_spatial 20 20 --hidden_expression 20 20 --optimizer adam --seed 9 -c 500
