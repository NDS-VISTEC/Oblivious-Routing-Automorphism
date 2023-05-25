# Copyright (c) 2023 VISTEC - Vidyasirimedhi Institute of Science and Technology
# Distribute under MIT License
# Authors:
#  - Sucha Supittayapornpong <sucha.s[-at-]vistec.ac.th>
#  - Kanatip Chitavisutthivong <kanatip.c_s18[-at-]vistec.ac.th>

import os
from functools import partial
import multiprocessing as mp

import network_generator as netgen
from topology_automorphism import Topology
from optimization_mosekfusion import OptimizationCVX_MOSEK
import state_helper as helper
from state_helper import HCONST, initHCONST
from verification import Verification

from dring_routing import DRingRouting
from verification_dring_route import VerificationDRing

ProcessorCount = mp.cpu_count()
NumThread = ProcessorCount
NumLPThread = ProcessorCount


TOPOLOGY = {'SlimFly': partial(netgen.loadSlimFly),
            'AbstractAugmentExpander': partial(netgen.generateAbstractAugmentExpander),
            'FatTreePartial': partial(netgen.generateFatTreePartial),
            'Torus2D': partial(netgen.generateTorus2D),
            'FatClique': partial(netgen.generateFatClique),
            '2LevelClos': partial(netgen.generate2LevelClos),
            'Clique': partial(netgen.generateClique),
            'BinaryCube': partial(netgen.generateBinaryCube),
            'DRing': partial(netgen.generateDRing),
            'DRingOriginal': partial(netgen.generateDRing_80_64),
            'Torus3D': partial(netgen.generateTorus3D),
            'Grid3D': partial(netgen.generateGrid3D),
            'Grid2D': partial(netgen.generateGrid2D),
            'Ring': partial(netgen.generateRing),
        } 


def process(G, toponame, objfunc, mosek_params, verify):
    rootdir = '.'
    initHCONST(rootdir, toponame, objfunc)
    helper.makeTopologyDataDirectory(rootdir)
    helper.makeAutomorphicDataDirectory(rootdir, toponame)
    helper.makeOutputDataDirectory(rootdir, toponame+'-' + str(objfunc))
    
    topo = Topology(G, toponame, NumThread)

    opt = OptimizationCVX_MOSEK(topo, NumLPThread, objfunc=objfunc, mosek_params=mosek_params)
    opt.optimize()

    if verify == True:
        ver = Verification(toponame, NumThread, objfunc)
        ver.verifyAllLinkLoad()


def run_example(topology, topo_params, objective_function, mosek_params={}, verify=True):
    if topology in TOPOLOGY.keys():
        G, toponame = TOPOLOGY[topology](topo_params)
        objfunc = objective_function['objfunc']
        if topology == 'DRing':
            numToRPerBlock = topo_params['numToRPerBlock']
            process_dring(G, toponame, numToRPerBlock, objfunc, mosek_params, verify)
        elif topology == 'DRingOriginal':
            numToRPerBlock = 10
            process_dring(G, toponame, numToRPerBlock, objfunc, mosek_params, verify)
        else:
            process(G, toponame, objfunc, mosek_params, verify)
    else:
        print('There is no specified topology in this example.')


def process_dring(G, toponame, numToRPerBlock, objfunc, mosek_params, verify):
    rootdir = '.'
    initHCONST(rootdir, toponame, objfunc)
    helper.makeTopologyDataDirectory(rootdir)
    helper.makeAutomorphicDataDirectory(rootdir, toponame)
    helper.makeOutputDataDirectory(rootdir, toponame+'-' + str(objfunc))

    topo = Topology(G, toponame, NumThread)

    if objfunc == 'linear' or objfunc == 'log':
        opt = OptimizationCVX_MOSEK(topo, NumLPThread, objfunc=objfunc, mosek_params=mosek_params)
        opt.optimize()
    else:
        if objfunc == 'ecmp':
            Route_mode = 'ECMP'
            dringRouting = DRingRouting(G, topo, numToRPerBlock, Route_mode)
        elif objfunc == 'su2':
            Route_mode = 'ShortestUnion2'
            dringRouting = DRingRouting(G, topo, numToRPerBlock, Route_mode)
        else:
            Route_mode = 'ShortestUnion2'
            dringRouting = DRingRouting(G, topo, numToRPerBlock, Route_mode)
        
        if verify == True:
            ver = VerificationDRing(toponame, NumThread, objfunc)
            ver.verifyAllLinkLoad()
            return

    if verify == True:
        ver = Verification(toponame, NumThread, objfunc)
        ver.verifyAllLinkLoad()


