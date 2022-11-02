from rich import print as rPrint
from rich.rule import Rule
#returns a dict with 4 sorted lists of all R G and B colors and rgb-color used in nodes datafield
def sliceColors(graph):
    colors = sorted([node['color'][1:] for node in graph['nodes'] if node['color'] != '#ffffff' and node['color'] != '#FFFFFF' and node['color'] != '#000000'])
    return(colors)

def deconstructColors(colors):
    r = [c[0:2] for c in colors]
    g = sorted([c[2:4] for c in colors])
    b = sorted([c[4:6] for c in colors])
    return({'colors':colors,'reds':r,'greens':g,'blues':b})

#traverses list and returns only elements, which occurr exactly one time
#as well as a sorted dict of all colors and number of occurencies
def unique(colors):
    occurencetable={}
    uniquelist=[]
    for c in colors:
        if c in occurencetable.keys():
            occurencetable[c]+=1
        else:
            occurencetable.update({c:1})
    tops={key: value for key, value in sorted(occurencetable.items(), key=lambda item: item[1])}
    for k in occurencetable.keys():
        if occurencetable[k] == 1: uniquelist.append(k)
    return(uniquelist,tops)





def wieBunt(colordict):
    meanC=colordict['colors'][int(len(colordict['colors'])/2)]
    meanR=colordict['reds'][int(len(colordict['reds'])/2)]
    meanG=colordict['greens'][int(len(colordict['greens'])/2)]
    meanB=colordict['blues'][int(len(colordict['blues'])/2)]
    avgC=avgR=avgG=avgB=0
    for i in range(len(colordict['colors'])):
        avgC+=int(colordict['colors'][i],16)
        avgR+=int(colordict['reds'][i],16)
        avgG+=int(colordict['greens'][i],16)
        avgB+=int(colordict['blues'][i],16)
    avgC=str(hex(int(avgC/len(colordict['colors']))))[2:]
    avgR=str(hex(int(avgR/len(colordict['colors']))))[2:]
    avgG=str(hex(int(avgG/len(colordict['colors']))))[2:]
    avgB=str(hex(int(avgB/len(colordict['colors']))))[2:]
    rPrint('mean color=[#'+meanC+']'+meanC)
    rPrint('mean color by each tone=[#'+meanR+meanG+meanB+']'+meanR+meanG+meanB)
    rPrint('avg color is [#'+avgC+']'+avgC)
    rPrint('avg color by each tone is [#'+avgR+avgG+avgB+']'+avgR+avgG+avgB)
    rPrint('Data consists of '+str(len(colordict['colors']))+' colors, whereby '+str(len(set(colordict['colors'])))+' colors differ.')

def printData(graph):
    rPrint(Rule('Slicing colors'))
    allcolors=sliceColors(graph)
    uniqecolors,tops=unique(allcolors)
    rPrint(Rule('All colors except black and white'))
    wieBunt(deconstructColors(allcolors))
    rPrint(Rule('Only unique colors except black and white'))
    wieBunt(deconstructColors(uniqecolors))
    rPrint(Rule('top 10 colors'))
    topsl=list(tops)
    topsl.reverse()
    for i in topsl[0:10]:
        rPrint(f'[#{i}]{i}[/#{i}] x {tops[i]}')
