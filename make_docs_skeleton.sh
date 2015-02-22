#!/bin/sh

rm How_models_fail.bbl
rm How_models_fail.blg
rm How_models_fail.aux

latex How_models_fail.tex
bibtex How_models_fail
pdflatex How_models_fail.tex
pdflatex How_models_fail.tex

./latex2html.py -p "http://www.eckhartarnold.de/papers/2015_How_Models_Fail/How_models_fail.pdf" -l "en" -r 'von <a href="http://www.eckhartarnold.de">Eckhart Arnold</a>' -k "Evolution of Cooperation, Social Simulations, History of Simulations, Science and Technology Studies" -d "A discussion of the failures of formal models in the social sciences and of the rationalizations for these failures" How_models_fail.tex

