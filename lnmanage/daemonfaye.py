from subprocess import Popen, PIPE, TimeoutExpired
from time import time,sleep
from rich import print as rPrint, inspect
from rich.console import Console
from rich.layout import Layout
from rich.text import Text as rText
from rich.table import Table as rTable
from rich.progress import Progress
from rich.rule import Rule
from rich.prompt import IntPrompt, Prompt, Confirm
from lnpixi import get_avg_fee
from fayeui import initUI
import threading, pickle, signal, random, json

timeouts=0 #number of timout exeptions occurred
vf=5 #verbosity filter. 0 instructs to stfu
partners=[] #list of ChanPartner objects
name_table={None:None} #to quick resolve names of nodes
color_table={None:None} #to quick resolve colors of nodes
known_nodes=[] #currently unused
graph=None # the lightning network graph. (gets updated on stratup)
mynode='' # own nodes public key (updates on startup)
minfee=20 # minmal fee, that is accepted from lnPixi
walletreserve=2500000 #reserve of wallet, that shall not spent while opening, in satoshis
pushamt=25 #amt of satoshis pushed to the other side, while opening channels

#ist es sinniger eine liste von dicts statt class(task) zu verwenden
class task():
    def __init__(self, tType, tData, callback):
       self.tType = tType #type of task
       self.tData = tData #contains dict with instructions and parameters for task (what is when, how to do? what are the conditions under which task shall get stopped or alike?)
       self.callback = callback #fuction to call and tell results of task
       self.status = 'waiting' #last know status of task
    def addevent(self,e={"type":"placeholder","time":time(),"data":"decay"}):
        self.events.append(e)
        return

#soll zyklische aufgaben uebernehmen. wie feywatchd, balancecheck usw.
class worker(threading.Thread):
    """So this is a docstring? thanks, kite!"""
    def __init__(self, threadID, name, task):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.task = task
        self.starttime = time()
    def run(self):
        outs,errs,t = rebal(self.task)
        self.task.callback(outs,errs,t)
        return()

def refresh_data():
    global vf
    if vf>2:rPrint('refreshing all data.\nstarting with channels,active_peers,closed_channel_peers')
    channels,errs,t = callExt()
    pass
    return()



def addChanPartner(pubkey, chanID, closingAddress, pType=["recovered"], chanSize=5000000,reopenUntill=99999999,lb=0,rb=0,iE=False):
    global partners,vf
    if pubkey not in [p['pubkey'] for p in partners]:
        partners.append({
            'alias':aliasTable(n=pubkey),
            'color':colorTable(n=pubkey),
            'pubkey':pubkey,
            'chanID':chanID,
            'channel_point':'',
            'hoststring':None, #host, where to connect to
            'fee':25,
            'fayefee':0,
            'upscore':0,
            'downscore':0,
            'flowscore':0,
            'flowamt':0,
            'openfee':0, #fee per vbyte on the opening transaction
            'hosts':[], #known hostnames and ports of this node
            'colors':[], #known past colors of this node
            'names':[], #known past names of this node
            'local_balance':lb,
            'remote_balance':rb,
            'notes':"This is a placeholder",
            'pType':pType, #type of channel aebal_winner, liquidity-swap, friend, random, sink, source, recommendtation, rented liquidity
            'chanSize':chanSize,
            'reopenUntill':reopenUntill, #reopen channel until blockheight of
            'openNext':False, #wether channel shall be reopened in next batch
            'closingAddress':closingAddress, #where funds shal go after  closing channel
            'isEstablished':iE}) #wether or not the channel is established
        if partners[-1]['alias'] not in partners[-1]['names']: partners[-1]['names'].append(partners[-1]['alias'])
        if partners[-1]['color'] not in partners[-1]['colors']: partners[-1]['colors'].append(partners[-1]['color'])




