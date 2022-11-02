import pickle, random, math
from time import sleep
from rich import print as rPrint, inspect
from rich.prompt import IntPrompt, Prompt, Confirm
from rich.layout import Layout
from rich.text import Text as rText
from rich.table import Table as rTable
from rich.console import Console as rCon
from rich.style import Style as rStyle
from sshkeyboard import listen_keyboard, stop_listening
from sys import stdin
from termios import tcflush, TCIOFLUSH



x=y=0 #cursor postition for selections
xMax=yMax=10 #max length of printed page of partner nodes list
vf=5 #verbosity filter. 0 instructs to stfu
config=None
sNodes=[] #list of selsected entrys(partners) from partnersdb
selectedentrys=[] #indexes of selected entrys
partnerSelectDb=[] #list of partners to select from
console = rCon()
submenu = 'list' #in what level of sub menu is the user
continueListening = True #continue Listening for keyboard?


# generate fake public keys for testing
def genFPK():
    l=66
    chars=['0','1','2','3','4','5','6','7','8','9','A','b','c','d','e','f']
    out=[]
    for i in range(l): out.append(random.choice(chars))
    return(''.join(out))

# decide what to do on keypress
def selectFromList(key):
    global x,y,xMax,yMax,partnerSelectDb,selectedentrys,sNodes,submenu,continueListening,opener
    #inspect(key)
    #if key == keyboard.Key.esc:
    #    #raise abort flag
    #    sNodes=[]
    #    rPrint(selectedentrys)
    #    for s in selectedentrys: sNodes.append(partnerSelectDb[s])
    #    #return(sNodes)
    #    #flush build up inputbuffer
    #    tcflush(stdin, TCIOFLUSH)
    #    return(False)# stop listener
    #try:
    #    k = key.char  # single-char keys
    #except:
    #    k = key.name  # other keys
    if key == 'q' or key == 'esc':
        sNodes=[]
        rPrint(selectedentrys)
        for s in selectedentrys: sNodes.append(partnerSelectDb[s])
        #return(sNodes)
        #flush build up inputbuffer
        tcflush(stdin, TCIOFLUSH)
        stop_listening()# stop listener
        continueListening=False
        return(False)

    elif key == 'e' and submenu == 'list':
        submenu = 'editPartner'
        stop_listening()# stop listener
        editPartner(y)
        submenu = 'list'
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)

    elif key == 's' and submenu == 'list':
        submenu = 'suchen'
        stop_listening()# stop listener
        selectedentrys=[]
        y=0
        nodes=findNode()
        printNodes(nodes,selectedentrys=selectedentrys,curentcursor=y)
        #submenu = 'list'
        #plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)

    elif key == 'up':
        if submenu == 'list':
            if y > 0: y-=1
            else: y = len(partnerSelectDb)-1
            plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
        #y-=1
    elif key == 'down':
        if submenu == 'list':
            if y < len(partnerSelectDb)-1: y+=1
            else: y = 0
            plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
        #y+=1
    elif key == 'pageup':
        if submenu == 'list':
            if y > 0: y-=yMax
            else: y = len(partnerSelectDb)-1
            plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
        #y-=1
    elif key == 'pagedown':
        if submenu == 'list':
            if y < len(partnerSelectDb)-1: y+=yMax
            else: y = 0
            plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
        #y+=1
    elif key == 'left':
        if submenu == 'list':
            if x > 0: x-=1
            else: x = xMax

    elif key == 'right':
        if submenu == 'list':
            if x < xMax: x+=1
            else: x = 0

    elif key == 'space':
        if submenu == 'list':
            if y in selectedentrys:selectedentrys.remove(y)
            else: selectedentrys.append(y)
            plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)

    elif key == 'o' and submenu ==  'list':
        stop_listening()# stop listener
        #tcflush(stdin, TCIOFLUSH)
        sleep(1)
        correct = Confirm.ask(f'Calling channel-open-function on {len(selectedentrys)} selected nodes?',default=False)
        if not correct: rPrint('Abborted opening.')
        if correct == True:
            submenu = 'opening'
            opener(sNodes)
            sleep(5)
            submenu = 'list'
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)

    rPrint(x,y)
    #flush build up inputbuffer
    #tcflush(stdin, TCIOFLUSH)
    return(True)

