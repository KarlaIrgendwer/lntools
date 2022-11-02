import pickle, random, math, threading, signal, json
from time import time,sleep
from rich import print as rPrint, inspect
from rich.console import Console
from rich.layout import Layout
from rich.text import Text as rText
from rich.table import Table as rTable
from rich.progress import Progress
from rich.rule import Rule
from rich.prompt import IntPrompt, Prompt, Confirm
from sshkeyboard import listen_keyboard, stop_listening
from sys import stdin
from termios import tcflush, TCIOFLUSH
from anfang import callExt


# this is yardsale-server it manages json data about items in invetrorys
# one inventrory is list of known serves with there funktions and conditions
# other inventory is inventory of items own server provides for sale (functions(f.e.
# pubkeypicture) and physical coins made of chokola and random seeds)

# first to implement vector of json data supplement is by using ln keysend feature
# so this will start as a keysend crawler

ksmTypes={
    '7629168':'tipping: Tip note / destination',
    '7629169':'podcast: JSON encoded metadata',
    '7629171':'tipping: Tip note / destination',
    '7629173':'podcast: Proposed (WIP) standard',
    '7629175':'podcast: PodcastIndex ID or GUID',
    '34349334':'chat: Chat message Whatsat and more',
    '34349337':'chat: Signature',
    '34349339':'chat: Chat message Whatsat and more',
    '34349340':'chat: Thunder Hub Sending Node Name ',
    '34349343':'chat: Timestamp',
    '34349345':'chat: Thunder Hub Content type typically "text"',
    '34349347':'chat: Thunder Hub Request type typically "text"',
    '133773310':'podcast: JSON encoded data',
    '5482373484':'keysend Preimage as 32 bytes',
    '696969':'lnpay: LNPay wallet destination',
    '818818':'hive: Hive account name',
    '112111100':'lnpay: LNPay Wallet ID'} #types of keysend messages

vf=5 #verbosity filter. 0 instructs to stfu
def inspectKeysend(ks):
    global vf,ksmTypes
    data = {'amt':2}
    return

def getKeysends():
    global vf
    o,r,t = callExt({'Popen_this':['lncli','listinvoices','--max_invoices','1'],'in_this_docker_container':'abs/lnd:v'})
    numInvoices = json.loads(o)['last_index_offset']
    o,r,t = callExt({'Popen_this':['lncli','listinvoices',f'--max_invoices', str(numInvoices)],'in_this_docker_container':'abs/lnd:v'})
    allEvents=json.loads(o)['invoices']

    ks=[evnt for evnt in allEvents if evnt['is_keysend'] == True]
    return(ks,allEvents)

def metrics(data):
    summe=sum([int(d['value_msat']) for d in data])
    avg=summe/len(data)
    median=sorted(data, key=lambda x:x['value_msat'])[int(len(data)/2)]['value_msat']
    return(f'{str(summe)}|{int(avg)}|{int(median)}')


#beware: currently prints data only, if ksmType is known
def printgui(data, **coords):
    global ksmTypes
    if 'y' in coords.keys():
        y = coords['y']
    if 'x' in coords.keys():
        x = coords['x']
    if 'backpack' in coords.keys():
        backpack=coords['backpack']
    if 'console' in coords.keys():
        console = coords['console']
    else: return('Need console to print to.')
    if 'metrics' in coords.keys():
        m = f"{data[x]['value_msat']}|{coords['metrics']}"
    else: m = "NaN"
    console.clear()
    rPrint(Rule(f"Showing Tx {x}/{len(data)}\t mS(1|A|∅|M):{m}"))
    messages = []
    for h in data[x]['htlcs']:
        for mt in ksmTypes.keys():
            if mt in h['custom_records'].keys():
                hdata = h['custom_records'][mt]
                #inspect(hdata)
                #rPrint(hdata)
                try: strdata = bytes.fromhex(hex(int(hdata,16))[2:]).decode('utf-8')
                except UnicodeDecodeError as e:
                    strdata='Could not de-unicoded.'
                messages.append({'type':ksmTypes[mt], 'hexdata':hdata, 'stringdata':strdata})
    if y==0: inspect(data[x])
    else:
        rPrint(messages[y-1])



if __name__ == '__main__':

    if vf>2:
        rPrint(Rule("LN Shop"))
        rPrint("looking for old statefile")
        rPrint("asking old known peers for bootup data")

        rPrint("reparsinging tx-db")
        ks,a=getKeysends()
        m=metrics(ks)
        printgui(ks,x=0,y=1,console=Console(),metrics=m)
        rPrint("istalling runner")

