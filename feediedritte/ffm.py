
#flask fee manager
from flask import Flask, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from rich import inspect
from daemon import start,stop,handOutChans,addPixi, isRunning, setter
from time import sleep

app = Flask(__name__)
app.config['SECRET_KEY'] = 'jehaim,aendert das!'

#form Class for daemon config
class daemonForm(FlaskForm):
    tickrate = StringField(label="ticks/hour", default="1", validators=[DataRequired()])
    minfee = StringField(label="min Fee", default="1")
    maxfee = StringField(label="max Fee")
    sf = StringField(label="vier")
    testsf = [StringField(label="fuenf", default="1"),StringField(label="sex")]
    submit = SubmitField("abdafuer")


#routes
@app.route('/')
def mainpage():
    return('hier platzhalter.')


@app.route('/chans/<chanid>')
def chandetails(chanid):
    return(chanid)

@app.route('/templates/<tmp>', methods=['GET','POST'])
def rt(tmp):
    daemonCheck()
    configForm = daemonForm()
    #chans=[{'id':'9c999f',
     #   'name':'namensspuel',
     #   'upscore':'6',
     #   'downscore':'3543543543',
     #   'fee':'30'}]
    return(render_template(tmp,form=configForm,chans=handOutChans()))

@app.route('/actions/<action>')
def daemonAction(action):
    if action == 'start': 
        print('trying to start daemon')
        start()
    if action == 'stop' :
        print('trying to stop daemon')
        stop()
    return("idk")

@app.route('/addpixi/<node>')
def addpixi(node):
    pass
    return(addPixi(node))


@app.route('/clear/<chanID>')
def clearScore(chanID):
    pass
    setter(data=None, what='clear', chanID=chanID)
    return('bau ma redirect!')

def daemonCheck():
    if isRunning():return(None)
    print('Daemoncheck failed. Conjuring daemon...')
    start()

#daemonCheck()