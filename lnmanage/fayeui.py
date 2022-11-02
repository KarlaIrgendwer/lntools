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
xMax=yMax=15 #max length of printed page of partner nodes list
vf=5 #verbosity filter. 0 instructs to stfu
config=None
sNodes=[] #list of selsected entrys(partners) from partnersdb
selectedentrys=[] #inexes of selected entrys
partnerSelectDb=[] #list of partners to select from
console = rCon()
submenu = 'list' #in what level of sub menu is the user
continueListening = True #continue Listening for keyboard?
sorting = 'lnd-Output'


# generate fake public keys for testing
def genFPK():
    l=66
    chars=['0','1','2','3','4','5','6','7','8','9','A','b','c','d','e','f']
    out=[]
    for i in range(l): out.append(random.choice(chars))
    return(''.join(out))

# decide what to do on keypress
def selectFromList(key):
    global x,y,xMax,yMax,partnerSelectDb,selectedentrys,sNodes,submenu,continueListening,opener,sorting
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

    elif key == 'up' and submenu == 'list':
        if y > 0: y-=1
        else: y = len(partnerSelectDb)-1
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
        #y-=1
    elif key == 'down' and submenu == 'list':
        if y < len(partnerSelectDb)-1: y+=1
        else: y = 0
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
        #y+=1
    elif key == 'pageup' and submenu == 'list':
        if y > 0: y-=yMax
        else: y = len(partnerSelectDb)-1
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
        #y-=1
    elif key == 'pagedown' and submenu == 'list':
        if y < len(partnerSelectDb)-1: y+=yMax
        else: y = 0
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
        #y+=1
    elif key == 'left' and submenu == 'editPartner':
        if x > 0: x-=1
        else: x = xMax

    elif key == 'right' and submenu == 'editPartner':
        if x < xMax: x+=1
        else: x = 0

    elif key == 'space' and submenu ==  'list':
        if y in selectedentrys:selectedentrys.remove(y)
        else: selectedentrys.append(y)
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
    #sort by balance
    elif key == 'b' and submenu ==  'list':
        partnerSelectDb=sorted(partnerSelectDb,key=lambda item:(int(item['local_balance'])/(int(item['local_balance'])+int(item['remote_balance']))) )
        if sorting=='balance':
            partnerSelectDb.reverse()
            sorting='ecnalab'
        else: sorting='balance'
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
    #sort by channelsize
    elif key == 's' and submenu ==  'list':
        partnerSelectDb=sorted(partnerSelectDb,key=lambda item:item['chanSize'])
        if sorting=='size':
            partnerSelectDb.reverse()
            sorting='ezis'
        else: sorting='size'
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)
    #sort by name
    elif key == 'n' and submenu ==  'list':
        partnerSelectDb=sorted(partnerSelectDb,key=lambda item:item['alias'])
        if sorting=='name':
            partnerSelectDb.reverse()
            sorting='eman'
        else: sorting='name'
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)

    elif key == 'r' and submenu ==  'list':
        rPrint("call ing Pixi")
        rePixi()
        
    elif key == 'o' and submenu ==  'list':
        stop_listening()# stop listener
        tcflush(stdin, TCIOFLUSH)
        correct = False
        correct = Confirm.ask(f'Calling channel-open-function on {len(selectedentrys)} selected nodes?')
        if not correct: rPrint('Abborted opening.')
        if correct == True:
            submenu = 'opening'
            opener(sNodes)
            sleep(5)
            submenu = 'list'
        plistTable(partners=partnerSelectDb,selectedentrys=selectedentrys,curentcursor=y)

    rPrint(x,y)
    #flush build up inputbuffer
    tcflush(stdin, TCIOFLUSH)
    return(True)