if __name__ == '__main__':

    # Clique Log function
    topo_params = {'numServerPerToR':10, 'numToR': 4, 'linkCapacity':1 }
    objective_function = {'objfunc': 'log'}
    mosek_params = {'mosek_params': {"intpntCoTolNearRel":"10000", "optimizer":"conic", "numThreads":0, "presolveUse":"off"}}
    run_example('Clique', topo_params=topo_params, objective_function=objective_function, mosek_params=mosek_params)
    '''
    # Partial Fattree Log function
    topo_params = {'switchRadix':32, 'numAgg': 4}
    objective_function = {'objfunc': 'log'}
    mosek_params = {'mosek_params': {"intpntCoTolNearRel":"10000", "optimizer":"conic", "numThreads":0, "presolveUse":"off"}}
    run_example('FatTreePartial', topo_params=topo_params, objective_function=objective_function, mosek_params=mosek_params)

    # Partial Fattree Linear function
    topo_params = {'switchRadix':32, 'numAgg': 4}
    objective_function = {'objfunc': 'linear'}
    mosek_params = {'mosek_params': {"optimizer":"freeSimplex", "numThreads":0, "presolveUse":"on"}}
    run_example('FatTreePartial', topo_params=topo_params, objective_function=objective_function, mosek_params=mosek_params)

    # FatClique Log function
    topo_params = {'numServerPerToR': 1, 'numLocalToR':3, 'numSubblock':3, 'numBlock':3}
    objective_function = {'objfunc': 'log'}
    mosek_params = {'mosek_params': {"optimizer":"conic", "numThreads":0, "presolveUse":"off"}}
    run_example('FatClique', topo_params=topo_params, objective_function=objective_function, mosek_params=mosek_params)

    # FatClique Linear function
    topo_params = {'numServerPerToR': 1, 'numLocalToR':3, 'numSubblock':3, 'numBlock':3}
    objective_function = {'objfunc': 'linear'}
    mosek_params = {'mosek_params': {"optimizer":"freeSimplex", "numThreads":0, "presolveUse":"on"}}
    run_example('FatClique', topo_params=topo_params, objective_function=objective_function, mosek_params=mosek_params)

    # DRing Log function
    topo_params = {'numServerPerToR': 10, 'numToRPerBlock':2, 'numBlock':6, 'linkCapacity':1}
    objective_function = {'objfunc': 'log'}
    mosek_params = {'mosek_params': {"optimizer":"conic", "numThreads":0, "presolveUse":"off"}}
    run_example('DRing', topo_params=topo_params, objective_function=objective_function, mosek_params=mosek_params)

    # DRing Linear function
    topo_params = {'numServerPerToR': 10, 'numToRPerBlock':2, 'numBlock':6, 'linkCapacity':1}
    objective_function = {'objfunc': 'linear'}
    mosek_params = {'mosek_params': {"optimizer":"freeSimplex", "numThreads":0, "presolveUse":"on"}}
    run_example('DRing', topo_params=topo_params, objective_function=objective_function, mosek_params=mosek_params)

    # DRing SU2 function
    topo_params = {'numServerPerToR': 10, 'numToRPerBlock':2, 'numBlock':6, 'linkCapacity':1}
    objective_function = {'objfunc': 'su2'}
    run_example('DRing', topo_params=topo_params, objective_function=objective_function)

    # DRing ECMP function
    topo_params = {'numServerPerToR': 10, 'numToRPerBlock':2, 'numBlock':6, 'linkCapacity':1}
    objective_function = {'objfunc': 'ecmp'}
    run_example('DRing', topo_params=topo_params, objective_function=objective_function)
    
    # DRingOriginal SU2 function
    topo_params = {'linkCapacity':1}
    objective_function = {'objfunc': 'su2'}
    run_example('DRingOriginal', topo_params=topo_params, objective_function=objective_function)
    '''