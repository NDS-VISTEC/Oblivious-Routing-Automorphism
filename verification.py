# Copyright (c) 2023 VISTEC - Vidyasirimedhi Institute of Science and Technology
# Distribute under MIT License
# Authors:
#  - Sucha Supittayapornpong <sucha.s[-at-]vistec.ac.th>
#  - Kanatip Chitavisutthivong <kanatip.c_s18[-at-]vistec.ac.th>

import os
import pickle
import networkx as nx
import multiprocessing as mp

import state_helper as helper
from state_helper import HCONST
from mosek.fusion import *


class Verification:
    """
    Class Verification for verify the optimal solution from Optimization process

    ...

    Attributes
    ----------
    toponame : str
        a topology name 
    numThread : int
        a number of thread (default 1)
    objfunc : str
        Objective function (default linear)
    Topo : Topology
        Topology object
    Route : dict
        a solution route

    """

    def __init__(self, toponame, numThread=1, objfunc='linear', intermediate=False):
        self.toponame = toponame
        self.numThread = numThread
        self.intermediate = intermediate

        rootdir = '.'
        helper.initHCONST(rootdir, toponame, objfunc)
        self.Topo = pickle.load(open(HCONST['outputdir'] + '/' + 'Topology', 'rb'))

        if self.intermediate is False:
            self.Route = pickle.load(open(HCONST['outputdir'] + '/' + 'OptimalRouting', 'rb'))
        else:
            self.Route = pickle.load(open(HCONST['outputdir'] + '/' + 'IntermediateSolution', 'rb'))

        self.buildMappingSdToIdx()

        
    def verifyAllLinkLoad(self):

        print('-------------------------')
        print('Step: Solution Verification')
        print('-------------------------')

        if os.path.exists(HCONST['outputdir'] + '/' + 'VerifiedThroughput'):
            verifiedThroughput = pickle.load(open(HCONST['outputdir'] + '/' + 'VerifiedThroughput', 'rb'))
            print('\t Verified: Max link load =', 1.0/verifiedThroughput)
            print('\t Verified: Throughput =', verifiedThroughput)
            return

        pool = mp.Pool(self.numThread)
        linkload = dict()
        for link, maxload in pool.imap_unordered(self.findMaxLinkLoad, self.Topo.DLinks):
            linkload[link] = maxload/self.Topo.UG.get_edge_data(*link)['capacity']
        
        maxload = max(linkload.values())
        verifiedThroughput = 1.0/maxload
        if self.intermediate is False:
            pickle.dump(verifiedThroughput, open(HCONST['outputdir'] + '/' + 'VerifiedThroughput', 'wb'))
            print('\t Verified: Max link load =', maxload)
            print('\t Verified: Throughput =', verifiedThroughput)            
        else:
            pickle.dump(verifiedThroughput, open(HCONST['outputdir'] + '/' + 'VerifiedIntermediateThroughput', 'wb'))
            print('\t Verified Intermediate: Max link load =', maxload)
            print('\t Verified Intermediate: Throughput =', verifiedThroughput)
            
        return linkload


    def buildMappingSdToIdx(self):
        self.mappingSdToIdx = dict()
        idx = 0
        for sd in self.Topo.Commodities:
            self.mappingSdToIdx[sd] = idx
            idx += 1


    def findMaxLinkLoad(self, link):

        Topo = self.Topo
        Route = self.Route

        M = Model()
        p = M.variable('p', len(Topo.Commodities), Domain.greaterThan(0.0))

        for n in Topo.ServerNodes:
            numServer = Topo.UG.nodes[n]['numServer']

            idx_comms_from_n = [p.index(self.mappingSdToIdx[k]).reshape(1) for k in self.mappingSdToIdx.keys() if k[0] == n]
            flow_out = Expr.add(idx_comms_from_n)
            M.constraint(Expr.sub(flow_out, numServer), Domain.lessThan(0.0))   

            idx_comms_to_n = [p.index(self.mappingSdToIdx[k]).reshape(1) for k in self.mappingSdToIdx.keys() if k[1] == n]
            flow_in = Expr.add(idx_comms_to_n)
            M.constraint(Expr.sub(flow_in, numServer), Domain.lessThan(0.0))  

        load_Lst = []
        for repsd in Topo.RepCommodities:
            autcomms = Topo.loadCommodityGroup(repsd)
            for sd in autcomms:
                rmap = Topo.loadCommodityAutomorphicMap(sd, isForward=False)
                alink = helper.applyGenerator(link, rmap)
                if repsd in Route.get_edge_data(*alink).keys():
                    load_Lst.append(Expr.mul(p.index(self.mappingSdToIdx[sd]).reshape(1), Route.get_edge_data(*alink)[repsd])) 
        load = Expr.add(load_Lst)

        M.objective("obj", ObjectiveSense.Maximize, load)
        M.solve()
        M.acceptedSolutionStatus(AccSolutionStatus.Feasible)

        return (link, M.primalObjValue())