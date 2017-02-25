#!/bin/bash

#Python 3.5
sudo apt-get install python3.5

#Pip 3.5
wget https://bootstrap.pypa.io/get-pip.py
python3.5 get-pip.py

#Python modules
pip3.5 install python-twitter
pip3.5 install -U discord.py
pip3.5 install praw

#Rasa NLU
git clone https://github.com/golastmile/rasa_nlu.git
python3.5 setup.py install

pip3.5 install git+https://github.com/mit-nlp/MITIE.git

