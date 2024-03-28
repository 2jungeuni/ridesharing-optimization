import argparse
import numpy as np

import gurobipy as gp
from gurobipy import *

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

# problem
def optimization(problem, num_v, time_limit, alpha, beta):
    array = open(problem).read().splitlines()
    n = int(array[0])

    count = 0
    i = 1
    p = {}
    while (count < n):
        property = array[i].split()
        p.update({count + 1: float(property[1])})
        i = i + 1
        count = count + 1
    i = n + 1

    # creating matrix distance matrix filled with zeros
    t = np.zeros(shape=(n, n))

    # populating of each row of matrix
    for j in range(0, n):
        temp = array[i].split()
        t[j] = temp
        i = i + 1

    # indices of nodes
    stations = [k for k in range(1, n + 1)]

    # set depot
    depot = 0
    p[depot] = 0
    all_stations = stations + [depot]

    # prize dictionary
    prize = {}
    for p_key, p_val in p.items():
        for v in range(num_v):
            prize[(p_key, v)] = -alpha * p_val

    # arch's weight
    t_0 = np.zeros((1, t.shape[0]))
    t = np.vstack((t_0, t))
    t_0 = np.zeros((1, t.shape[0]))
    t = np.concatenate((t_0.T, t), axis=1)

    # define and initialize the optimal model
    m = gp.Model()  # minimization is default
    m.Params.outputFlag = False
    #m.Params.timeLimit = 10

    # re-definite distance matrix, t
    dist = {}
    dist_selected = {}
    for i, row in enumerate(t):
        for j, elem in enumerate(row):
            for v in range(num_v):
                if (i != j):
                    dist[(i, j, v)] = beta * t[i][j]
                    dist_selected[(i, j, v)] = t[i][j]

    # edge
    e_vars = m.addVars(dist.keys(), obj=dist, vtype=GRB.BINARY, name="e")
    # prize
    p_vars = m.addVars(prize.keys(), obj=prize, vtype=GRB.BINARY, name="p")

    # Constraint 1: only one vehicle can visit one stop except for the depot.
    cons1 = m.addConstrs(p_vars.sum(i, "*") <= 1 for i in stations)
    # Constraint 2: visited node i must have an outgoing edge.
    cons2 = m.addConstrs(e_vars.sum(i, "*", v) == p_vars[(i, v)] for i in all_stations for v in range(num_v))
    # Constraint 3: visited node j must have an ingoing edge.
    cons3 = m.addConstrs(e_vars.sum("*", j, v) == p_vars[(j, v)] for j in all_stations for v in range(num_v))
    # Constraint 4: considering the origin.
    cons4_1 = m.addConstr(p_vars.sum(depot, "*") == num_v)
    # Constraint 5: there is a time limit.
    cons_5 = m.addConstrs(gp.quicksum(dist_selected[i, j, v] * e_vars[i, j, v]
                                      for i in range(0, n + 1)
                                      for j in range(0, n + 1) if i != j)
                          + 30 * p_vars.sum("*", v) <= time_limit
                          for v in range(num_v))

    def subtourlim(model, where):
        if where == GRB.Callback.MIPSOL:
            # make a list of edges selected in the solution
            vals = model.cbGetSolution(model._vars)
            selected = gp.tuplelist((i, j, k) for i, j, k in model._vars.keys() if vals[i, j, k] > 0.5)
            # find the shortest cycle in the selected edge list
            tour = subtour(selected)
            for v in range(num_v):
                if tour[v]:
                    for tv in tour[v]:
                        if len(tv) < n:
                            # add subtour elimination constraint for every pair of cities in tour
                            model.cbLazy(gp.quicksum(model._vars[i, j, v] for i, j in itertools.permutations(tv, 2))
                                         <= len(tv) - 1)

    def subtour(edges, exclude_depot=True):
        cycle = [[] for v in range(num_v)]

        for v in range(num_v):
            unvisited = all_stations.copy()

            while unvisited:    # true if list is non-empty
                this_cycle = []
                neighbors = unvisited

                while neighbors:
                    current = neighbors[0]
                    this_cycle.append(current)
                    unvisited.remove(current)
                    neighbors = [j for i, j, k in edges.select(current, '*', '*') if (j in unvisited) and (k == v)]

                if len(this_cycle) > 1:
                    if exclude_depot:
                        if not (depot in this_cycle):
                            cycle[v].append(this_cycle)
        return cycle

    # optimize model
    m._vars = e_vars
    m._dvars = p_vars
    m.Params.lazyConstraints = 1
    m.optimize(subtourlim)

    # solution
    print("objective value: ", m.objVal)

    e_vals = m.getAttr('x', e_vars)
    sol_dict = {}
    for car in range(num_v):
        sol_dict[car] = {}
        for i, j, k in e_vals.keys():
            if (e_vals[i, j, k] > 0.5) and (k == car):
                sol_dict[k][i] = j

    routes = []
    for car in range(num_v):
        print("car: ", car)
        route = sol_dict[car]
        i = 0
        path = []
        travel_time = 0
        while True:
            i = route[i]
            if i == 0:
                break
            path.append(i)
            travel_time += dist_selected[(i, sol_dict[car][i], car)]
        print("path: ", path)
        print("travel time: ", travel_time)
        routes.append(path)
    return routes

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-v", "--num_vehicles", required=True, help="Enter the number of vehicles for the system.")
    parser.add_argument("-l", "--limit", required=True, help="Define the working time for each ride-sharing vehicle.")
    parser.add_argument("-a", "--alpha", required=True, help="Set the weight for the number of serviced passengers.")
    parser.add_argument("-b", "--beta", required=True, help="Set the weight for waiting times for passengers.")
    args = parser.parse_args()
    num_v = int(args.num_vehicles)
    time_limit = float(args.limit)
    alpha = float(args.alpha)
    beta = float(args.beta)
    routes = optimization("./data/wk_morning.tw", num_v, time_limit, alpha, beta)