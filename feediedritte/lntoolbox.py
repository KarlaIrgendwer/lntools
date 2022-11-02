#!/usr/bin/python


import json, os, time, threading, signal, argparse, sys
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
import threading, pickle, signal, random, json

joblist = []
exitFlag = False # needed for later implementation of ctrl+c-handler
vf = 5 #verbosity filter
name_table = {None:None}
color_table = {None:None}
graph = None
fillLevels = {'data':None,'time':time()}

#wrapper function to Popen
#Trys to execute in docker container, if work['in_this_docker_container'] is supplied
#   needs to be the name of the container, so that docker ps | grep "namestring" returns the correct line
#returns result_of_command,Erros,runtime_in_seconds
#this shall be replaced by some legit grpc or smth
def callExt(work):
    global timeouts,vf
    if not(work) or work == None:return(None,"no work supplied",0)
    pot = work['Popen_this']
    dc = work['in_this_docker_container']
    if 'timeout' in work.keys(): t = work['timeout']
    else: t=None
    #callback = work["callme"]
    s=time()
    if vf<=2: rPrint(Rule("digging through docker container for stuff"))
    if dc == '' or dc == None:ma=Popen(pot, stdout=PIPE, stderr=PIPE) #fixmoneyfixworld
    else:
        if vf<=2:rPrint('\tI try finding this container: ',dc)
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
        if vf<=2: rPrint("\tcontainer may be found. Try to invoke this: \t", do_this)

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


# initalises global vars
def refresh_globals():
    global graph, mynode
    if vf <= 2: rPrint('trying to get fresh graph...')
    o,r,t = callExt({'Popen_this':['lncli','describegraph'],'in_this_docker_container':'abs/lnd:v','timeout':120})
    if vf <= 2: rPrint(f'len(Output): {len(o)}\nError: {r}\n','this took:',t,'s\nupdating name and color resolution tables and own puplic key now.')
    if o == '' or o == None:return(-1)
    graph=json.loads(o)
    aliasTable(n=None,u=True)#build new alias table
    colorTable(n=None,u=True)#build new color table
    o,r,t = callExt({'Popen_this':['lncli','getinfo'],'in_this_docker_container':'abs/lnd:v'})
    mynode=json.loads(o)['identity_pubkey']
    if vf<=2: rPrint(f'This shall be your Nodes Name: [{colorTable(mynode)}]{aliasTable(mynode)}[/{colorTable(mynode)}] and Public Key: [{colorTable(mynode)}]{mynode}[/{colorTable(mynode)}]')
    return(mynode)




#return list of all nodes with vissible channel to node
def get_chan_partners(node):
    global graph
    myedges1=[n for n in graph["edges"] if n['node1_pub']==node]
    myedges2=[n for n in graph["edges"] if n['node2_pub']==node]
    chanpartners=[{ 'pubkey':cp['node2_pub'],
                    'chanid':cp['channel_id'],
                    'size':cp['capacity'],
                    'basefee':cp['node1_policy']['fee_base_msat'],
                    'feerate':cp['node1_policy']['fee_rate_milli_msat']} for cp in myedges1] + [{'pubkey':cp['node1_pub'],
                    'chanid':cp['channel_id'],
                    'size':cp['capacity'],
                    'basefee':cp['node2_policy']['fee_base_msat'],
                    'feerate':cp['node2_policy']['fee_rate_milli_msat']} for cp in myedges2]
    return(chanpartners)

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

# return filldnes of channel
def get_filledness(chanid):
    global vf, fillLevels
    if time()-fillLevels['time'] < 60 and fillLevels['data'] != None: chans=fillLevels['data']
    else: 
        if vf == -1: rPrint('Refreshing filledness table')
        o,r,t = callExt({'Popen_this':['lncli','listchannels'],'in_this_docker_container':'abs/lnd:v'})
        if o == '':return(.0)
        if vf == -1: rPrint('output is not Null')
        chans=json.loads(o)
        fillLevels = {'data':chans,'time':time()}
        if vf == -1: rPrint('this took:',t)
    for c in chans['channels']:
        if c['chan_id'] == chanid:
            return(int(c['local_balance'])/int(c['capacity']))
    return(.0)


