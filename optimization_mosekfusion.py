# Copyright (c) 2023 VISTEC - Vidyasirimedhi Institute of Science and Technology
# Distribute under MIT License
# Authors:
#  - Sucha Supittayapornpong <sucha.s[-at-]vistec.ac.th>
#  - Kanatip Chitavisutthivong <kanatip.c_s18[-at-]vistec.ac.th>

import time
import pickle
import networkx as nx
import os

import state_helper as helper
from state_helper import HCONST

import numpy as np
import mosek
import gc
import multiprocessing as mp

from mosek.fusion import *
import modelLib as mlib
import sys


def compute_sd_intersect(element, tm_keys):
    (repsd, replink), autcomms = element
    sd_list = list()
    for sd in autcomms:
        if sd in tm_keys:
            sd_list.append(sd)
    return ((repsd, replink), sd_list)

class OptimizationCVX_MOSEK:

    """
    Class OptimizationCVX_MOSEK

    ...

    Attributes
    ----------
    Name : str
        a class name
    NumLPThread : int
        a number of thread
    Topo : Topology
        Topology object
    M : Mosek.Model
        optimization model
    Theta : Mosek.Variable
        minimum throughput variable
    F : dict
        flow variables
    S : dict
        throughput of commodity variable
    LinkConstrs : dict
        link constraints
    LinkViolationTolerance: float
        link violation tolerance
    """


    def __init__(self, topology, numLPThread=1, objfunc='linear', mosek_params={}):
        print('-------------------------')
        print('Step: Optimization')
        print('-------------------------')
        
        self.LinkViolationTolerance = 1e-6
        self.Name = 'Optimization-' + topology.Name + '-' + str(objfunc)
        self.NumLPThread = numLPThread

        self.Topo = topology
        self.M = None
        self.S = None
        self.F = None
        self.Theta = None
        self.LinkConstrs = dict((replink, set()) for replink in self.Topo.RepLinks)

        self.objfunc = objfunc
        self.mosek_params = mosek_params

        rootdir = '.'
        helper.makeOutputDataDirectory(rootdir, self.Topo.Name+'-' + str(objfunc))
        parameters = (self.Name, self.NumLPThread, self.LinkViolationTolerance)
        pickle.dump(parameters, open(HCONST['outputdir'] + '/' + 'Parameters', 'wb'))
        pickle.dump(self.Topo, open(HCONST['outputdir'] + '/' + 'Topology', 'wb'))


    def buildMappingSdToIdx(self):
        self.mappingSdToIdx = dict()
        idx = 0
        for repsd in self.Topo.RepCommodities:
            self.mappingSdToIdx[repsd] = idx
            idx += 1


    def debug(self, canobj):
        S = self.S

        print("--- Obj value: ", canobj)
        print("\t Theta: ", self.Theta.level()[0])
        print("--- Theta_hat_uv")
        s = dict()
        for repsd in self.Topo.RepCommodities:
            autcomms = self.Topo.loadCommodityGroup(repsd)
            S_value = S.index(self.mappingSdToIdx[repsd]).level()[0]
            print('\t  s_{0}_{1}'.format(repsd[0], repsd[1]), " ", S_value, " size: ", len(autcomms))
            s[repsd] = (S_value, len(autcomms))
        numCommodities = 0
        totthroughput = 0
        totthroughputSq = 0
        for repsd in self.Topo.RepCommodities:
            autcomms = self.Topo.loadCommodityGroup(repsd)
            S_value = S.index(self.mappingSdToIdx[repsd]).level()[0]
            totthroughput += len(autcomms)*S_value
            numCommodities += len(autcomms)
            totthroughputSq += len(autcomms)*S_value*S_value
        print("--- Total throughput (Efficiency): ", totthroughput)
        fairness = ((totthroughput*totthroughput)/numCommodities)/totthroughputSq
        print("--- Jain's fairness index: ", fairness)

        return s, totthroughput, fairness

    def optimize(self):

        if os.path.exists(HCONST['outputdir'] + '/' + 'OptimalRouting'):
            print("\t Existing optimal solution is available.")
            return

        overallOptTime = time.time()
        overallOptTime_solve = 0 # overall MOSEK solve time 
        iterationTimes = dict()

        self.initialModel()
        self.createVariables()
        self.setObjective()
        self.setVariableConstraint()
        self.setThroughputConstraint()
        self.setFlowConservationConstraint()
        
        cntiter = 0
        maxviolation = float('inf')

        existIntermediateResult = False
        while os.path.exists(HCONST['intmeddir'] + '/' + 'iteration_{0}'.format(cntiter)):
            existIntermediateResult = True
            (_, _, throughput, tmlinks) = self.loadIntermediateResult(cntiter)
            constrs = self.addLinkCapacityConstraint(tmlinks, cntiter)
            print('\t {0}: Load intermediate result'.format(cntiter))
            cntiter += 1
            gc.collect()
        if existIntermediateResult:
            self.computeCandidateSolution()

        while maxviolation > self.LinkViolationTolerance:
            singleIterationTime = time.time()
            # Start Traffic Matrix
            tmtime = time.time()            
            if cntiter == 0:             
                inittm = self.Topo.getNearWorstCaseTrafficMatrix()
                tmlinks = [(inittm, replink) for replink in self.Topo.RepLinks]
                tmtime_solve = 0
            else:
                tmlinks, maxviolation, tmtime_solve = self.findWorstcaseTrafficMatrix()
            tmtime = time.time() - tmtime
            # End Traffic Matrix
            gc.collect()

            constrs = self.addLinkCapacityConstraint(tmlinks, cntiter)
            for (tm, replink), constr in zip(tmlinks, constrs):
                self.LinkConstrs[replink].add((tuple(tm.items()), constr))

            # Start Optimize
            opttime = time.time()
            solve_time, throughput, canobj = self.computeCandidateSolution()
            solve_time = self.M.getSolverDoubleInfo("optimizerTime")
            overallOptTime_solve += solve_time
            opttime = time.time() - opttime
            # End Optimize      
            gc.collect()

            singleIterationTime = time.time() - singleIterationTime
            iterationTimes[cntiter] = (singleIterationTime, maxviolation, throughput, canobj, opttime, tmtime, solve_time, tmtime_solve)
            print('\t {0}: Throughput = {1:.5}, OptSolveTime = {2:.2f}, Opttime = {3:.2f}, TMSolveTime = {4:.2f}, TMtime = {5:.2f}, MaxVio = {6:.10f}'.format(cntiter, throughput, solve_time, opttime, tmtime_solve, tmtime, maxviolation))
            self.saveIntermediateResult(cntiter, tmlinks, throughput)
            cntiter += 1

        s, totthroughput, fairness = self.debug(canobj)
        pickle.dump((s, totthroughput, fairness), open(HCONST['outputdir'] + '/' + 'Fairness', 'wb'))
        overallOptTime = time.time() - overallOptTime
        print('\t overallOptTime: ', overallOptTime)
        print('\t Solve overallOptTime: ', overallOptTime_solve)
        pickle.dump((overallOptTime, iterationTimes, overallOptTime_solve), open(HCONST['outputdir'] + '/' + 'OptimizationTime', 'wb'))
        self.saveOptimalRouting()


    def initialModel(self):
        M = Model()
        for key in self.mosek_params["mosek_params"]:
            M.setSolverParam(key, self.mosek_params["mosek_params"][key])
        # Show MOSEK log
        # M.setLogHandler(sys.stdout)
        self.M = M


    def createVariables(self):
        Topo = self.Topo
        M = self.M
        
        # lb = 0
        Theta = M.variable('theta', 1, Domain.greaterThan(0.0))
        self.Theta = Theta

        # S[repsd]
        # lb=0, ub=MaxThroughput = 1
        self.buildMappingSdToIdx()
        S = M.variable('s', len(Topo.RepCommodities), Domain.greaterThan(0.0))
        self.S = S

        # F[repsd][repflow]
        # lb=0, ub=MaxThroughput = 1
        F = dict()
        for repsd in Topo.RepCommodities:
            F[repsd] = dict()
            for repflow in Topo.RepCommFlows[repsd]:
                linkcap = Topo.UG.get_edge_data(*repflow)['capacity']
                F[repsd][repflow] = M.variable('f_{0}_{1}_{2}_{3}'.format(repsd[0], repsd[1], repflow[0], repflow[1]),1, Domain.greaterThan(0.0))
        self.F = F


    def setObjective(self):
        Topo = self.Topo        
        Theta = self.Theta
        S = self.S
        F = self.F
        objfunc = self.objfunc
        M = self.M

        MAX_THROUGHPUT = 10
        TOT_COMMODITY = len(Topo.Commodities)
        totthroughput_Lst = list()
        t = M.variable('t', len(Topo.RepCommodities))
        autcomms_sizes = [float(len(Topo.loadCommodityGroup(repsd))) for repsd in Topo.RepCommodities]

        if objfunc.lower() == 'linear':
            totthroughput = Expr.dot(S, autcomms_sizes)
        elif objfunc.lower() == 'log':
            # mlib.log(M, t, S)
            M.constraint(Expr.hstack(S, Expr.constTerm(len(Topo.RepCommodities), 1) , t), Domain.inPExpCone())
            totthroughput = Expr.dot(t, autcomms_sizes)
        else:
            totthroughput = Expr.dot(S, autcomms_sizes)

        MAX_TOT_FLOW = sum(Topo.UG.get_edge_data(*repflow)['capacity'] for repsd in Topo.RepCommodities for repflow in Topo.RepCommFlows[repsd]) * 2
        totflow_Lst = [F[repsd][repflow] for repsd in Topo.RepCommodities for repflow in Topo.RepCommFlows[repsd]]
        totflow = Expr.add(totflow_Lst)

        if objfunc.lower() == 'linear':
            # ((Theta*MAX_THROUGHPUT*TOT_COMMODITY) + totthroughput)*MAX_TOT_FLOW - totflow
            objexpr =  Expr.sub(Expr.mul(Expr.add(Expr.mul(MAX_THROUGHPUT*TOT_COMMODITY, Theta), totthroughput), MAX_TOT_FLOW), totflow)
        elif objfunc.lower() == 'log':
            objexpr = totthroughput
        else:
            objexpr =  Expr.sub(Expr.mul(Expr.add(Expr.mul(MAX_THROUGHPUT*TOT_COMMODITY, Theta), totthroughput), MAX_TOT_FLOW), totflow)
        M.objective("obj", ObjectiveSense.Maximize, objexpr)


    def setVariableConstraint(self):
        Topo = self.Topo        
        Theta = self.Theta
        S = self.S
        F = self.F
        M = self.M

        MaxThroughput = 1
        M.constraint(S, Domain.lessThan(MaxThroughput))
            
        for repsd in Topo.RepCommodities:
            for repflow in Topo.RepCommFlows[repsd]:
                M.constraint(F[repsd][repflow], Domain.lessThan(1))       


    def setThroughputConstraint(self):
        Topo = self.Topo        
        Theta = self.Theta
        S = self.S
        M = self.M

        Theta_lst = Expr.vstack([Theta]*len(Topo.RepCommodities))
        M.constraint(Expr.sub(S, Theta_lst), Domain.greaterThan(0))     
    

    def setFlowConservationConstraint(self):
        Topo = self.Topo        
        S = self.S
        F = self.F
        M = self.M

        for repsd in Topo.RepCommodities:
            s, d = repsd
            flowmap = Topo.loadCommodityFlowMap(repsd)
            nodes = Topo.SwitchNodes.union(Topo.ServerNodes)
            for n in nodes:
                flowin_Lst = [F[repsd][flowmap[h, n]] for h in Topo.UG.neighbors(n)]
                if n == s :
                    flowin_Lst.append(S.index(self.mappingSdToIdx[repsd]).reshape(1))
                flowout_Lst = [F[repsd][flowmap[n, h]] for h in Topo.UG.neighbors(n)]
                if n == d :
                    flowout_Lst.append(S.index(self.mappingSdToIdx[repsd]).reshape(1))
                flowin = Expr.add(flowin_Lst)
                flowout = Expr.add(flowout_Lst)
                # flowin == flowput
                M.constraint(Expr.sub(flowin,flowout), Domain.equalsTo(0.0))       


    def addLinkCapacityConstraint(self, tmlinks, iterindex):
        Topo = self.Topo
        F = self.F
        M = self.M

        constrs = list()
        for tm, replink in tmlinks:
            tm_keys = set(tm.keys())
            capacity = Topo.UG.get_edge_data(*replink)['capacity']
            load = 0
            flowtmmap = Topo.loadLinkCapacityDependency(replink)

            if len(tm_keys) <= 10240:
                load_Lst = list()
                for (repsd, replink), autcomms in flowtmmap.items():
                    for sd in autcomms:
                        if sd in tm.keys():
                            load_Lst.append(Expr.mul(F[repsd][replink],tm[sd]))

                load = Expr.add(load_Lst)
                # load <= capacity
                M.constraint(load, Domain.lessThan(capacity))

            else :
                # Optimize code for efficiency, parallel building MOSEK fusion expression 
                pool = mp.Pool(processes=mp.cpu_count())
                args = list()
                for element in flowtmmap.items():
                    args.append((element, tm_keys))
                sd_intersect = pool.starmap(compute_sd_intersect, args)
                load_Lst = list()
                for (repsd, replink), sd_list in sd_intersect:
                    load_ = list()
                    for sd in sd_list:
                        load_.append(Expr.mul(F[repsd][replink],tm[sd]))
                    load_Lst.extend(load_)
        
                load = Expr.add(load_Lst)
                M.constraint(load, Domain.lessThan(capacity))

        return constrs


    def computeCandidateSolution(self):
        M = self.M
        mosek_params = self.mosek_params
        M.solve()
        M.acceptedSolutionStatus(AccSolutionStatus.Feasible)

        solve_time = 0
        return solve_time, self.Theta.level()[0], M.primalObjValue()
    

    def findWorstcaseTrafficMatrix(self):
        Topo = self.Topo
        
        tmlinks = list()
        maxviolation = 0
        tmtime = 0
        for replink in Topo.RepLinks:
            newtm, violation, solve_time = self.findWorstcaseTrafficMatrixAtRepLink(replink)
            tmtime += solve_time
            maxviolation = max(maxviolation, violation)
            if newtm != None:
                tmlinks.append((newtm, replink))

        return tmlinks, maxviolation, tmtime


    def findWorstcaseTrafficMatrixAtRepLink(self, replink):
        Topo = self.Topo
        F = self.F

        with Model() as c:
            mosek_params = {"optimizer":"freeSimplex", "numThreads":1, "presolveUse":"off"}
            for key in mosek_params:
                c.setSolverParam(key, mosek_params[key])

            t = dict()
            load = list()
            flowtmmap = Topo.loadLinkCapacityDependency(replink)
            tfMappingSdToIdx = dict()
            minServer_lst = list()
            idx = 0
            flowval_lst = list()

            for (repsd, replink), autcomms in flowtmmap.items():
                flowval = F[repsd][replink].level()[0]
                if flowval == 0:
                    continue
                for s, d in autcomms:
                    minServer = min(Topo.UG.nodes[s]['numServer'], Topo.UG.nodes[d]['numServer'])
                    minServer_lst.append(minServer)
                    tfMappingSdToIdx[s, d] = idx
                    idx += 1
                    flowval_lst.append(flowval)

            t = c.variable('t', len(minServer_lst), Domain.greaterThan(0.0))
            c.constraint(Expr.sub(t, minServer_lst) , Domain.lessThan(0))
            load = Expr.dot(t, flowval_lst)

            c.objective("obj", ObjectiveSense.Maximize, load)
            
            # Input and output constraints
            intx_lst = list()
            outtx_lst = list()
            numServer_lst = list()
            
            tfMappingSdToIdx_Keys =  tfMappingSdToIdx.keys()
            for n in Topo.ServerNodes:
                intx = list()                       
                outtx = list()
                for h in Topo.ServerNodes:
                    if n == h:
                        continue
                    if (h, n) in tfMappingSdToIdx_Keys:
                        # intx += t[h, n]
                        intx.append(t.index(tfMappingSdToIdx[h, n]))
                    if (n, h) in tfMappingSdToIdx_Keys:
                        # outtx += t[n, h]
                        outtx.append(t.index(tfMappingSdToIdx[n, h]))
                if len(intx) > 0:
                    intx = Expr.add(intx) 
                else:
                    intx = Expr.constTerm(1, 0)
                if len(outtx) > 0:
                    outtx = Expr.add(outtx) 
                else:
                    outtx = Expr.constTerm(1, 0)

                numServer = Topo.UG.nodes[n]['numServer']
                intx_lst.append(intx)
                outtx_lst.append(outtx)
                numServer_lst.append(numServer)
            
            c.constraint(Expr.sub(Expr.vstack(intx_lst), numServer_lst) , Domain.lessThan(0)) 
            c.constraint(Expr.sub(Expr.vstack(outtx_lst), numServer_lst) , Domain.lessThan(0)) 
            c.solve()

            newTM = None        

            load = c.primalObjValue()
            violation = (load / Topo.UG.get_edge_data(*replink)['capacity']) - 1
            if violation > 0:
                newTM = dict()
                for sd in tfMappingSdToIdx.keys():
                    tfValue = t.index(tfMappingSdToIdx[sd]).reshape(1).level()[0]
                    if tfValue > 0:
                        newTM[sd] = tfValue
            return newTM, violation, c.getSolverDoubleInfo("optimizerTime")

    
    def saveOptimalRouting(self):
        Topo = self.Topo
        F = self.F

        g = nx.DiGraph()
        for node in Topo.UG.nodes():
            g.add_node(node)
        for i, j in Topo.UG.edges():
            g.add_edge(i, j)
            g.add_edge(j, i)
            for repsd in Topo.RepCommodities:
                flowmap = Topo.loadCommodityFlowMap(repsd)
                flowij = F[repsd][flowmap[i, j]].level()[0]
                flowji = F[repsd][flowmap[j, i]].level()[0]             

                if flowij > 0:
                    g[i][j][repsd] = flowij

                if flowji > 0:
                    g[j][i][repsd] = flowji

        pickle.dump(g, open(HCONST['outputdir'] + '/' + 'OptimalRouting', 'wb'))


    def saveIntermediateResult(self, cntiter, tmlinks, throughput):
        Topo = self.Topo
        F = self.F

        g = nx.DiGraph()
        for node in Topo.UG.nodes():
            g.add_node(node)
        for i, j in Topo.UG.edges():
            g.add_edge(i, j)
            g.add_edge(j, i)
            for repsd in Topo.RepCommodities:
                flowmap = Topo.loadCommodityFlowMap(repsd)
                flowij = F[repsd][flowmap[i, j]].level()[0]
                flowji = F[repsd][flowmap[j, i]].level()[0]                    
                if flowij > 0:
                    g[i][j][repsd] = flowij

                if flowji > 0:
                    g[j][i][repsd] = flowji

        pickle.dump((cntiter, g, throughput, tmlinks), open(HCONST['intmeddir'] + '/' + 'iteration_{0}'.format(cntiter), 'wb'))

    
    def loadIntermediateResult(self, cntiter):
        (cntiter, g, throughput, tmlinks) = pickle.load(open(HCONST['intmeddir'] + '/' + 'iteration_{0}'.format(cntiter), 'rb'))
        return (cntiter, g, throughput, tmlinks)