#wrapper function to Popen
#Trys to execute in docker container, if work['in_this_docker_container'] is supplied
#   needs to be the name of the container, so that docker ps | grep "namestring" returns the correct line
#returns result_of_command,Erros,runtime_in_seconds
def callExt(work):
    global timeouts,vf
    if not(work) or work == None:return(None,"no work supplied",0)
    pot = work['Popen_this']
    dc = work['in_this_docker_container']
    if 'timeout' in work.keys(): t = work['timeout']
    else: t=None
    #callback = work["callme"]
    s=time()
    if vf>2: rPrint(Rule("digging through docker container for stuff"))
    if dc == '' or dc == None:ma=Popen(pot, stdout=PIPE, stderr=PIPE) #fixmoneyfixworld
    else:
        if vf>2:rPrint('\tI try finding this container: ',dc)
        try:
            dockerP=Popen(['docker','ps'], stdout=PIPE, stderr=PIPE)
            outs,errs=dockerP.communicate()
        except Exception as e:
            if vf>0:rPrint('docker ps errored this:',e)
            return("error while getting proccesslist from docker.:"+str(e),errs.decode,time()-s)
        findID=outs.decode()
        epos=findID.find(dc)
        if epos<1: return(None,"error:could not find " + str(dc) + ' in docker ps',time()-s)
        grep=findID[epos-30:epos+30]
        dID=grep[grep.find('\n')+1:grep.find('  ')]
        if dID == "": return(None,"error: container id could not be extracted",time()-s)
        do_this = ["docker","exec",dID] + pot
        ma=Popen(do_this, stdout=PIPE, stderr=PIPE)
        if vf>2: rPrint("\tcontainer may be found. Try to invoke this: \t", do_this)

    try:
        if isinstance(t,int) and t > 0: outs,errs=ma.communicate(timeout=t)
        else: outs,errs=ma.communicate()
        #print("\n\nouts:\n",str(outs))
        #print("\n\nerrs:\n",str(errs))
    except TimeoutExpired:
        ma.kill()
        outs, errs = ma.communicate()
        if vf>0:rPrint("\n\nTIMEOUT!!!\nouts:\n",str(outs))
        outs=str(outs)+"timeout"
        if vf>0:rPrint("\n\nTIMEOUT!!!\nerrs:\n",str(errs))
        timeouts += 1
    return(outs.decode(),errs.decode(),time()-s)

#pimpled servant to load and dump data to harddrive
#direction shall be 'load' or 'dump'
#jar (to use) defaults to lnmDB.pickle
#returns -1 on error
def pickleKnecht(direction='load',jar='fayeDB.pickle'):
    global partners, name_table, known_nodes,vf,graph
    r=0
    if direction == 'load':
        if vf>2:rPrint('trying to unpickle some old data.')
        try:
            with open(jar,"rb") as f:
                lnmDB = pickle.load(f)
                partners = lnmDB['partners']
                if vf>2:rPrint("unpickled old Data.")
        except Exception as e:
            if vf>2:rPrint("No old Data found.\nerror:",e)
            r=-1
    elif direction == 'dump':
        if vf>2:rPrint('trying to pickle data towards: ',jar)
        try:
            with open(jar,"wb") as f:
                pickle.dump({'partners':partners},f)
                if vf>2:rPrint("pickled Data towards ",jar)
        except Exception as e:
            if vf>0:rPrint("Oh noes! I could not pickle Data to ",jar, '/nGot hit by Exception: ',e)
            r=-1
    else: r=-1
    return(r)

# collect open channels and add towards partnersdb
def chans():
    global partners,vf
    #get open channels
    o,r,t = callExt({'Popen_this':['lncli', 'listchannels'],'in_this_docker_container':'abs/lnd:v'})
    cs=json.loads(o)['channels']
    if vf>2: rPrint('found '+str(len(cs))+' open Channels')
    for c in cs:
        found = False
        #if vf>2:
        #    rPrint('search Partners for: ',c)
        #    sleep(2)
        for p in partners:
            if p['pubkey'] == c['remote_pubkey']:
                found = True
                if vf>5: rPrint("found ",c['remote_pubkey'],aliasTable(c['remote_pubkey']),' in partners. updating...')
                p['isEstablished']=True
                p['chanSize']=c['capacity']
                p['local_balance']=c['local_balance']
                p['remote_balance']=c['remote_balance']
                p['chanID']=c['chan_id']
                p['color']=colorTable(n=c['remote_pubkey'])
                p['pType'].append('open Channel')
        if found == False:
            if vf>5: rPrint('could not find ',c['remote_pubkey'],aliasTable(c['remote_pubkey']),' in partners. adding it.')
            addChanPartner(pubkey=c['remote_pubkey'],
                            chanID=c['chan_id'],
                            closingAddress=c['close_address'],
                            pType=["new open channel"],
                            chanSize=c['capacity'],
                            iE=True,
                            lb=c['local_balance'],
                            rb=c['remote_balance'])