#returns median, average, capped average, own fee and [chanid,chanpoint] from all incomming chans
#capper=[0,1] do not cap feelist
#capper=[0,0.75] cap feelist to use only first 75%of ordered feelist
#capper=[0.1,0.9] ignore first and last 10 percent od channels
def get_avg_fee(node,mynode,capper=[0,0.85]):
    global graph
    #pop nonetype feepolicies of edges
    #i should change this to make them zero-fee-policy
    edges1=[n for n in graph["edges"] if n['node1_pub']==node and n['node2_policy']!=None ]
    edges2=[n for n in graph["edges"] if n['node2_pub']==node and n['node1_policy']!=None ]
    others_fee1=[int(o["node2_policy"]['fee_rate_milli_msat']) for o in edges1]
    others_fee2=[int(o["node1_policy"]['fee_rate_milli_msat']) for o in edges2]
    of=others_fee1+others_fee2
    if len(of)<2:return(0,0,0,0,["none","none"])
    of.sort()
    median=of[int(len(of)/2)]
    avg=sum(of)/len(of)
    shortenfees=of[int(len(of)*capper[0]):int(len(of)*capper[1])]
    avgc=sum(shortenfees)/len(shortenfees)
    myfee=[int(e["node1_policy"]['fee_rate_milli_msat']) for e in edges1 + edges2 if e['node1_pub'] == mynode]
    myfee=myfee+[int(e["node2_policy"]['fee_rate_milli_msat']) for e in edges1 + edges2 if e['node2_pub'] == mynode]+[0]
    #chanid/point
    try:
        cidp=[ [e['channel_id'], e['chan_point']] for e in edges1 + edges2 if e['node2_pub'] == mynode or e['node1_pub'] == mynode ][0]
    except: cidp=["none","none"]
    return({'median':median,'round':round(avg,1),'roundCapped':round(avgc,1),'myfee':myfee[0],'cidp':cidp})

def get_fees_of_node(node):
    global graph
    channelsFees=[]
    myedges1=[n for n in graph["edges"] if n['node1_pub']==node]
    myedges2=[n for n in graph["edges"] if n['node2_pub']==node]
    for cp in myedges1:
        channelsFees.append({"alias":aliasTable(n=cp['node2_pub']),'infee':cp['node1_policy'], 'outfee':cp['node2_policy']})
    for cp in myedges2:
        channelsFees.append({"alias":aliasTable(n=cp['node1_pub']),'infee':cp['node2_policy'], 'outfee':cp['node1_policy']})
    pass
    return(channelsFees)

#outputs fee suggestions for node
#pr stands for print
def fee_report(node,pr=False):
    if pr:print("\n------------------------------------------------------------------------------------\n\t\tAnalazing fees for: "+aliasTable(n=node)+"\n"+node+"\n\nCurrent\tMedian\tCapped_avg\tAlias")
    partners=get_chan_partners(node)
    suggestionCluster=[]
    for p in partners:
        med,avg,avgc,sett,cidp = get_avg_fee(p,node)
        #what does this chanpoint mean?
        if cidp[1] != "0000000000000000000000000000000000000000000000000000000000000000:0":
            suggestionCluster.append({'alias':aliasTable(n=p),'pubkey':p,'median':med,'avg':avg,'cappedAvg':avgc,'curFee':sett,'chanID':cidp[0],'chanPoint':cidp[1]})
        if pr:print("\t".join([str(sett),str(med),str(avg),"\t"+aliasTable(n=p)]))
    pass
    return(suggestionCluster)

#first version output
def runoldway():
    #print current  fee settings
    print("\n------------------------------------------------------------------------------------\n\t\tPrinting fee status for: "+aliasTable(n=centernode_key)+"\n\nOutgoing\tAlias of counterparty\t\tOutgoing")
    for cf in get_fees_of_node(centernode_key):
        print(cf['infee']['fee_rate_milli_msat'], "\t", cf['alias'], "\t\t", cf['outfee']['fee_rate_milli_msat'])

    #print suggenstioncluster
    fee_report(centernode_key,pr=True)


#sieving joblist for nodes with more than nc channels
def sieving(nc=1,nl=[]):
    if nl == []: return(0)
    return([n for n in nl if len(get_chan_partners(n)) > nc])
