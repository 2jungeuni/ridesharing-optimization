import os
import argparse
import numpy as np
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

# solver status
status_dict = {1: "loaded",
               2: "optimal",
               3: "infeasible",
               4: "infeasible and unbounded",
               5: "unbounded",
               6: "cut off",
               7: "iteration limit",
               8: "node limit",
               9: "time limit",
               10: "solution limit",
               11: "interrupted",
               12: "numeric",
               13: "suboptimal",
               14: "in progress",
               15: "user objective limit",
               16: "work limit",
               17: "memory limit"}

# define new optimization problem
def instance_loader(path):
    prize = {}                                          # contains the prize for each zone
    array = open(path).read().splitlines()

    count = 0
    i = 1
    n = int(array[0])                                   # variable n contains the number of zones
    while (count < n):
        property = array[i].split()
        time = property[0].split(",")
        prize.update({count + 1: float(property[1])})   # prize
        i = i + 1
        count = count + 1
    i = n + 1

    # creating matrix distance matrix filled with zeros
    distance_matrix = np.zeros(shape=(n, n))

    # populating of each row of matrix
    for j in range(0, n):
        temp = array[i].split()
        distance_matrix[j] = temp
        i = i + 1

    return {"n": n, "p": prize, "m": distance_matrix}

# solve optimization
def main(problem, depot, limit, alpha, beta):
    assert 1 <= depot <= 63, "depot should be between 1 and 63."

    # path to instance folder
    pathInstances = './data'

    # checking if is a directory of instances or a single instance
    if (os.path.isdir(pathInstances)):
        instances_list = os.listdir(pathInstances)
        instances_list.sort()

    instance_path = Path.cwd() / pathInstances / problem

    # reading instance from file
    ris = instance_loader(instance_path)
    # depot
    o = depot   # TODO: can be changed
    d = 0   # TODO: can be changed

    # prize
    p = ris["p"]
    p[0] = 0
    prize = {}
    for p_key, p_val in p.items():
        prize[p_key] = -1 * alpha * p_val

    # arch's weight
    t = ris["m"]
    t_0 = np.zeros((1, t.shape[0]))
    t = np.vstack((t_0, t))
    t_0 = np.zeros((1, t.shape[0]))
    t = np.concatenate((t_0.T, t), axis=1)

    # define and initialize the optimal model
    m = gp.Model()  # minimization is default
    m.Params.outputFlag = False

    # re-definite distance matrix, t
    dist = {}
    dist_selected = {}
    for i, row in enumerate(t):
        for j, elem in enumerate(row):
            if (i != j):
                dist[(i, j)] = beta * t[i][j]
                dist_selected[(i, j)] = t[i][j]

    # edge
    e_vars = m.addVars(dist.keys(), obj=dist, vtype=GRB.BINARY, name='e')
    # prize
    p_vars = m.addVars(prize.keys(), obj=prize, vtype=GRB.BINARY, name="p")

    # Constraint 1: visited node i must have an outgoing edge.
    cons1 = m.addConstrs(e_vars.sum(i, "*") == p_vars[i] for i in range(0, ris["n"] + 1) if (i != o) and (i != d))
    # Constraint 2: visited node j must have an ingoing edge.
    cons2 = m.addConstrs(e_vars.sum("*", j) == p_vars[j] for j in range(0, ris["n"] + 1) if (j != o) and (j != d))
    # Constraint 3: about the origin.
    # 3-1: origin must have an outgoing edge.
    cons3_1 = m.addConstr(e_vars.sum(o, "*") == 1)
    # 3-2: origin don't have any ingoing edges.
    cons3_2 = m.addConstr(e_vars.sum("*", o) == 0)
    # 3-3: origin must be visited.
    cons3_3 = m.addConstr(p_vars[o] == 1)
    # Constraint 4: about the destination (It is consistent with the origin).
    # 4-1
    cons4_1 = m.addConstr(e_vars.sum("*", d) == 1)
    # 4-2
    cons4_2 = m.addConstr(e_vars.sum(d, "*") == 0)
    # 4-3
    cons4_3 = m.addConstr(p_vars[d] == 1)
    # Constraint 5: there is a time limit.
    cons5 = m.addConstr(gp.quicksum(dist_selected[i, j] * e_vars[i, j]
                                    for i in range(0, ris["n"] + 1)
                                    for j in range(0, ris["n"] + 1) if i != j) + 30 * p_vars.sum('*') <= limit)

    # optimize model
    m._vars = e_vars
    m._dvars = p_vars
    m.Params.lazyConstraints = 1

    def subtourlim(model, where):
        if where == GRB.Callback.MIPSOL:
            # make a list of edges selected in the solution
            vals = model.cbGetSolution(model._vars)
            selected = gp.tuplelist((i, j) for i, j in model._vars.keys()
                                    if vals[i, j] > 0.5)

            # find the shortest cycle in the selected edge list
            tour = subtour(selected)
            if len(tour) >= 1:
                for st in tour:
                    len_tour = len(st)
                    model.cbLazy(gp.quicksum(model._vars[st[idx % len_tour], st[(idx + 1) % len_tour]]
                                             for idx in range(len_tour)) <= len_tour - 1)

    def subtour(edges, exclude_depot=True):
        unvisited = list(range(0, ris["n"] + 1))
        cycle = []
        while unvisited:
            this_cycle = []
            neighbors = unvisited
            while neighbors:
                current = neighbors[0]
                this_cycle.append(current)
                unvisited.remove(current)
                neighbors = [j for i, j in edges.select(current, '*') if j in unvisited]

            if len(this_cycle) > 1:
                if exclude_depot:
                    if not (o in this_cycle or d in this_cycle):
                        cycle.append(this_cycle)
        return cycle

    m.optimize(subtourlim)

    # solution
    print("depot: ", o)
    print("objective value: ", m.objVal)

    e_vals = m.getAttr('x', e_vars)
    selected = {i: j for i, j in e_vals.keys() if e_vals[i, j] > 0.5}

    # get a path
    route = []
    route_time  = 0
    key = o
    while key is not d:
        route_time += dist_selected[(key, selected[key])]
        route.append(key)
        key = selected[key]
    route.append(d)
    print("total travel time: ", route_time)
    return route[:-1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-z", "--zone", required=True, help="Enter the zone index you want to start from.")
    parser.add_argument("-l", "--limit", required=True, help="Define the working time for a ride-sharing vehicle.")
    parser.add_argument("-a", "--alpha", required=True, help="Set the weight for the number of serviced passengers.")
    parser.add_argument("-b", "--beta", required=True, help="Set the weight for waiting times for passengers.")
    args = parser.parse_args()
    depot = int(args.zone)
    time_limit = float(args.limit)
    alpha = float(args.alpha)
    beta = float(args.beta)

    problem = "we_morning.tw"
    route = main(problem, depot, time_limit, alpha, beta)
    print("route: ", route)