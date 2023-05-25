# Copyright (c) 2023 VISTEC - Vidyasirimedhi Institute of Science and Technology
# Distribute under MIT License
# Authors:
#  - Sucha Supittayapornpong <sucha.s[-at-]vistec.ac.th>
#  - Kanatip Chitavisutthivong <kanatip.c_s18[-at-]vistec.ac.th>

import os

HCONST = { 'topology data directory': 'Precomputation',
           'commodity data directory': 'commodity',
           'flow data directory': 'flow',
           'link data directory': 'link',
           'traffic data directory': 'traffic',
           'stage data directory': 'stage',
           'commdir': None,
           'flowdir': None,
           'linkdir': None,
           'trafficdir': None,
           'stagedir': None,
           'output data directory': 'Output',
           'intermediate data directory': 'intermediate',
           'outputdir': None,
           'intmeddir': None}


def involve(node, autmap):
    return autmap[node] != node


def applyGenerator(nodes, autmap):
    return tuple(autmap[n] for n in nodes)


def makeTopologyDataDirectory(rootdir):
    if not os.path.exists(rootdir):
        os.mkdir(rootdir)
    if not os.path.exists(rootdir + '/' + HCONST['topology data directory']):
        os.mkdir(rootdir + '/' + HCONST['topology data directory'])


def makeAutomorphicDataDirectory(rootdir, toponame):
    topopath = rootdir + '/' + HCONST['topology data directory'] + '/' + toponame
    if not os.path.exists(topopath):
        os.mkdir(topopath)

    commpath = topopath + '/' + HCONST['commodity data directory']
    if not os.path.exists(commpath):
        os.mkdir(commpath)
    HCONST['commdir'] = commpath

    flowpath = topopath + '/' + HCONST['flow data directory']
    if not os.path.exists(flowpath):
        os.mkdir(flowpath)
    HCONST['flowdir'] = flowpath

    linkpath = topopath + '/' + HCONST['link data directory']
    if not os.path.exists(linkpath):
        os.mkdir(linkpath)
    HCONST['linkdir'] = linkpath

    trafficpath = topopath + '/' + HCONST['traffic data directory']
    if not os.path.exists(trafficpath):
        os.mkdir(trafficpath)
    HCONST['trafficdir'] = trafficpath

    stagepath = topopath + '/' + HCONST['stage data directory']
    if not os.path.exists(stagepath):
        os.mkdir(stagepath)
    HCONST['stagedir'] = stagepath
    
    
def makeOutputDataDirectory(rootdir, toponame):
    if not os.path.exists(rootdir):
        os.mkdir(rootdir)
        
    outputpath = rootdir + '/' + HCONST['output data directory']
    if not os.path.exists(outputpath):
        os.mkdir(outputpath)

    topopath = outputpath + '/' + toponame
    if not os.path.exists(topopath):
        os.mkdir(topopath)
    HCONST['outputdir'] = topopath

    intmedpath = topopath + '/' + HCONST['intermediate data directory']
    if not os.path.exists(intmedpath):
        os.mkdir(intmedpath)
    HCONST['intmeddir'] = intmedpath
    
    
def initHCONST(rootdir, toponame, objfunc):
    topopath = rootdir + '/' + HCONST['topology data directory'] + '/' + toponame
    
    commpath = topopath + '/' + HCONST['commodity data directory']
    HCONST['commdir'] = commpath

    flowpath = topopath + '/' + HCONST['flow data directory']
    HCONST['flowdir'] = flowpath

    linkpath = topopath + '/' + HCONST['link data directory']
    HCONST['linkdir'] = linkpath

    trafficpath = topopath + '/' + HCONST['traffic data directory']
    HCONST['trafficdir'] = trafficpath

    stagepath = topopath + '/' + HCONST['stage data directory']
    HCONST['stagedir'] = stagepath    

    outputpath = rootdir + '/' + HCONST['output data directory'] + '/' + toponame + '-' + str(objfunc)
    HCONST['outputdir'] = outputpath

    intmedpath = outputpath + '/' + HCONST['intermediate data directory']
    HCONST['intmedpath'] = intmedpath