#edit some specs of partner and return edited object
def editPartner(pID):
    global partnerSelectDb, console
    #flush build up inputbuffer
    #tcflush(stdin, TCIOFLUSH)
    partner = partnerSelectDb[pID]
    console.clear()
    #inspect(partner)
    #rPrint(partner.keys())
    correct = False
    while not correct:
        newCS = IntPrompt.ask(f"New size of channel with {partner['alias']}",default=int(partner['chanSize']))
        if newCS < 1000000: rPrint('[red bold]Warning[/red bold] Channelsize less than 1 million Satoshi!')
        correct = Confirm.ask(f"Edit {partner['alias']}'s Channelsize to {newCS}?",default=False)
    partner['chanSize']=newCS
    #newCS = console.input('New channelsize for '+str(partner['alias'])+' ('+str(partner['chanSize'])+'):')
    #rPrint('New channelsize:',newCS,'\nNote, to add:','/nAll correct([bold]y[/bold] to confirm)')
    return(partner)

def findNode():
    global graph, vf
    console.clear()
    sleep(0.1)
    try:
        phrase=Prompt.ask("Wonach suchen?",default='swissknife')
    except EOFError as e:
        rPrint(f'EOFError:{e}')
        sleep(2)
        phrase=Prompt.ask("Wonach suchen?",default='swissknife')
    ergebnis=[node for node in graph['nodes'] if node['pub_key'].lower().find(str(phrase).lower()) > -1 or node['alias'].lower().find(str(phrase).lower()) > -1]
    return(ergebnis)

def printNodes(nodes,selectedentrys=[],curentcursor=0):
    global console
    numPages=math.ceil(len(nodes)/yMax)
    curPage=math.ceil(curentcursor/yMax)
    pt = rTable(title="Use [bold][Space][/bold] to (de)select entrys, [bold]\[a][/bold] to add Node and [bold][Up][/bold]/[bold][Down][/bold] to navigate. Page [bold]"+str(curPage)+"[/bold]/[bold]"+str(numPages)+'[/bold]')
    pt.add_column("Alias", justify="left", style="cyan", no_wrap=True)
    pt.add_column("Public Key", justify="left", style="cyan", no_wrap=True)
    pt.add_column("Size", justify="center", style="green", no_wrap=True)
    pt.add_column("S", justify="right", style="white", no_wrap=True)
    for i,node in enumerate(nodes):
        if curPage == math.ceil(i/yMax):
            choosen=''
            if i in selectedentrys: choosen='[bold]*[/bold]'
            alias=rText(node['alias'],style=node['color'])
            cs=rText(str(getChansize(node['pub_key'])))
            pk=rText(node['pub_key'])
            s=None
            if i == curentcursor: s='on #fafafa'
            pt.add_row(alias,pk,cs,choosen,style=s)
    console.print(pt)
    return(None)

def getChansize(pubkey):
    return(5000000)



