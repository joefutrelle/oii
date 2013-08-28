import os

import re

import numpy as np

from oii.utils import remove_extension

OUTDIR='woah'

species_count = {}

paths = []
with open('paths.txt') as pdt:
    for path in pdt:
        paths += [path.rstrip()]

for path in paths:
    path = os.path.basename(path)
    try:
        extension = '.' + re.findall(r'\.([a-zA-Z][a-zA-Z0-9]*)$',path)[0]
        path = re.sub(r'\.[a-zA-Z][a-zA-Z0-9]*','',path)
    except IndexError:
        extension = ''
    species = path
    species = re.sub(r'[a-z]+','a',species)
    species = re.sub(r'[A-Z]+','A',species)
    species = re.sub(r'[a-zA-Z]{2,}','B',species)
    species = re.sub(r'[0-9]+','9',species)
    species += extension
    try:
        species_count[species] += 1
    except KeyError:
        species_count[species] = 1

s = np.sum(species_count.values())
for k in sorted(species_count, key=species_count.get, reverse=True):
    c = species_count[k]
    if c > s / 500.:
        print k, species_count[k]
                       
