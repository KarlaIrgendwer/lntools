#pimpled servant to load and dump data to harddrive
#direction shall be 'load' or 'dump'
#jar (to use) defaults to lnmDB.pickle
#returns -1 on error
def pickleKnecht(direction='load',jar='state.pickle',state=None):
    global vf
    if direction == 'load':
        if vf>2:rPrint('trying to unpickle some old data.')
        try:
            with open(jar,"rb") as f:
                state = pickle.load(f)
                state['counters']['reboots'] += 1
                if vf>2:rPrint("unpickled old Data.")
        except Exception as e:
            if vf>2:rPrint("No old Data found.\nSince I was instructed to load stuff, I will try to create a dataset by recovering from closed and open channels./nerror:",e)
            state={'channels':[],
                    'locked':False,
                    'createtime':time.localtime(),
                    'counters':{'reboots':0,'reloads':0,'updateactions':0,'adjustmentactions':0}}
                    }
    elif direction == 'dump':
        if vf>2:
            if state == None: rPrint('Warning: trying to pickle nothing.')
            rPrint('trying to pickle data towards: ',jar)
        try:
            with open(jar,"wb") as f:
                pickle.dump(state,f)
                if vf>2:rPrint("pickled Data towards ",jar)
        except Exception as e:
            if vf>0:rPrint("Oh noes! I could not pickle Data to ",jar, '/nGot hit by Exception: ',e) #your servant became just a little bit more hideous
            r=-1
    else: r=-1
    return(state)





def initpickle(path='./state.pickle'):
    state={'channels':[],
            'locked':False,
            'createtime':time.localtime(),
            'counters':{'reboots':0,'reloads':0,'updateactions':0,'adjustmentactions':0}}
            }