#prints table, containing partner list and highlight currently selected partner
def plistTable(partners,selectedentrys=[],curentcursor=0):
    global console, sNodes
    console.clear()
    numPages=math.ceil(len(partners)/yMax)
    curPage=math.ceil(curentcursor/yMax)
    pt = rTable(title="Use [bold][Space][/bold] to (de)select entrys, [bold]\[e][/bold] to edit, [bold]\[o][/bold] to open and [bold][Up][/bold]/[bold][Down][/bold] to navigate. Page [bold]"+str(curPage)+"[/bold]/[bold]"+str(numPages)+'[/bold]')
    pt.add_column("Alias", justify="left", style="cyan", no_wrap=True)
    pt.add_column("Size", justify="center", style="green", no_wrap=True)
    pt.add_column("Public Key", justify="left", style="cyan", no_wrap=True)
    pt.add_column("Fee", justify="left", style="cyan", no_wrap=True)
    pt.add_column("FayeFee", justify="left", style="cyan", no_wrap=True)
    pt.add_column("S", justify="right", style="white", no_wrap=True)
    #pt.add_column("open", justify="left", style="cyan", no_wrap=True)
    for i,p in enumerate(partners):
        if curPage == math.ceil(i/yMax):
            choosen=''
            if i in selectedentrys: choosen='[bold]*[/bold]'
            alias=rText(p['alias'],style=p['color'])
            cs=rText(str(p['chanSize']))
            pk=rText(p['pubkey'])
            pf=rText(str(p['fee']),style='red')
            ff=rText(str(p['fayefee']),style='red')
            s=None
            if i == curentcursor: s='on #fafafa'
            #rPrint(p)
            #Confirm.ask('Established?')
            if p['isEstablished'] == False:
                #testasd = rText('testtext')
                #inspect(testasd)
                #rPrint(testasd)
                #Confirm.ask(f'vor: {alias}/{testasd}')
                alias.stylize('strike')
                #testasd.stylize('blue')
                #testasd.stylize('strike')
                #inspect(testasd)
                #rPrint(testasd)
                #Confirm.ask(f'nach: {alias}/{testasd}')
                cs.stylize('strike')
                pk.stylize('strike')
            pt.add_row(alias,cs,pk,pf,ff,choosen,style=s)

    st = rTable(title='Selected Partners')
    st.add_column("Alias", justify="left", style="cyan", no_wrap=True)
    st.add_column("Size", justify="center", style="green", no_wrap=True)
    st.add_column("Public Key", justify="left", style="cyan", no_wrap=True)
    sNodes=[]
    for se in selectedentrys: sNodes.append(partnerSelectDb[se])
    for p in sNodes:
        alias=rText(p['alias'],style=p['color'])
        cs=rText(str(p['chanSize']))
        pk=rText(p['pubkey'])
        if not p['isEstablished']:
            alias.stylize('strike')
            cs.stylize('strike')
            pk.stylize('strike')
        st.add_row(alias,cs,pk,choosen)


    #rPrint("Use [Space] to (de)select entrys and [Up]/[Down] to navigate. Page ",curPage,"/",numPages,sep='',end='\n\n')
    #print partnertable
    console.print(pt)
    #inspect(st)
    console.print(st)

#takes list of partners, a callback function for opening channels and initalizes UI with it
#returns keylistener
def initUI(partners, **callbacks):
    global partnerSelectDb,continueListening,opener,graph
    if 'opener' in callbacks.keys():
        opener=callbacks['opener']
    if 'graph' in callbacks.keys():
        graph=callbacks['graph']
    partnerSelectDb = partners
    plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
    while continueListening:
        listen_keyboard(on_press=selectFromList,
                    sequential=False,
                    until=None,
                    delay_second_char=0.05,
                    delay_other_chars=0.05,)
    #listener = keyboard.Listener(on_press=selectFromList)
    #return(listener)

# returns a dict with selected partners, all partners and ...
# clears all selection if clear == True
def getEditedPartners(clear=False):
    global partnerSelectDb, sNodes, selectedentrys
    partnerdict = {'allPartners':partnerSelectDb,'selectedPartners':sNodes}
    if clear:
        sNodes=[]
        selectedentrys=[]
    return(partnerdict)


if __name__ == "__main__":
    #generate testdata
    colors=['#123456','#ffffff','#afafaf','#fafafa','#ddffdd','#ddeeaa','#00dd00','#dd0000','#0000dd']
    for i in range(100):
        partnerSelectDb.append({'alias':'node'+str(i),'fee':random.choice([i,int(i*random.randint(2,4)),random.randint(0,35)]),'pubkey':genFPK(),'isEstablished':random.choice([True,False]),'chanSize':random.choice([5000000,1000000,10000000,12345678,111111]),'color':random.choice(colors),'notes':'This is a placeholder','pType':'test','reopenUntill':600000,'hoststring':'pk@a.sd','hosts':['a.sd']})

    #selectListener = keyboard.Listener(on_press=selectFromList)
    #selectListener.start()  # start to listen on a separate thread
    #rPrint("vor join")
    #sleep(100)
    #selectListener.join()  # remove if main thread is polling self.keys
    plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
    while continueListening:
        listen_keyboard(on_press=selectFromList,
                    sequential=False,
                    until=None,
                    delay_second_char=0.05,
                    delay_other_chars=0.05,)
    rPrint(sNodes)
