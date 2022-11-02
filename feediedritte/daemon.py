#läuft im hintergrund und aktualisiert periodisch kanäle und deren bewertungen.
from lntoolbox import aliasTable,colorTable,get_chan_partners,refresh_globals,get_filledness,get_avg_fee
from time import sleep

vf = 5 
pleaseDie = False #allow daemon to end
chanslist = []  #periodically recreated list of all chan.data()
pixilist = []   #list of chans to repixi
editlist = []   #list of different actionos to perform on channel (maybe merge with pixilist)
daemonrunning = False
mynode = ''

#evtl. war es eine bescheuerte idee, das als klasse zu betrachten...
class channel():
    def __init__(self, chanID, alias, pubkey, color, size, feerate, basefee):
      self.alias = alias
      self.chanID = chanID
      self.color = color
      self.size = size
      self.pubkey = pubkey
      self.fillscore = 0
      self.flowscore = 0
      self.downscore = 0
      self.upscore = 0
      self.tickintervall = 10
      self.nextTickIn = 1
      self.feerate = feerate
      self.basefee = basefee
      self.filledness = [x for x in range(-10,0)] #ten most recent filledstates
      self.pixi = None
      self.ticks = 0
      
    def __repr__(self):
        return(str(self.data()))

    def data(self):
        r={
      'alias': self.alias,
      'chanID': self.chanID,
      'pubkey': self.pubkey,
      'color': self.color,
      'fillscore': int(self.fillscore),
      'flowscore': round(self.flowscore,2),
      'upscore': int(self.upscore),
      'downscore': int(self.downscore),
      'feerate': self.feerate,
      'basefee': self.basefee,
      'tickintervall': self.tickintervall,
      'filledness': self.filledness,
      'size': self.size,
      'ticks': self.ticks,
      'pixi': self.pixi}
        return(r)
    
    def repixi(self):
        pass
        #get a suggestion
        self.pixi=get_avg_fee(mynode=mynode,node=self.pubkey)
        return(self.pixi)

    def getfee(self):
      pass
      return

    def tickscore(self,fillednes):
        global vf
        self.ticks += 1
        scoremod=0
        if fillednes in  self.filledness: self.flowscore = self.flowscore*0.99995
        else: 
            if vf <= 2: print(f"Filldness differs in  Chan {self.alias}.\n\tOlds:{self.filledness}\n\tNew:{fillednes}")
            self.flowscore += 25
            self.filledness.pop(0)
            self.filledness.append(fillednes)
        if fillednes > 0.3 and fillednes < 0.7: self.fillscore = self.fillscore*0.95
        if fillednes > 0.95: scoremod -= 3
        if fillednes < 0.05: scoremod += 3
        if fillednes * self.size > self.size - 100000: scoremod -= 7
        if fillednes * self.size < 100000: scoremod += 7
        self.fillscore += scoremod
        return(self.fillscore)


    def inc_score(self):
       self.upscore += 25
       return(self.upscore)

    def dec_score(self):
       self.downscore += 25
       return(self.downscore)

    def decay_score(self):
       for s in [self.upscore,self.downscore]:
           if s < 10: s = 0
           else: s -= 10
       return(self.upscore,self.downscore)

    def doTasks(self):
        global editlist
        task = next((e for e in editlist if e['chanID'] == self.chanID), None)
        if task != None:
            editlist.remove(task)
            if task['what'] == 'fee':self.basefee=data
            if task['what'] == 'interval':self.tickintervall=data
            if task['what'] == 'pixi':self.repixi()
            if task['what'] == 'clear':
                self.fillscore = 0
                self.flowscore = 0
                self.downscore = 0
                self.upscore = 0
        return





def getChans(node):
    chans = []
    cs = get_chan_partners(node)
    for c in cs:
        chans.append(
            channel(chanID=c['chanid'],
                alias=aliasTable(c['pubkey']),
                pubkey=c['pubkey'],
                color=colorTable(c['pubkey']),
                size=int(c['size']),
                feerate=int(c['feerate']),
                basefee=int(c['basefee'])))
    return(chans)

def evalChans(chans,tickdelay=1):
    global pleaseDie, vf, chanslist, pixilist, daemonrunning,editlist
    if daemonrunning == True: return("already at work")
    while pleaseDie == False:
        daemonrunning = True
        #update global accessible chans. Workaround until implemented better. :-)
        chanslist = [c.data() for c in chans]
        for c in chans:
            c.nextTickIn -= 1
            if c.nextTickIn < 1 and pleaseDie == False:
                c.doTasks()
                if c.chanID in pixilist:
                    pixilist.remove(c.chanID)
                    c.repixi()
                if vf < 2: print(c)
                c.tickscore(get_filledness(c.chanID))
                c.nextTickIn = c.tickintervall
        sleep(tickdelay)
    daemonrunning = False
    return(chans)

def start(callback=lambda x:x):  
    global mynode
    if vf < 2: print("Starting feewatcher daemon...\nAnd/Or refreshing globals")
    mynode = refresh_globals()
    if daemonrunning == False:
        if vf < 2: print("get chans")
        chans = getChans(mynode)
        for c in chans: c.repixi()
        if vf < 2: print("eval chans")
        chans = evalChans(chans)
    return()

def stop(hard=False):
    global pleaseDie
    pleaseDie = True
    if vf < 2: print("Asked daemon to die. It will try to in one to #channels tickdelays.")

def handOutChans():
    global chanslist
    return(chanslist)

def addPixi(chanid):
    global chanslist,pixilist
    ret='failure'
    if chanid in [c['chanID'] for c in chanslist]: 
        pixilist.append(chanid)
        ret=('success')
    return(ret)

def setter(data=None, what='interval', chanID=None):
    global editlist
    if what in ['fee', 'interval', 'pixi','basefee','feerate','clear']:
        if data != None:data=int(data)
        editlist.append({'chanID':chanID,'what':what,'data':data})
    return(None)





def isRunning():
    return(daemonrunning)