#returns list of all pubkeys a channel exists with
def openChans():
    global vf
    opens=[]
    #get open channels
    o,r,t = callExt({'Popen_this':['lncli', 'listchannels'],'in_this_docker_container':'abs/lnd:v'})
    cs=json.loads(o)['channels']
    if vf>2: rPrint('found '+str(len(cs))+' open Channels')
    for c in cs:
        opens.append(['remote_pubkey'])
    return(opens)

#takes node=nodes_pub_key and update allocationtable u=False
def aliasTable(n=None,u=False):
    global name_table, graph
    if u:
        name_table.clear()
        for i in [{no['pub_key']:no['alias']} for no in graph['nodes'] if not(no['pub_key'] in name_table)]:
            name_table.update(i)
    if n != None:
      try:
        alias=name_table[n]
      except:
        alias="node could not be found with resolver"
      return(alias)
    return(None)

#takes node=nodes_pub_key and update allocationtable u=False
def colorTable(n=None,u=False):
    global color_table, graph
    if u:
        color_table.clear()
        for i in [{no['pub_key']:no['color']} for no in graph['nodes'] if not(no['pub_key'] in color_table)]:
            color_table.update(i)
    if n != None:
      try:
        color=color_table[n]
      except:
        color="#000000"
      return(color)
    return(None)



# shall reinitiate fee, based on lnpixi
# if partner pubkey is not supplied, it does for all partners
def rePixi(partner=None):
    if partner==None:
        global partners, graph, mynode, minfee
        if vf>2: rPrint("rePixi() got no partner supplied. It trys to update all partner fees.")
        #mynode=[s for s in name_table if name_table[s].find("ewitterw")>=0][0]
        suggestionCluster=[]
        new_fees=[]
        if vf>2: rPrint('calling lnPixi for ',len(partners),' Nodes')
        with Progress() as progress:
            pixiTask = progress.add_task("Fee-Faye thinking abouts fees...", total=len(partners))
            for p in partners:
                if vf>6: rPrint('calling lnPixi for node:',p['alias'])
                med,avg,cavg,myfee,chan=get_avg_fee(p['pubkey'],mynode,graph=graph)
                suggestionCluster.append([med,avg,cavg,chan])
                nf = int(max(med+cavg/2,minfee))
                new_fees.append([p['pubkey'],nf])
                p['fayefee']=nf
                progress.update(pixiTask, advance=1)
            #if vf>1: rPrint(new_fees)
    else:
        if vf>2: rPrint("rePixi() trys to update fees for partner:"+str(partner))
        med,avg,cavg,myfee,chan=get_avg_fee(partner,mynode,graph=graph)
        nf = int(max(med+cavg/2,minfee))
        if vf>1: rPrint(partner,nf)
        for p in partners:
            if p['pubkey'] == partner: p['fayefee'] = nf
    return(partner)



# initalises global vars
def refresh_globals():
    global graph, mynode
    if vf>2: rPrint('trying to get fresh graph...')
    o,r,t = callExt({'Popen_this':['lncli','describegraph'],'in_this_docker_container':'abs/lnd:v'})
    if vf>2: rPrint('this took:',t,'s\nupdating name and color resolution tables and own puplic key now.')
    graph=json.loads(o)
    aliasTable(n=None,u=True)#build new alias table
    colorTable(n=None,u=True)#build new color table
    o,r,t = callExt({'Popen_this':['lncli','getinfo'],'in_this_docker_container':'abs/lnd:v'})
    mynode=json.loads(o)['identity_pubkey']
    if vf>2: rPrint(f'This shall be your Nodes Name: [{colorTable(mynode)}]{aliasTable(mynode)}[/{colorTable(mynode)}] and Public Key: [{colorTable(mynode)}]{mynode}[/{colorTable(mynode)}]')



if __name__ == "__main__":
    if vf>2:
        #Console.rule("[bold red]lnmanage Startup")
        rPrint('yeay! all "compiled". Try getting network data...')
    refresh_globals()
    if vf>2: rPrint('Instructing servant to get some channel data')
    pickleKnecht(direction="load")
    if vf>2:
        rPrint(Rule("[bold red]Bootup somehow succesfull"))
        rPrint('Collecting open channels...')
    chans()
    initUI(partners, rePixi=rePixi)
    if vf>2:
        rPrint('Ende. Knecht!!! Lege er ein!')
    pickleKnecht(direction='dump')
    if vf>2:
        rPrint('Noch etwas spassdata zum schluss?')
        rPrint(Rule("[bold red]shutdown initiated"))
    #return None
