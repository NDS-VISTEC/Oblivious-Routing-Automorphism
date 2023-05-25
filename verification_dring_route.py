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


class VerificationDRing:
    """
    Class Verification for verify the DRing routing 

    ...

    Attributes
    ----------
    toponame : str
        a topology name 
    numThread : int
        a number of thread (default 1)
    Route_mode : str
        Route mode (ECMP or SU2)
    Topo : Topology
        Topology object
    Route : dict
        a solution route

    """

    def __init__(self, toponame, numThread=1, Route_mode='ecmp'):
        self.toponame = toponame
        self.numThread = numThread
        self.Route_mode = Route_mode

        rootdir = '.'
        helper.initHCONST(rootdir, toponame, Route_mode)
        self.Topo = pickle.load(open(HCONST['outputdir'] + '/' + 'Topology', 'rb'))
        self.buildMappingSdToIdx()

        if Route_mode == 'su2':
            if not os.path.exists(HCONST['outputdir'] + '/' + 'SU2Routing'):
                print("Shortest-Union(2) solution does not exist")
            else:
                self.SU2Route = pickle.load(open(HCONST['outputdir'] + '/' + 'SU2Routing', 'rb'))
            self.Route = self.SU2Route
        elif Route_mode == 'ecmp':
            if not os.path.exists(HCONST['outputdir'] + '/' + 'ECMPRouting'):
                print("ECMP solution does not exist")
            else:
                self.ECMPRoute = pickle.load(open(HCONST['outputdir'] + '/' + 'ECMPRouting', 'rb'))
            self.Route = self.ECMPRoute
        elif Route_mode == 'linear':
            if not os.path.exists(HCONST['outputdir'] + '/' + 'OptimalRouting'):
                print("Optimal solution does not exist")
            else:
                self.ECMPRoute = pickle.load(open(HCONST['outputdir'] + '/' + 'OptimalRouting', 'rb'))
            self.Route = self.ECMPRoute
        else:
            print("Incorrect Route mode")
    
        
    def verifyAllLinkLoad(self):

        print('-------------------------')
        print('Step: Solution Verification')
        print('-------------------------')

        if os.path.exists(HCONST['outputdir'] + '/' + 'VerifiedThroughput_'+ self.Route_mode):
            verifiedThroughput = pickle.load(open(HCONST['outputdir'] + '/' + 'VerifiedThroughput_'+ self.Route_mode, 'rb'))
            print('\t Verified: Max link load =', 1.0/verifiedThroughput)
            print('\t Verified: Throughput =', verifiedThroughput)
            return

        pool = mp.Pool(self.numThread)
        linkload = dict()
        for link, maxload in pool.imap_unordered(self.findMaxLinkLoad, self.Topo.DLinks):
            linkload[link] = maxload/self.Topo.UG.get_edge_data(*link)['capacity']
        
        maxload = max(linkload.values())
        verifiedThroughput = 1.0/maxload
        pickle.dump(verifiedThroughput, open(HCONST['outputdir'] + '/' + 'VerifiedThroughput_'+ self.Route_mode, 'wb'))
        print('\t Verified: Max link load =', maxload)
        print('\t Verified: Throughput =', verifiedThroughput)            
            
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
        flow_link = Route.get_edge_data(*link)
        flow_link_keys = flow_link.keys()
        for sd in Topo.Commodities:
            if sd in flow_link_keys:
                load_Lst.append(Expr.mul(p.index(self.mappingSdToIdx[sd]).reshape(1), flow_link[sd])) 
        load = Expr.add(load_Lst)

        M.objective("obj", ObjectiveSense.Maximize, load)
        M.solve()
        M.acceptedSolutionStatus(AccSolutionStatus.Feasible)

        return (link, M.primalObjValue())