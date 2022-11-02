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
from ui import initUI
from fun import printData
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



def addChanPartner(pubkey, chanID, closingAddress, pType=["recovered"], chanSize=5000000,reopenUntill=99999999,lb=0,rb=0,iE=False,num_updates=0,cp=''):
    global partners,vf
    if pubkey not in [p['pubkey'] for p in partners]:
        partners.append({
            'alias':aliasTable(n=pubkey),
            'color':colorTable(n=pubkey),
            'pubkey':pubkey,
            'chanID':chanID,
            'num_updates':num_updates,
            'channel_point':cp,
            'hoststring':None, #host, where to connect to
            'fee':25,
            'fayefee':0,
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
def pickleKnecht(direction='load',jar='lnmDB.pickle'):
    global partners, name_table, known_nodes,vf,graph
    r=0
    if direction == 'load':
        if vf>2:rPrint('trying to unpickle some old data.')
        try:
            with open(jar,"rb") as f:
                lnmDB = pickle.load(f)
                partners = lnmDB['partners']
                #name_table = lnmDB['name_table']
                #known_nodes = lnmDB['known_nodes']
                if vf>2:rPrint("unpickled old Data.")
        except Exception as e:
            if vf>2:rPrint("No old Data found.\nSince I was instructed to load stuff, I will try to create a dataset by recovering from closed and open channels.\nerror:",e)
            r=-1
            #hier sollte noch ein tryblock ringsrum
            #o,r,t = callExt({'Popen_this':['lncli','describegraph'],'in_this_docker_container':'abs/lnd:v'})
            #graph=json.loads(o)
            #aliasTable(n=None,u=True)#build new alias table
            o,e,t=callExt({'Popen_this':['lncli','closedchannels'],'in_this_docker_container':'abs/lnd:v'})
            cc=json.loads(o)['channels']
            recover(cc)
            pass #createnametable()
    elif direction == 'dump':
        if vf>2:rPrint('trying to pickle data towards: ',jar)
        try:
            with open(jar,"wb") as f:
                pickle.dump({'partners':partners,'name_table':name_table,'known_nodes':known_nodes},f)
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
                p['channel_point']=c['channel_point']
                p['local_balance']=c['local_balance']
                p['remote_balance']=c['remote_balance']
                p['num_updates']=c['num_updates']
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
                            rb=c['remote_balance'],
                            cp=c['channel_point'])
    pass

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


#add all nodes from previously closed channels cc
def recover(cc):
    global vf, known_nodes, partners
    for c in cc:
        addChanPartner(pubkey=c['remote_pubkey'], chanID=c['chan_id'], closingAddress='unkown', pType=["recovered","closed"], chanSize=c['capacity'],cp=c['channel_point'])
        #dict_keys(['channel_point', , 'chain_hash', 'closing_tx_hash', 'remote_pubkey', 'capacity', 'close_height', 'settled_balance', 'time_locked_balance', 'close_type', 'open_initiator','close_initiator', 'resolutions'])


# collects data for reopening channels
# future: looks in partners-db, if all channels meet theire requierements
# future: looks in closed channels for potential reopens
# shall, one day, take feywatchd and flowanalysis into account
def collectReopen():
    global partners, vf
    roc = [r for r in partners if int(r['num_updates']) > 10000]
    roc = sorted(roc, key=lambda item: item['num_updates'])
    roc.reverse()
    if vf>2:
        rPrint(f'found {len(roc)} Channels with > 10k updates. thoose are top 16:')
        for p in roc[:16]:
            rPrint(f'Channel with {p["alias"]} has {p["num_updates"]} Updates.')
    return(roc)


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

# shall apply current config from partners to client(lnd)
def apply(client="lnd"):
    pass

# crawls the graph for a connection towards a pubkey
# updates and returns that partner, if succesfull
def updateConnectionParms(partner):
    global graph
    node = [n for n in graph['nodes'] if n['pub_key'] == partner['pubkey']]
    if len(node) == 0:
        return(None)
    node = node[0]
    # check if connection info is given in graph
    if len(node['addresses']) < 1:
        if vf>2: rPrint('could not find any connection info on ' + partner['alias'] + ' within the graph.')
        return(None)
    # update hoststrings
    if partner['hoststring'] == None or partner['hoststring'] == '':
        partner['hoststring'] = node['addresses'][0]['addr']
    else:
        for n in range(len(node['addresses'])):
            if node['addresses'][n]['addr'] not in partner['hosts']: partner['hosts'].append(node['addresses'][n]['addr'])
    return(partner)

#returns true if partner is connected
def checkCon(partner):
    o,r,t = callExt({'Popen_this':['lncli','listpeers'],'in_this_docker_container':'abs/lnd:v'})
    connectedPeers=json.loads(o)
    if partner['pubkey'] in [c['pub_key'] for c in connectedPeers['peers']]:
        #there is allready a connection to this peer
        if vf>1: rPrint(partner['alias'],'is connected. Returning...')
        return(True)
    else:
        return(False)

def connectPeer(partner):
    updateConnectionParms(partner)
    pk=partner['pubkey']
    hosts=[partner['hoststring']]+partner['hosts']
    for hs in hosts:
        if not checkCon(partner) and hs != None:
            o,r,t = callExt({'Popen_this':['lncli','connect', pk+'@'+hs],'in_this_docker_container':'abs/lnd:v'})
            if vf>1:
                rPrint(f'tryed to connect to {partner["alias"]}.\nOutput:{o}\nError:{r}\nthis took:{t}s')



# try to (re)connect all partners in passed partners list, if nescessary
# returns list of successfully connected partner
def connectPartners(partners):
    successfulls = []
    if vf>1: rPrint(Rule(f'Try connecting {len(partners)} peers'))
    #add check here to filter out allready connected peers
    for partner in partners:
        if vf>1: rPrint(Rule('Connecting Peer '+str(partner['alias'])))
        connectPeer(partner)
        if checkCon(partner): successfulls.append(partner)
    return(successfulls)

#returns the up to date confirmed balance in stoshis in lnds wallet
def getBalance():
    o,r,t = callExt({'Popen_this':['lncli','walletbalance'],'in_this_docker_container':'abs/lnd:v'})
    balance=int(json.loads(o)['confirmed_balance'])
    return(balance)

# shall instruct lnd to forge a channel opening transaction including all partners
# and theire parameters
def openCh(partners, fee=1):
    global walletreserve, pushamt
    openchans=openChans()
    for p in partners:
        if p['pubkey'] in openchans:
            partners.remove(p)
            if vf>1: rPrint(f'Partner {aliasTable(p["pubkey"])} already shares a channel. Dropped it from list.')
    opening_data = connectPartners(partners)
    if len(opening_data) > 0:
        cList=[]
        for partner in opening_data:
            rPrint(f"I could open towards {partner['alias']} with channelsize of {partner['chanSize']}.")
            cList.append({"node_pubkey":partner['pubkey'], "local_funding_amount":int(partner['chanSize']), 'push_sat':int(pushamt)})
        correct = Confirm.ask(f'Shall I proceed?')
        if correct:
            openingsum = sum([int(p['chanSize']) for p in opening_data])
            if getBalance()-openingsum-walletreserve < 1:
                rPrint(f'nodes balance of {getBalance()}sat is not sufficiant for funding {openingsum}sat Channels and keeping {walletreserve}sat resevre.')
                return(None)
            else:
                rPrint(f'*beepboobbeeb*... doing stuff.... *brrrrrr* certainly not making up to do smth... opening {openingsum}sat Channels ...')
                rPrint(cList)
                while not Confirm.ask(f'Go ahead?'):pass
                o,r,t = callExt({'Popen_this':['lncli','batchopenchannel', '--sat_per_vbyte=1', json.dumps(cList)], 'in_this_docker_container':'abs/lnd:v'})
                rPrint(f'Out: {o}\nError: {r}\nTime: {t} seconds')
                while not Confirm.ask(f'Weiter?'):pass

        else:
            return(None)
    else:
        rPrint('There where zero successful connects. Aborting')


#shall close all channels to all portners from supplied partnerdb
#shall return list of successfully closed channels/partners for reopening them
#shall also return a list of all talkitalki from lnd
def closeChans(partners):
    opencandidate = []
    talki = []
    #disable all channels, wait until all htlcs cleared and then close.... 
    for p in partners:
        if True:    #test if channel with partner existent
            pass #remove help, to activate
            o,r,t = callExt({'Popen_this':['lncli','closechannel', f'--chan_point={p["channel_point"]}', '--sat_per_vbyte=1'], 'in_this_docker_container':'abs/lnd:v'})
            talki.append({'out':o, 'error':r, 'time':t})
            if r == '': opencandidate.append(p)
            else: rPrint(f'Error while closing towards {p["alias"]}\nOut: {o}\nError: {r}\nTime: {t} seconds')
            #lncli closechannel  --chan_point value xyz:0  --conf_target 100 --sat_per_vbyte 1
    return(opencandidate,talki)






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


#pimpled servant to load and dump data to harddrive
#if stuff == none: load from jar and return stuff
#jar (to use) defaults to igor.pickle
#returns None on error
def pickleIgor(stuff,jar='igor.pickle'):
    global vf
    r=0
    if stuff == None:
        if vf>2:rPrint('trying to unpickle some old data.')
        try:
            with open(jar,"rb") as f:
                stuff = pickle.load(f)
                if vf>2:rPrint("unpickled old Data.")
        except Exception as e:
            if vf>2:rPrint("No old Data found.\nPlease accept this hand full of nothing as imbursement for my incompetance and this error, that got thrown with shattering power to my face.\nerror:",e)
            return(None)
    else:
        if vf>2:rPrint('trying to pickle data towards: ',jar)
        try:
            with open(jar,"wb") as f:
                pickle.dump(stuff,f)
                if vf>2:rPrint("pickled Data towards ",jar)
        except Exception as e:
            if vf>0:rPrint("Oh noes, master! I could not pickle Data to ",jar, '/nGot hit by Exception: ',e)
            return(None)
    return(stuff)


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
    if vf>2: rPrint('looking for qued openings')
    reopen=pickleIgor(None, jar='reopens.pickle')
    if reopen != None:
        openCh(reopen)
    #inspect(partners[10], help=True)
    if vf>2: rPrint(f'Found {len(partners)} Channels. Looking for Reopening candidates.')
    roc = collectReopen()
    correct = Confirm.ask(f'You want to que those channels to be reopened?\nWarning! This currently overwrites prevousliy qued reopens.')
    if correct:
        if vf>2: rPrint('closing top 8 Channels')
        opencandidate,lnderror=closeChans(roc[:16])
        r=pickleIgor(opencandidate, jar='reopens.pickle')


    while not Confirm.ask(f'May i clear screen and continue?'): pass
    #reconsider fees
    #rePixi()
    #start keylistener

    initUI(partners, opener=openCh, graph=graph)
    if vf>2:
        rPrint('Ende. Knecht!!! Lege er ein!')
    pickleKnecht(direction='dump')
    if vf>2:
        rPrint('Etwas spassdata zum schluss noch:')
        printData(graph)
        rPrint(Rule("[bold red]shutdown initiated"))
    #return None