#edit some specs of partner and return edited object
def editPartner(pID):
    global partnerSelectDb, console
    #flush build up inputbuffer
    tcflush(stdin, TCIOFLUSH)
    partner = partnerSelectDb[pID]
    console.clear()
    inspect(partner)
    rPrint(partner.keys())
    correct = False
    while not correct:
        newFee = IntPrompt.ask(f"New Fee of channel with {partner['alias']}",default=int(partner['fayefee']))
        if newFee < 2: rPrint('[red bold]Warning[/red bold] Fee less than 2 Satoshi per million!')
        correct = Confirm.ask(f"Edit {partner['alias']}'s Fee to {newFee}?",default=False)
    partner['fee']=newFee
    #newCS = console.input('New channelsize for '+str(partner['alias'])+' ('+str(partner['chanSize'])+'):')
    #rPrint('New channelsize:',newCS,'\nNote, to add:','/nAll correct([bold]y[/bold] to confirm)')
    return(partner)

#prints table, containing partner list and highlight currently selected partner
def plistTable(partners,selectedentrys=[],curentcursor=0):
    global console, sNodes, sorting
    console.clear()
    numPages=math.ceil(len(partners)/yMax)
    curPage=math.ceil(curentcursor/yMax)
    pt = rTable(title="Use [bold][Space][/bold] to (de)select, [bold]\[e][/bold] to edit, [bold]\[b/s/n/u/d/f][/bold] to change sorting and [bold][Up][/bold]/[bold][Down][/bold] to navigate. Page [bold]"+str(curPage)+"[/bold]/[bold]"+str(numPages)+'[/bold] sorting:'+sorting)
    pt.add_column("Alias", justify="left", style="cyan", no_wrap=True)
    pt.add_column("Balance", justify="center", style="green", no_wrap=True)
    pt.add_column("Info", justify="left", style="cyan", no_wrap=True)
    pt.add_column("Fee", justify="left", style="cyan", no_wrap=True)
    pt.add_column("FayeFee", justify="left", style="cyan", no_wrap=True)
    pt.add_column("upscore", justify="left", style="cyan", no_wrap=True)
    pt.add_column("downscore", justify="left", style="cyan", no_wrap=True)
    pt.add_column("flowscore", justify="left", style="cyan", no_wrap=True)
    pt.add_column("S", justify="right", style="white", no_wrap=True)
    #pt.add_column("open", justify="left", style="cyan", no_wrap=True)
    for i,p in enumerate(partners):
        if curPage == math.ceil(i/yMax):
            choosen=''
            if i in selectedentrys: choosen='[bold]*[/bold]'
            alias=rText(p['alias'],style=p['color'])
            cs=rText(f"{p['local_balance']} << {p['chanSize']} >> {p['remote_balance']}")
            cs.stylize('#00ced1',cs.plain.find('<<')+3,cs.plain.find('>>')-1)
            cs.stylize('#32cd32',0,cs.plain.find('<<')-1)
            cs.stylize('#ff6347',cs.plain.find('>>')+3)
            info=rText("nothing yet")
            pf=rText(str(p['fee']),style='#daa520')
            ff=rText(str(p['fayefee']),style='#daa520')
            us=rText(str(p['upscore']),style='#800080')
            ds=rText(str(p['downscore']),style='#800080')
            fs=rText(str(p['flowscore']),style='#800080')
            s=None
            if i == curentcursor: s='on #fafafa'
            if p['isEstablished'] == False:
                alias.stylize('strike')
                cs.stylize('strike')
                pk.stylize('strike')
            pt.add_row(alias,cs,info,pf,ff,us,ds,fs,choosen,style=s)

    console.print(pt)


#takes list of partners, a callback function for opening channels and initalizes UI with it
#returns keylistener
def initUI(partners, **callbacks):
    global partnerSelectDb,continueListening,opener,rePixi
    if 'opener' in callbacks.keys():
        opener=callbacks['opener']
    else: opener=inspect
    if 'rePixi' in callbacks.keys():
        rePixi=callbacks['rePixi']
    else: rePixi=inspect
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
