from anfang import pickleIgor
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

continueListening=True
openings=[]


def keyinput(key):
    global continueListening, openings
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


def startui():
    global continueListening, openings
    while continueListening:
    listen_keyboard(on_press=keyinput,
                sequential=False,
                until=None,
                delay_second_char=0.05,
                delay_other_chars=0.05,)