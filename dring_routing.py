# Copyright (c) 2023 VISTEC - Vidyasirimedhi Institute of Science and Technology
# Distribute under MIT License
# Authors:
#  - Sucha Supittayapornpong <sucha.s[-at-]vistec.ac.th>
#  - Kanatip Chitavisutthivong <kanatip.c_s18[-at-]vistec.ac.th>

import pickle
import networkx as nx
from network_generator import *
from topology_automorphism import Topology
import state_helper as helper
from state_helper import HCONST, initHCONST

import os
from itertools import islice
import multiprocessing as mp

class DRingRouting:
    """
    Class DRingRouting for generating DRing's route based on 

    V. Harsh, S. A. Jyothi, and P. B. Godfrey, “Spineless data centers,” in Proceedings of the 19th ACM Workshop on Hot Topics in Networks, ser. HotNets '20. New York, NY, USA: Association for Computing Machinery, 2020, pp. 6

    ...

    Attributes
    ----------
    Topo : Topology
        Topology object 
    numToRPerBlock : int
        a number of ToR per Block
    Route : dict
        DRing route
    Route_mode : str
        route mode (ShortestUnion2 or ECMP)
    """

    def __init__(self, G, topo, numToRPerBlock, Route_mode='ShortestUnion2'):

        print('-------------------------')
        print('Step: Generate DRing routing')
        print('-------------------------')

        self.Topo = topo
        self.numToRPerBlock = numToRPerBlock
        self.H = G.to_directed()
        self.ECMPRoute = None
        self.SU2Route = None

        rootdir = '.'
        pickle.dump(self.Topo, open(HCONST['outputdir'] + '/' + 'Topology', 'wb'))

        if Route_mode == 'ShortestUnion2':
            if not os.path.exists(HCONST['outputdir'] + '/' + 'SU2Routing'):
                print("\t Shortest-Union(2) solution does not exist!")
                self.generateSU2Route()
            else:
                self.SU2Route = pickle.load(open(HCONST['outputdir'] + '/' + 'SU2Routing', 'rb'))
            self.Route = self.SU2Route
        elif Route_mode == 'ECMP':
            if not os.path.exists(HCONST['outputdir'] + '/' + 'ECMPRouting'):
                print("\t ECMP solution does not exist!")
                self.generateECMPRoute()
            else:
                self.ECMPRoute = pickle.load(open(HCONST['outputdir'] + '/' + 'ECMPRouting', 'rb'))
            self.Route = self.ECMPRoute
        else:
            print("\t Incorrect Route mode")
            return 

    
    def getShortestPaths(self, src, dst):
        paths = nx.all_shortest_paths(self.H, source=src, target=dst)
        return paths


    def toEdgesPath(self, path):
        paths = list()
        for i in range(len(path)-1):
            nodeA = path[i]
            nodeB = path[i+1]
            paths.append((nodeA,nodeB))
        return paths


    def getECMPpaths(self, src, dst):
        paths = self.getShortestPaths(src, dst)
        return paths


    def testECMPpaths(self, src, dst):
        paths = self.getECMPpaths(src, dst)
        for p in paths:
            print(p)
            print(self.toEdgesPath(p))
            print('------')
    

    def generateECMPRoute(self):
        ECMPRoute = dict()
        for sd in self.Topo.Commodities:
            ECMPRoute[sd] = dict()
            src, dst = sd
            paths = list(self.getECMPpaths(src, dst))
            flow = 1.0/len(paths)
            for p in paths:
                p = self.toEdgesPath(p)
                for edge in p:
                    if edge in ECMPRoute[sd]:
                        ECMPRoute[sd][edge] += flow
                    else:
                        ECMPRoute[sd][edge] = flow

        g = nx.DiGraph()
        for node in self.Topo.UG.nodes():
            g.add_node(node)
        for i, j in self.Topo.UG.edges():
            g.add_edge(i, j)
            g.add_edge(j, i)
            for sd in self.Topo.Commodities:
                route_sd = ECMPRoute[sd]
                flowij = 0
                flowji = 0
                if (i, j) in route_sd:
                    flowij = ECMPRoute[sd][(i, j)]
                if (j, i) in route_sd:
                    flowji = ECMPRoute[sd][(j, i)]

                if flowij > 0:
                    g[i][j][sd] = flowij
                if flowji > 0:
                    g[j][i][sd] = flowji

        pickle.dump(g, open(HCONST['outputdir'] + '/' + 'ECMPRouting', 'wb'))


    def getKShortestPaths(self, src, dst, k):
        return list(islice(nx.shortest_simple_paths(self.H, src, dst), k))


    def getShortestUnion2paths(self, src, dst):
        K = 2 # path_length_edge
        all_shortest_paths = list(self.getECMPpaths(src, dst))
        num_of_all_shortest_paths = len(all_shortest_paths[0])
        if num_of_all_shortest_paths <= 2: # Is exists directed link?
            paths = list()
            # Retrieve almost_shortest_paths instead 
            almost_shortest_paths = self.getKShortestPaths(src, dst, 1+(self.numToRPerBlock*2))
            # Select only a path with its length <= K (path_length_edge)
            for path in almost_shortest_paths:
                path_length_node = len(path)
                if path_length_node <= K+1:
                    paths.append(path)
            return paths
        return all_shortest_paths
    

    def testShortestUnion2paths(self, src, dst):
        paths = self.getShortestUnion2paths(src, dst)
        for p in paths:
            print(p)
            print(self.toEdgesPath(p))
            print('------')


    def generateSU2Route(self):
        SU2Route = dict()
        for sd in self.Topo.Commodities:
            SU2Route[sd] = dict()
            src, dst = sd
            paths = list(self.getShortestUnion2paths(src, dst))
            flow = 1.0/len(paths)
            for p in paths:
                p = self.toEdgesPath(p)
                for edge in p:
                    if edge in SU2Route[sd]:
                        SU2Route[sd][edge] += flow
                    else:
                        SU2Route[sd][edge] = flow

        g = nx.DiGraph()
        for node in self.Topo.UG.nodes():
            g.add_node(node)
        for i, j in self.Topo.UG.edges():
            g.add_edge(i, j)
            g.add_edge(j, i)
            for sd in self.Topo.Commodities:
                route_sd = SU2Route[sd]
                flowij = 0
                flowji = 0
                if (i, j) in route_sd:
                    flowij = SU2Route[sd][(i, j)]
                if (j, i) in route_sd:
                    flowji = SU2Route[sd][(j, i)]

                if flowij > 0:
                    g[i][j][sd] = flowij
                if flowji > 0:
                    g[j][i][sd] = flowji

        pickle.dump(g, open(HCONST['outputdir'] + '/' + 'SU2Routing', 'wb'))


