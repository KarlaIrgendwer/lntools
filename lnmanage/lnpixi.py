#!/usr/bin/python

#may be used for getting an idea of current feerates for a node
#based on the fees, others have set
import json, os, time, threading, signal, argparse, sys, requests, rich

joblist=[]
exitFlag = False # needed for later implementation of ctrl+c-handler
vf=0 #verbosity filter
name_table={None:None}
graph={}

#worker class to generate html-file-output
#work shal be a list of nodes pubkey as string
class htmlGen(threading.Thread):
   def __init__(self, threadID, name, work, outdir):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.work = work
      self.outdir = outdir
   def run(self):
      workerWebBuilder(self.work,self.outdir)
      if vf > 0: print("\nWorker "+str(self.threadID)+" finished.")
      return()




#return list of all nodes with vissible channel to node
def get_chan_partners(node):
    global graph
    myedges1=[n for n in graph["edges"] if n['node1_pub']==node]
    myedges2=[n for n in graph["edges"] if n['node2_pub']==node]
    chanpartners=[cp['node2_pub'] for cp in myedges1]+[cp['node1_pub'] for cp in myedges2]
    return(chanpartners)

#resolves pubkey to Alias
#this may be rather slow
def resolve_alias(node):
    global graph
    return([n['alias'] for n in graph['nodes'] if n['pub_key']==node][0])

#faster version of resolve_alias
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
        alias="node could not be found"
      return(alias)
    return(None)


#retruns median, average, capped average, own fee and [chanid,chanpoint] from all incomming chans
#capper=[0,1] do not cap feelist
#capper=[0,0.75] cap feelist to use only first 75%of ordered feelist
#capper=[0.1,0.9] ignore first and last 10 percent od channels
def get_avg_fee(node,mynode,capper=[0,0.85],graph=graph):
    #global graph
    #pop nonetype feepolicies of edges
    #i may change this to make them zero-fee-policy
    #rich.inspect(graph)
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
    return(median,round(avg,1),round(avgc,1),myfee[0],cidp)

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

#build this htmlpage
def buildHtml(data,orginal='./fees.html',alias='asddsaedccde',pubkey="1234567890abcdef"):
    with open(orginal,"r") as org:
        t=org.read()
        z=t[0:t.find('[{"al')]+json.dumps(data)+";\nvar pubkey = '"+pubkey+"'"+";\nvar alias='"+alias+"';"+t[t.find('edccde";')+8:]
    return(z)


def buildFrontend(nodes=[{"alias":"asddsa","pub_key":"123abc","color":"#3399ff"}],orginal='./frontend.html',outfile='out/index.html'):
    if vf > 0:print("building frontend(" + str(len(nodes)) + " entrys) in: " + str(outfile))
    items=[]
    for n in nodes:
        items.append('<a href="'+n["pub_key"]+'/index.html" style="color: '+n['color']+'">'+n["alias"]+' - '+n["pub_key"]+'</a>')
    with open(orginal,"r") as f:
        t=f.read()
    i=t.find('<!-- hierrein -->')
    site=t[0:i]+"\n".join(items)+t[i:]
    if outfile != None:
        with open(outfile,"w") as f:
            f.write(site)
    return(site)

def workerWebBuilder(nodelist,outdir='out'):
    for n,node in enumerate(nodelist):
        alias=aliasTable(n=node)
        pr=False
        if vf > 1: print("Try generating feereport "+str(n)+" for: "+alias)
        if vf > 0: pr=True
        sc=fee_report(node,pr=pr)
        if sc != []:
            if vf > 1: print("Exporting feereport towards out/"+node+".html")
            site=buildHtml(sc,alias=alias,pubkey=node)
            newpath = outdir+'/'+node
            if not os.path.exists(newpath):
                os.makedirs(newpath)
            with open(newpath+"/index.html","w") as f:
                f.write(site)

#spawn workers, that build html
def startWorkers(joblist,outdir):
    global max_threads
    max_chunk=10
    id=0
    while len(joblist) > 0:
        while (threading.activeCount() < max_threads):
            amount=len(joblist)
            if amount > max_chunk: amount=max_chunk
            work=[joblist.pop() for _ in range(0,amount)]
            if not exitFlag:
                id+=1
                worker=htmlGen(id,"Builder_"+str(id),work,outdir)
                worker.start()
                if vf > 0: print("started worker:"+str(id))
        if len(joblist) <1:exit()

