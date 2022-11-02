Todo:
  - readme.md
  - name/abstrakt/beschreibung (Welcome to financial neuron managment engine. short for -fancy smart acronym- currently this is more a blueprint of some ideas and mainly focuses on lnd node management)
  - structur and consistency
  - refactor from docker to grpc (or add option for grpc)
  - connect also to c-lightning
  - tidy stuff up
  - integrate macaroons
  - get screenshotkey working again and make screenshots of software in action
  - plebs einbeziehen/veroeffentlichen (rc1alpha)
  - expand fun-data-output to html,json,pickle (*lacht* ich lege regenboegen ein. xD)
  - opener inteligenter/interaktiver machen. (failOnMinchansize 'adjust Size to minchansize(y/n)?')



maintained sqllite/pickle datenbank mit partnernodes, deren rollen (liquidity-swap (zeitliche vereinbarungen u.ae.), friend, randomfind, sink, source, recommendtation, gemietete liquiditaet, gut funktionierende fees, ...) und parameter, kanaldaten, tasks, ...

steuert spaeter auch aebal, feywatchd und co.

lauft als deamon mit webinterface (jinja/flask oder stupid templates) oder rich interface in der console

soll als zentrum das peer und channel -management haben?

erste tasks:
  - test lnd-connect
  - create partnernodes data strukture
  - (un)pickle this data
  - batch(re)open my channels
  - retrieve data about all nodes, that once where channel partnernodes
  - list them and give options to task a try to reconnect, opening of a new channel, add to banlist
  - create datastructure for future/regular tasks (what, when, recallfunction,...), save done tasks with outcome
  - create regular tasks to
    - check node health (try using rebalance -c and such) and issue reboots and stuff
    - restart datacollection of feywatchd



gedanken machen:
  - interface-frage (im moment richConsoleText)
    - pygame zum keylistening?
    - sciplot outputs im html-teil?
  - wann veroeffentlichen? werbung? nicht doch lieber r2r zocken?
  - feesuggestor [nur,wo,wie,] einbinden?
  - bcdm.sh dazu packen?
  - wie schaffen
    - anzufangen
    - dabei zu bleiben == lass dich doch nicht ablenken, wie z.b. gerade von lingustigkram...
    - sinnig zu wirken (mein wirken als handlung, nicht "den anschein erwecken".)
    - nicht im detail zu verlieren oder details zu uebersehen
    - probleme zu umschiffen
  - soll ein screen erzeugt werden, um outputs wie von aebal anzuzeigen? wenn, dann direkt vom startscript aus?



next:
  - get channelstate (open,closed,...) to partnersdb
  - write back from ui modded partnersdb
  - mit partnersdb abgleichen
  - turn keyboardecho back on

  - rich-ui
  - in einzelne unterprogramme aufteilen. (eins fuer feemanagement, reopening, ...)
  - screen-startscript, welches einzelne unterprogramme laed erstellen
  - channel editing/impose partnersdb on live lnd



Plebnettext:

Hello there, dear plebs.

I tryed myself on managing an ln-node. During this time I generated a bit of code. Some of those tools i wrote have proofen usefull to me. They are all in a more like concept style, instead of alpha. I know, that this all is pretty messy. And that there are better ways certain task should/may be done. But I lack the ressources, to refactor/implement/finish everything to a nice and more secure release in a timely appropriate manner. So I decided, to publish this code in its current state. I hope it proofs usefull to someone, before it becomes obsolete.

This currently gets its data from asking docker to execute lncli-commands. So this currently only works for lnd within a docker container, if user has the right to interact with docker.




Functionalitys
  aebal.py: Uses C-Ottos rebalance-lnd in an automated way on heavy imbalanced channels.
  lndtoolbox: collection of functions, often used by this programms
  feediedritte: collects transaction agnostic data about the performance (fillednesss and activity) and fee state of channels. And displays them using flask. Let it run a few days and adjust settings, to improve numbers. (higher flowscore and fillednessscore closer to zero)
  txw.py: keysend reader
  maintain.py: bulk-reopen channels with more then 10k updates
  anfang.py: bulk-recover closed channels.
  fun.py: graphs-colordata sumarized
  lnpixi: generate websites about feedata of one to all node(s)

Screenshots:


Hints:
  - You can config your favourite terminal multiplexer, to automate startup.
  - "ssh -L 5050:127.0.0.1:5000 lnuser@192.168.1.69" may forward that flask-web-interface to you.
  - some programms currently pickle some data for later analysis and usage. It may be usefull to "mv eventlist.pickle  pickleshelf/$(date +%Y-%m-%d-%s).eventlist.pickle" or alike.
  - feediedritte is currently the only part of this software, featuring an installer
  - there are more hints in sourcecode comments

gebrauchte befehle:
NAME:
   lncli batchopenchannel - Open multiple channels to existing peers in a single transaction.

USAGE:
   lncli batchopenchannel [command options] channels-json

CATEGORY:
   Channels

DESCRIPTION:

  Attempt to open one or more new channels to an existing peer with the
  given node-keys.

  Example:
  lncli batchopenchannel --sat_per_vbyte=5 '[{
    "node_pubkey": "02abcdef...",
    "local_funding_amount": 500000,
    "private": true,
    "close_address": "bc1qxxx..."
  }, {
    "node_pubkey": "03fedcba...",
    "local_funding_amount": 200000,
    "remote_csv_delay": 288
  }]'
  --conf_target value    (optional) the number of blocks that the transaction *should* confirm in, will be used for fee estimation (default: 0)
  --sat_per_vbyte value  (optional) a manual fee expressed in sat/vByte that should be used when crafting the transaction (default: 0)
  --min_confs value      (optional) the minimum number of confirmations each one of your outputs used for the funding transaction must satisfy (default: 1)
  --label value          (optional) a label to attach to the batch transaction when storing it to the local wallet after publishing it

describegraph       Describe the network graph.
getnodemetrics      Get node metrics.
getchaninfo         Get the state of a channel.
listchannels        List all open channels.
closedchannels      List all closed channels.
newaddress          Generates a new address.
walletbalance       Compute and display the wallet's current balance.
tower               Interact with the watchtower.
wtclient            Interact with the watchtower client.



