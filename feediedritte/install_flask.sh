#!/bin/bash
echo $SHELL
echo $BASH_VERSION
venvname="venv"
pipd="./$venvname/bin"
progs=(flask flask-wtf flask-sqlalchemy rich)  
#create venv
python3 -m venv --without-pip $venvname

#get pip
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
$pipd/python3 get-pip.py
rm get-pip.py

#install modules
for p in "${progs[@]}"
do
	echo "$p"
	$pipd/pip install $p
done

source $venvname/bin/activate