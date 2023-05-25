# Copyright (c) 2023 VISTEC - Vidyasirimedhi Institute of Science and Technology
# Distribute under MIT License
# Authors:
#  - Sucha Supittayapornpong <sucha.s[-at-]vistec.ac.th>
#  - Kanatip Chitavisutthivong <kanatip.c_s18[-at-]vistec.ac.th>

import networkx as nx
import pynauty
import itertools
import pickle
import time
import os
import multiprocessing as mp


import state_helper as helper
from state_helper import involve, applyGenerator, HCONST



class Topology:
    """
    Topology class 

    ...

    Attributes
    ----------
    Name : str
        a topology name 
    NumThread : int
        a number of thread
    UG : nx.Graph
        a undirecteed graph
    SwitchNodes : set
        a set of switch nodes
    ServerNodes : set
        a set of server nodes
    Commodities : set
        a set of commodities
    ULinks : set
        a set of undirected links
    DLinks : set
        a set of directed links
    Autgen : set
        a set of automorphic generators
    RepCommodities : set
        a set of representative commodities    
    RepCommFlows : set
        a set of representative flows of commodity    
    RepLinks : set
        a set of representative links         
    ComputationTime : dict
        store compupation times   
    """


    def __init__(self, ugraph, toponame, numThread=1):
        self.Name = toponame
        self.NumThread = numThread
        self.UG = None
        self.SwitchNodes = None
        self.ServerNodes = None
        self.Commodities = None
        self.ULinks = None
        self.DLinks = None
        self.Autgen = None
        self.RepCommodities = None
        self.RepCommFlows = None
        self.RepLinks = None
        self.ComputationTime = dict()

        print('-------------------------')
        print('Step: Topology Automorphism')
        print('-------------------------')
        
        rootdir = '.'
        self.setUGraph(ugraph)

        print('Find generators: ', end='')
        cnttime = time.time()
        self.findAutomorphicGenerators()
        cnttime = time.time() - cnttime
        print('{0:.2f}'.format(cnttime))
        self.ComputationTime['Find generators'] = cnttime
        
        print('Find representative commodities: ', end='')
        cnttime = time.time()
        self.findRepresentativeCommodities()
        cnttime = time.time() - cnttime
        print('{0:.2f}'.format(cnttime))
        self.ComputationTime['Find representative commodities'] = cnttime

        print('Find representative flows: ', end='')
        cnttime = time.time()
        self.findRepresentativeCommodityFlows()
        cnttime = time.time() - cnttime
        print('{0:.2f}'.format(cnttime))
        self.ComputationTime['Find representative flows'] = cnttime

        print('Find representative links: ', end='')
        cnttime = time.time()
        self.findRepresentativeLinks()
        cnttime = time.time() - cnttime
        print('{0:.2f}'.format(cnttime))
        self.ComputationTime['Find representative links'] = cnttime

        print('Precompute link constraint dependency: ', end='')
        cnttime = time.time()
        self.precomputeLinkCapacityConstraintDependency()
        cnttime = time.time() - cnttime
        print('{0:.2f}'.format(cnttime))
        self.ComputationTime['Precompute link constraint dependency'] = cnttime

        pickle.dump(self.ComputationTime, open(HCONST['outputdir'] + '/' + 'TopoComputationTime', 'wb'))
    
        
    def setUGraph(self, ugraph):
        stagepath = HCONST['stagedir'] + '/' + 'setUGraph'
        if os.path.exists(stagepath):
            (self.UG, self.SwitchNodes, self.ServerNodes, self.Commodities, self.ULinks, self.DLinks) = pickle.load(open(stagepath, 'rb'))
            return
        
        assert set(ugraph.nodes()) == set(range(ugraph.number_of_nodes()))
        self.UG = nx.Graph()
        for n in ugraph.nodes():
            numServer = ugraph.nodes[n]['numServer']
            self.UG.add_node(n, numServer=numServer)

        for e in ugraph.edges():
            capacity = ugraph.edges[e]['capacity']
            self.UG.add_edge(*e, capacity=capacity)

        self.SwitchNodes = set([n for n in self.UG.nodes() if self.UG.nodes[n]['numServer'] == 0])            
        self.ServerNodes = set([n for n in self.UG.nodes() if self.UG.nodes[n]['numServer'] > 0])
        self.Commodities = set(itertools.permutations(self.ServerNodes, 2))
        self.ULinks = set(self.UG.edges())
        self.DLinks = self.ULinks.union([(j, i) for (i, j) in self.ULinks])

        stagedata = (self.UG, self.SwitchNodes, self.ServerNodes, self.Commodities, self.ULinks, self.DLinks)
        pickle.dump(stagedata, open(stagepath, 'wb'))


    def findAutomorphicGenerators(self):
        stagepath = HCONST['stagedir'] + '/' + 'findAutomorphicGenerator'
        if os.path.exists(stagepath):
            (self.Autgen) = pickle.load(open(stagepath, 'rb'))
            return        
        
        nodecnt = 0
        colorgroup = dict()
        adj = dict()
        for n in self.UG.nodes():
            colorname = ('n', self.UG.nodes[n]['numServer'])
            if colorname not in colorgroup.keys():
                colorgroup[colorname] = set()
            colorgroup[colorname].add(n)
            nodecnt +=1

        augmap = dict() #edge-to-augvertex map
        raugmap = dict() #augvertex-to-edge map            
        for e in self.UG.edges():
            i, j = e
            colorname = ('c', self.UG.edges[e]['capacity'])
            if colorname not in colorgroup.keys():
                colorgroup[colorname] = set()
            augnode = nodecnt
            nodecnt += 1      
            colorgroup[colorname].add(augnode)
            augmap[e] = augnode
            raugmap[augnode] = e

            if i not in adj.keys():
                adj[i] = list()
            if j not in adj.keys():
                adj[j] = list()
            if augnode not in adj.keys():
                adj[augnode] = list()
            adj[i].append(augnode)
            adj[augnode].append(i)
            adj[j].append(augnode)
            adj[augnode].append(j)

        g = pynauty.Graph(number_of_vertices=nodecnt, adjacency_dict=adj, vertex_coloring=list(colorgroup.values()))
        (gens, _, _, _, _) = pynauty.autgrp(g)
        self.Autgen = set([tuple(g[0:self.UG.number_of_nodes()]) for g in gens])

        stagedata = (self.Autgen)
        pickle.dump(stagedata, open(stagepath, 'wb'))

        
    def findRepresentativeCommodities(self):
        stagepath = HCONST['stagedir'] + '/' + 'findRepresentativeCommodities'
        if os.path.exists(stagepath):
            (self.RepCommodities) = pickle.load(open(stagepath, 'rb'))
            return
        
        tovisit = set()        
        visited = set()
        repcomms = set()

        commodities = list(self.Commodities)
        commodities.sort()
        for repsd in commodities:
            if repsd in visited:
                continue
            repcomms.add(repsd)
            autcomms = set()
            self.saveCommodityAutomorphicMap(repsd, repsd, None)
            tovisit.add((repsd, repsd))
            while len(tovisit) > 0:
                (sd, parent) = tovisit.pop()
                autcomms.add(sd)
                visited.add(sd)
                for autmap in self.Autgen:
                    asd = applyGenerator(sd, autmap)
                    if asd in visited:
                        continue
                    self.saveCommodityAutomorphicMap(asd, sd, autmap)
                    tovisit.add((asd, sd))

            self.saveCommodityGroup(repsd, autcomms)
        self.RepCommodities = repcomms
        
        stagedata = (self.RepCommodities)
        pickle.dump(stagedata, open(stagepath, 'wb'))        
        

    def saveCommodityGroup(self, repsd, autcomms):
        fpath = HCONST['commdir'] + '/' + '{0}_{1}_CommodityGroup'.format(*repsd)
        pickle.dump(autcomms, open(fpath, 'wb'))

        
    def loadCommodityGroup(self, repsd):
        fpath = HCONST['commdir'] + '/' + '{0}_{1}_CommodityGroup'.format(*repsd)
        return pickle.load(open(fpath, 'rb'))


    def saveCommodityAutomorphicMap(self, sd, parent, autmap):        
        fpath = HCONST['commdir'] + '/' + '{0}_{1}_AutomorphicMap'.format(*sd)
        if sd == parent:
            fmap = tuple(range(self.UG.number_of_nodes()))
            pickle.dump(fmap, open(fpath + '_Forward', 'wb'))
            pickle.dump(fmap, open(fpath + '_Reverse', 'wb'))
        else:
            ppath = HCONST['commdir'] + '/' + '{0}_{1}_AutomorphicMap'.format(*parent)
            pmapfwd = pickle.load(open(ppath + '_Forward', 'rb'))
            fmap = applyGenerator(pmapfwd, autmap)
            rmap = [None]*len(fmap)
            for i in range(len(fmap)):
                rmap[fmap[i]] = i
            rmap = tuple(rmap)
            pickle.dump(fmap, open(fpath + '_Forward', 'wb'))
            pickle.dump(rmap, open(fpath + '_Reverse', 'wb'))


    def loadCommodityAutomorphicMap(self, sd, isForward=True):
        fpath = HCONST['commdir'] + '/' + '{0}_{1}_AutomorphicMap'.format(*sd)
        if isForward:
            return pickle.load(open(fpath + '_Forward', 'rb'))
        else:
            return pickle.load(open(fpath + '_Reverse', 'rb'))


    def findRepresentativeCommodityFlows(self):
        stagepath = HCONST['stagedir'] + '/' + 'findRepresentativeCommodityFlows'
        if os.path.exists(stagepath):
            (self.RepCommFlows) = pickle.load(open(stagepath, 'rb'))
            return

        self.RepCommFlows = dict()
        pool = mp.Pool(self.NumThread)
        for repsd, repflows in pool.imap_unordered(self.findRepresentativeCommodityFlowsByCommodity, self.RepCommodities):
            self.RepCommFlows[repsd] = repflows
        pool.close()
        pool.join()
        stagedata = (self.RepCommFlows)
        pickle.dump(stagedata, open(stagepath, 'wb'))                
    

    def findRepresentativeCommodityFlowsByCommodity(self, repsd):
        autgen = set()
        for autmap in self.Autgen:
            if involve(repsd[0], autmap) or involve(repsd[1], autmap):
                continue
            autgen.add(autmap)

        tovisit = set()
        visited = set()
        repflows = set()
        flowmap = dict()

        links = list(self.DLinks)
        links.sort()
        for canlink in links:
            if canlink in visited:
                continue
            repflows.add(canlink)
            flowmap[canlink] = canlink
            tovisit.add(canlink)
            while len(tovisit) > 0:
                link = tovisit.pop()
                visited.add(link)
                for autmap in autgen:
                    alink = applyGenerator(link, autmap)
                    if alink in visited:
                        continue
                    flowmap[alink] = flowmap[link]
                    tovisit.add(alink)
        self.saveCommodityFlowMap(repsd, flowmap)
        return (repsd, repflows)


    def saveCommodityFlowMap(self, repsd, flowmap):
        fpath = HCONST['flowdir'] + '/' + '{0}_{1}_FlowMap'.format(*repsd)
        pickle.dump(flowmap, open(fpath, 'wb'))


    def loadCommodityFlowMap(self, repsd):
        fpath = HCONST['flowdir'] + '/' + '{0}_{1}_FlowMap'.format(*repsd)
        return pickle.load(open(fpath, 'rb'))


    def findRepresentativeLinks(self):
        stagepath = HCONST['stagedir'] + '/' + 'findRepresentativeLinks'
        if os.path.exists(stagepath):
            (self.RepLinks) = pickle.load(open(stagepath, 'rb'))
            return

        self.RepLinks = set()
        links = list(self.DLinks)
        links.sort()
        dephash = dict()
        pool = mp.Pool(self.NumThread)
        for (canlink, flowtmmap) in pool.imap_unordered(self.calculateRepresentativeFlow, links):
            linkcapacity = self.UG.get_edge_data(*canlink)['capacity']
            depkey = list()
            for repsd in self.RepCommodities:
                for repflow in self.RepCommFlows[repsd]:
                    if (repsd, repflow) in flowtmmap.keys():
                        v = len(flowtmmap[repsd, repflow])
                    else:
                        v = 0
                    depkey.append(v)
            depkey.append(linkcapacity)
            depkey = tuple(depkey)
            if depkey not in dephash:
                dephash[depkey] = list()
            dephash[depkey].append(canlink)
        pool.close()
        pool.join()

        for depkey, links in dephash.items():
            links.sort()
            self.RepLinks.add(links[0])

        stagedata = (self.RepLinks)
        pickle.dump(stagedata, open(stagepath, 'wb'))
        

    def calculateRepresentativeFlow(self, link):
        flowtmmap = dict()
        for repsd in self.RepCommodities:
            autcomms = self.loadCommodityGroup(repsd) 
            flowmap = self.loadCommodityFlowMap(repsd) 
            for sd in autcomms:
                rmap = self.loadCommodityAutomorphicMap(sd, isForward=False)
                assert repsd == helper.applyGenerator(sd, rmap)
                alink = helper.applyGenerator(link, rmap)
                repflowlink = flowmap[alink]
                if (repsd, repflowlink) not in flowtmmap:
                    flowtmmap[repsd, repflowlink] = list()
                flowtmmap[repsd, repflowlink].append(sd)
        for (repsd, repflowlink) in flowtmmap.keys():
            flowtmmap[repsd, repflowlink].sort()
            flowtmmap[repsd, repflowlink] = tuple(flowtmmap[repsd, repflowlink])
        
        return link, flowtmmap    


    def precomputeLinkCapacityConstraintDependency(self):
        stagepath = HCONST['stagedir'] + '/' + 'precomputeLinkCapacityConstraintDependency'
        if os.path.exists(stagepath):
            return
        
        pool = mp.Pool(self.NumThread)
        for link, flowtmmap in pool.imap_unordered(self.calculateRepresentativeFlow, self.RepLinks):
            self.saveLinkCapacityDependency(link, flowtmmap)

        stagedata = (None)
        pickle.dump(stagedata, open(stagepath, 'wb'))


    def saveLinkCapacityDependency(self, replink, flowtmmap):
        fpath = HCONST['linkdir'] + '/' + '{0}_{1}_LinkCapacityConstraintMap'.format(*replink)
        pickle.dump(flowtmmap, open(fpath, 'wb'))


    def loadLinkCapacityDependency(self, replink):
        fpath = HCONST['linkdir'] + '/' + '{0}_{1}_LinkCapacityConstraintMap'.format(*replink)
        return pickle.load(open(fpath, 'rb'))


    def getMinimalAllToAllTrafficMatrix(self):
        minNumServer = min(self.UG.nodes[n]['numServer'] for n in self.ServerNodes)
        tm = dict()
        for sd in self.Commodities:
            tm[sd] = minNumServer/(len(self.ServerNodes) - 1)
        return tm


    def getNearWorstCaseTrafficMatrix(self):
        numServerSwitch = len(self.ServerNodes)
        BG = nx.complete_bipartite_graph(numServerSwitch, numServerSwitch)
        for repsd in self.RepCommodities:
            src, dst = repsd
            numServer = min(self.UG.nodes[src]['numServer'], self.UG.nodes[dst]['numServer'])
            plen = len(nx.algorithms.shortest_paths.generic.shortest_path(self.UG, source=src, target=dst)) - 1
            autcomms = self.loadCommodityGroup(repsd)
            for asd in autcomms:
                u, v = asd[0], numServerSwitch + asd[1]
                BG[u][v]['weight'] = plen * numServer

        matching = nx.algorithms.matching.max_weight_matching(BG)
        tm = dict()
        for sd in matching:
            if sd[0] < sd[1]:
                u, v = sd[0], sd[1] - numServerSwitch
            else:
                u, v = sd[1], sd[0] - numServerSwitch
            minServer = min(self.UG.nodes[u]['numServer'], self.UG.nodes[v]['numServer'])
            tm[u,v] = minServer
        return tm
        
