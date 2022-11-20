import csv
from typing import List
import queueing_tool as qt
import numpy as np

"""
   fixed parameters:
       NUM_TA: number of TA's
       UNIT_TIME: time each TA holds OH per week
       TOTAL_TIME: NUM_TA * UNIT_TIME

   variable parameters:
       tn: number of each TA's for each time slot
       dt: duration of each time slot
       sn: number of slots per week
       satisfying constrains:
       tn * dt * sn = TOTAL_TIME
       tn, dt, sn >= 1

   evaluation criteria:
       avg_wt: average waiting time
       avg_ql: average length of queue
       avg_ot:average overtime to clear up the queue
       students_served: total number of students served

   to analyze data:
       filter all data s.t. res[*][5] == 0, 
           aggregate res[*][2] - res[*][0] -> avg_wt
           aggregate res[*][3] -> avg_ql
           aggregate cnt -> total_students
       find maximum value in res[*][3] < SIM_TIME - dt -> avg_ot

   to run a simulation:
       for each (tn, dt, sn):
           adjust graph according to tn
           adjust rate cutoff according to dt
           run the simulation sn times
           aggregate data
   """

NUM_TA = 25
UNIT_TIME = 2
CLASS_SIZE = 375
TOTAL_TIME = NUM_TA * UNIT_TIME



def rate(t):
    return 0.1 + (np.sin(np.pi * t / 2) ** 2) / 2


def arr_f(t):
    return qt.poisson_random_measure(t, rate, 100)


def ser_f(t):
    return t + np.random.exponential(10)


def generate_all_params() -> List[List[int]]:
    res = []
    for tn in range(1, NUM_TA + 1):
        for dt in range(1, 9):  # [1 - 8 hours]
            sn = TOTAL_TIME // (tn * dt)
            if sn >= 1:
                res.append([tn, dt, sn])
    print("length of res is", len(res))
    return res


def construct_network(tn):
    adja_list = {0: [1], 1: [k for k in range(2, 2 + tn)]}
    edge_list = {0: {1: 1}, 1: {k: 2 for k in range(2, 2 + tn)}}
    g = qt.adjacency2graph(adjacency=adja_list, edge_type=edge_list)
    q_classes = {1: qt.QueueServer, 2: qt.QueueServer}
    q_args = {
        1: {
            'arrival_f': arr_f,
            'service_f': lambda t: t,
            'AgentFactory': qt.GreedyAgent
        },
        2: {
            'num_servers': 1,
            'service_f': ser_f
        }
    }
    qn = qt.QueueNetwork(g=g, q_classes=q_classes, q_args=q_args, seed=13)
    qn.initialize(edge_type=1)
    return qn


def filter_result(data, tn, dt):
    res = [[] for _ in range(tn + 1)]
    for arrive, start, depart, q_len, total_len, idx in data:
        if idx <= tn and arrive <= dt * 60:
            res[int(idx)].append([arrive, start, depart, q_len, total_len])
    return res

def get_avg_wait_time(cropped_data, tn):
    time = 0.
    num_students = 0
    for i in range(1, tn + 1):
        for arrive, start, _, _, _ in cropped_data[i]:
            time += start - arrive
        num_students += len(cropped_data[i])

    return time / num_students

def get_avg_overtime(cropped_data, tn, dt):
    total_overtime = 0.
    for i in range(1, tn + 1):
        if cropped_data[i]:
            total_overtime += max(0, cropped_data[i][-1][2] - dt * 60)
    return total_overtime / tn


def get_total_students(cropped_data):
    return len(cropped_data[0])


def get_strategy_score(avg_wt, avg_ot, students_served):
    wt_score = max(0., min(100., 105.88 - 0.58823 * avg_wt))
    # print("wt score is", wt_score)
    ot_score = max(0., min(100, 100 + (avg_ot * -.6)))
    # print("ot score is", ot_score)
    students_served_score = min(100, students_served * (100 / (CLASS_SIZE / 1.5)))
    # print("students served score is", students_served_score)
    return (wt_score + ot_score + students_served_score) / 3

if __name__ == "__main__":
    params = generate_all_params()
    results = []
    scores = [0] * len(params)
    for i, (tn, dt, sn) in enumerate(params):
        print(tn, "TA's each time slot, lasts for", dt, "hours,", sn, "sessions")
        g = construct_network(tn)
        g.start_collecting_data()
        g.simulate(t=dt * 60 * 20)
        data = g.get_queue_data()
        cropped_data = filter_result(data, tn, dt)
        avg_wt = get_avg_wait_time(cropped_data, tn)
        avg_ot = get_avg_overtime(cropped_data, tn, dt)
        students_served = get_total_students(cropped_data) * sn
        scores[i] = get_strategy_score(avg_wt, avg_ot, students_served)
        results.append([(tn, dt, sn), avg_wt, avg_ot, students_served, scores[i]])
        print("score is", scores[i])

    max_idx = 0
    max_score = scores[0]

    for i in range(len(scores)):
        if scores[i] > max_score:
            max_score = scores[i]
            max_idx = i

    with open('sample.csv', 'w') as f:
        mywriter = csv.writer(f, delimiter=',')
        mywriter.writerows(results)

    print("Optimal strategy is (", params[max_idx], ") with a score of", max_score)