if __name__ == "__main__":
    ####parameter handling and logic on what to do
    p = argparse.ArgumentParser()
    paras=[["--node","The target nodes pubkey",""],
        ["--dgjson","path to describegraph.json default:./describegraph.json","./describegraph.json"],
        ["--nodesjson","path to jsonfile, containing list of target nodes",""],
        ["--nodeshttp","address of website containing list of target nodes",""],
        ["--outdir","folder in which html-structure will be created defaults to ./out","./out"],
        ["--doit","allow generating all. Defaults to False",False],
        ["--vf","verbosity filter. Defaults to 1 for say enough. (below 1 is silent)",1],
        ["--test","test mode Defaults to 0 for not testing.",0],
        ["--watch","watch dgjson for updates. Defaults to False, due to not yet implemented",False],
        ["--numthreads","number of threads to utilyze. defaults to 16",16]]
    for para in paras:
        p.add_argument(para[0], type=type(para[2]), default=para[2], help=para[1])

    args = p.parse_args()
    dgjson = args.dgjson
    centernode_key=args.node #cosy bane
    max_threads=args.numthreads
    outdir=args.outdir
    nodesjson=args.nodesjson
    nodeshttp=args.nodeshttp
    doit=args.doit
    vf=args.vf
    nodelist=None
    if os.path.isfile(nodesjson):
        with open(nodesjson,"r") as f:
            nodelist=json.load(f)
        if vf > 0: print("Loaded something, assumed to be a list of node pubkeys.")

    if not os.path.exists(outdir):os.makedirs(outdir)

    if os.path.isfile(dgjson):
        with open(dgjson,"r") as f:
            try:
                 graph=json.load(f)
            except Exception as e:
                if vf > 0: print("failed loading dgjson, exiting:\n",e)
                sys.exit(2)
            if vf > 0: print("dg.json was loaded. I spare geometry checks for now.")
    else:
        if vf > 0: print(dgjson + " not found. Looking in stdin:")
        si=sys.stdin
        if not si.isatty():
            l=(si.read())
        try:
            graph=json.loads(l)
        except:
            if vf > 0: print("failed loading dgjson from stdin")
            sys.exit(2)
        if vf > 0: print("loded something from stdin. I spare geometry checks for now. Lets assume, its a well formed describegraph.json.")

    if vf > 0: print("hey, we may have a graph variable")

    #put code in here to test it
    if args.test == 1:
        print("test stuff and exit")
        print(len(name_table))
        print(name_table)
        sys.exit()

    if vf > 0: print("Generating node name table")
    aliasTable(n=None,u=True)

    if len(centernode_key) > 10:
        if vf > 1: print("generating one set of pages for node:"+centernode_key+"\nin:"+outdir)
        nl=[{"color":n['color'],"alias":n['alias'],"pub_key":n['pub_key']} for n in graph['nodes'] if n["pub_key"]==centernode_key]
        buildFrontend(nodes=nl,outfile=outdir+"/index.html")
        joblist=[n["pub_key"] for n in nl]
        workerWebBuilder([centernode_key],outdir)
        sys.exit(0)

    if nodelist !=None:
        if vf > 0: print("Spawning Workers to generate "+str(len(nodelist))+" sets of websites.")
        nl=[]
        for node in nodelist:
            try:
                nl.append([{"color":n['color'],"alias":n['alias'],"pub_key":n['pub_key']} for n in graph['nodes'] if n["pub_key"]==node].pop())
            except Exception as e:
                print("could not add Node: ",node)
        buildFrontend(nodes=nl,outfile=outdir+"/index.html")
        joblist=[n["pub_key"] for n in nl]
        startWorkers(joblist,outdir)
        sys.exit(0)

    if vf > 0: print("no node nor nodelist found. Generating for all nodes, seen within 1 week.")
    nl=[{"color":n['color'],"alias":n['alias'],"pub_key":n['pub_key']} for n in graph['nodes'] if time.time()-n["last_update"]<604800]
    buildFrontend(nodes=nl,outfile=outdir+"/index.html")
    joblist=[n["pub_key"] for n in nl]
    if not doit:
        if vf > 0: print("not starting workers.")
        sys.exit(0)
    startWorkers(joblist,outdir)


#sieving joblist for nodes with more than nc channels
def sieving(nc=1,nl=[]):
    if nl == []: return(0)
    return([n for n in nl if len(get_chan_partners(n)) > nc])
