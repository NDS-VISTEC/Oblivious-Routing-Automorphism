# Oblivious Routing Automorphism

**Optimal Oblivious Routing with Concave Objective for Structured Networks (TON 2023)** <br>

**[Paper](https://ieeexplore.ieee.org/document/10100699)** <br>

In general, for any network, oblivious routing can be formulated as a robust multi-commodity flow problem with a concave objective in which the number of constraints grows factorially with the number of switches in the network resulting in the problem being intractable. <br>

In this work, we exploit the topological network structure and graph automorphism to reduce the complexity of the robust optimization problem to the point that is tractable for any off-the-shelf solver running on commodity hardware. <br>

<img src="https://i.imgur.com/DqjnobI.png" width="600"><br>

The contributions of this work are threefold, which leads to a more general oblivious routing formulation supporting traditional linear objective functions and fairness-aware functions. <br>

1. We prove the existence of an automorphism-invariant optimal solution of an oblivious routing problem with a concave objective in every structured topology. This reduces the search space of optimal solutions. <br>
2. We design the iterative algorithm that targets the automorphism-invariant optimal solution using graph automorphism. The algorithm is tractable in comparison to solving the intractable oblivious routing formulation. <br>
3. We develop the polynomial-time construction of the algorithm and illustrate three applications of the algorithm. <br>

##  Highlight results

We show highlight results of proposed iterative algorithm in terms of scalability, throughput performance. <br>

**Scalability** <br> 

<img src="https://i.imgur.com/FcxxL53.png" width="600"><br>

This figure shows the sizes of the strawman optimization formulation (3) and our automorphism-invariant optimization formulation (8) in terms of numbers of variables and constraints at different sizes of FatClique, assuming only one traffic matrix is considered. It is easy to see that the latter formulation is much smaller than the former one. <br>

**Throughput performance** <br>

We evaluate the performance of our algorithm by the worse-case throughput. The result with different objective functions is compared to a [heuristic algorithm](https://www.sysnet.ucsd.edu/sysnet/miscpapers/wcmp-eurosys-final.pdf) in which tries to balance the imbalance by weighting flows regarding their bottleneck capacity. <br>

<img src="https://i.imgur.com/gzDfC2f.png" width="600"><br>

This figure shows the worst-case throughput values under partially deployed FatTree. At 30 aggregation blocks, the throughput improvement is 87.5%.<br>

## Table of contents
-----
  * [Code Structure](#code-structure)
  * [How to use](#how-to-use)
  * [Slimfly topology](#slimfly-topology)
  * [Using your own topology](#using-your-own-topology)
  * [Citation](#citation)
------

## Code structure
- ```main.py``` consists of templates and examples 
- ```network_generator.py``` for generating the topology
- ```topology_automorphism.py``` for constructing automorphic topology
- ```optimization_mosekfusion.py``` for finding optimal routing solution 
- ```verification.py``` for verifying the routing solution 
- ```verification_dring_route.py``` for verifying the DRing routing (ECMP and SU2) solution  
- ```dring_routing.py``` for generating DRing route based on original paper (ECMP and SU2)
- ```state_helper.py``` miscellaneous helper methods
- ```modelLib.py``` is a library of simple building blocks in Mosek Fusion
- ```Dockerfile``` for building the Docker image
- ```requirements.txt``` required python packages for the Docker image 


## How to use

### Download code
```shell
$ git clone https://github.com/NDS-VISTEC/Oblivious-Routing-Automorphism.git
```

### Use Docker
We test the code with the following environment
- Ubuntu 20.04 LTS
- Docker 20.10.17 (build 100c701)

**Build an Docker image**

```shell
$ echo $PWD
/home/NDS/
$ ls $PWD
Oblivious-Routing-Automorphism  mosek.lic
$ cd Oblivious-Routing-Automorphism
$ sudo docker build -t oblivious-routing-automorphism .
```

**Run the code via docker**

Assume you already have [MOSEK license file (mosek.lic)](https://www.mosek.com/products/academic-licenses/) in $PWD/mosek.lic
```shell
$ echo $PWD
/home/NDS/
$ ls $PWD
Oblivious-Routing-Automorphism  mosek.lic
$ sudo docker run --volume=$PWD/mosek.lic:/root/mosek/mosek.lic:ro --volume=$PWD/Oblivious-Routing-Automorphism:/app oblivious-routing-automorphism
```

### Use native environment

**Prerequisites** 
- Python 3.10.8
- Mosek 9.3.18
- networkx 2.8
- numpy 1.21.5
- pynauty 1.0.2

All packages can be installed as follows: 

```shell
$ pip install -r requirements.txt
```

**How to run** 

Assume you already have [MOSEK license file (mosek.lic)](https://www.mosek.com/products/academic-licenses/) in ~/mosek/mosek.lic

```shell
$ python main.py
```

## SlimFly topology
For SlimFly topology, it can be downloaded via https://spcl.inf.ethz.ch/Research/Scalable_Networking/SlimFly/ <br>
(1) Extract ```sf.tar.gz``` file <br>
(2) Copy directory ```sf_sc_2014/graphs/adjacency-list-format``` to this project directory <br>
(3) Rename directory from ```adjacency-list-format``` to ```SlimFly``` <br>

## Using your own topology
You can implement your topology in ```network_generator.py``` and create your workflow based on templates in ```main.py```

## Citation
```
@ARTICLE{oblivious-routing-automorphism,
  author={Chitavisutthivong, Kanatip and Supittayapornpong, Sucha and Namyar, Pooria and Zhang, Mingyang and Yu, Minlan and Govindan, Ramesh},
  journal={IEEE/ACM Transactions on Networking}, 
  title={Optimal Oblivious Routing With Concave Objectives for Structured Networks}, 
  year={2023},
  volume={},
  number={},
  pages={1-13},
  doi={10.1109/TNET.2023.3264632}}
```
## Visit us
<a href="https://vistec.ist/network"><img src="https://i.imgur.com/NV7ADp2.png" height="40"></a>&nbsp;<a href="https://vistec.ist/"><img src="https://i.imgur.com/jNeJIKB.png" height="40"></a>