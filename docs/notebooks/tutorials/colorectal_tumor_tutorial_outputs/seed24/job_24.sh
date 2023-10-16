#!/bin/bash
#SBATCH -J 24
#SBATCH -o colorectal_tumor_tutorial_outputs/seed24/out.24
#SBATCH -e colorectal_tumor_tutorial_outputs/seed24/err.24
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH -t 0-01:00:00
#SBATCH --mem-per-cpu=5000
source /n/fs/ragr-data/users/uchitra/miniconda3/bin/activate base
conda activate gaston-package
gaston -i colorectal_tumor_data/coords_from_paper.npy -o colorectal_tumor_data/glmpca_from_paper.npy --epochs 10000 -d colorectal_tumor_tutorial_outputs --hidden_spatial 20 20 --hidden_expression 20 20 --optimizer adam --seed 24 -c 500
