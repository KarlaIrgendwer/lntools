# lntools
Welcome to financial neuron managment engine. short for -fancy smart acronym- This is currently more a blueprint of some ideas and mainly focuses on lnd node management using docker interactions.

Functionalitys
  - aebal.py: Uses C-Ottos rebalance-lnd in an automated way on heavy imbalanced channels.
  - lndtoolbox: collection of functions, often used by this programms
  - feediedritte: collects transaction agnostic data about the performance (fillednesss and activity) and fee state of channels. And displays them using flask. Let it run a few days and adjust settings, to improve numbers. (higher flowscore and fillednessscore closer to zero)
  - txw.py: makeshift keysend reader
  - maintain.py: bulk-reopen channels with more then 10k updates
  - anfang.py: bulk-recover closed channels.
  - fun.py: graphs-colordata sumarized
  - lnpixi: generate websites about feedata of one to all node(s)

Screenshots:


Hints:
  - You can config your favourite terminal multiplexer, to automate startup.
  - "ssh -L 5050:127.0.0.1:5000 lnuser@192.168.1.69" may forward that flask-web-interface to you.
  - some programms currently pickle some data for later analysis and usage. It may be usefull to "mv eventlist.pickle  pickleshelf/$(date +%Y-%m-%d-%s).eventlist.pickle" or alike.
  - feediedritte is currently the only part of this software, featuring an installer
  - there are more hints in sourcecode comments
