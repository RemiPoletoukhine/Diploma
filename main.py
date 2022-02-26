import simpy as sp
import random as rdm
import pandas as pd
from PyProbs import Probability as Pr
from collections import namedtuple
from statistics import mean
import os

# chosen values:
THE_SEED = 123456798
PROBA = 1
FOOD_NUM = 1
FOOD_TIME = 3
PAY_NUM = 1
PAY_TIME = 2
C_AMOUNT = 100
C_INTERVAL = 2
# TODO: list creator
TABLE_LIST = [2, 4, 2, 3, 2,
              4, 3, 2, 4, 2,
              3, 2, 4, 3, 4]
BOOKING_TIME = 1
EATING_TIME = 20
N = 1


# file = open("Results.txt", "r+")
# file.truncate(0)
# file.close()


class Cafeteria(object):

    def __init__(self, env, food_num, food_time, pay_num, pay_time, table_list):
        self.env = env
        # resource 1: serviceperson who forms the order
        self.food = sp.Resource(env, food_num)
        self.food_time = food_time
        # resource 2: checkout where customers pay for the order
        self.pay = sp.Resource(env, pay_num)
        self.pay_time = pay_time
        # resource 3: list of tables in the cafeteria; each table is a resource
        self.table_res_list = sp.FilterStore(env, capacity=len(table_list))
        Table = namedtuple('Table', 'id, seats')
        table_list = list(zip(list(range(len(table_list))), table_list))
        for element in table_list:
            self.table_res_list.items.append(Table(element[0], element[1]))

        # for i in range(len(table_list.id)):
        # self.table_res_list.items.append(table_list.seats[i])
        # for i in range(len(table_list)):
        # self.table_res_list.items.append(table_list[i])

    def order(self, customer):
        # the process of ordering
        service_time_random = rdm.uniform(1, FOOD_TIME)
        yield self.env.timeout(service_time_random)
        # print("Serviceman Mark composed the %s's order in %.2f minutes." % (customer, service_time_random))

    def payment(self, customer):
        # the process of payment
        payment_time_random = rdm.uniform(0.5, PAY_TIME)
        yield self.env.timeout(payment_time_random)
        # print("Cashier Zuck finished the checkout of %s's order in %.2f minutes." % (customer, payment_time_random))


def customer(env, name, seats_required, cafe, has_table):
    global df_stats
    # the customer process (identified by "name") enters the cafeteria ("cafe")
    arrival_time = env.now
    # print("%s enters the cafeteria at %.2f." % (name, env.now))
    has_vacant_tables = False
    pre_booking = False
    for i in range(len(cafe.table_res_list.items)):
        # print(cafe.table_res_list.items[i])
        if cafe.table_res_list.items[i].seats >= seats_required:
            has_vacant_tables = True
    # the process of table booking
    # the customer books a table in advance with a certain possibility (here - with a PROBA possibility)
    if Pr.Prob(PROBA):
        # the option with pre-booking works only if no one seeks for the place (queue is empty)
        # TODO: if a company enters the cafe, they stand in the queue for booking (not just to get a table try for once)
        if has_vacant_tables:
            # print("hmm, looks like I, %s, can book a table here" % name)
            booking_start = env.now
            table = yield cafe.table_res_list.get(lambda table: table.seats >= seats_required)
            booking_time_random = rdm.uniform(0.5, BOOKING_TIME)
            yield cafe.env.timeout(booking_time_random)
            # print("%s has been booking a table for %.2f." % (name, booking_time_random))
            # print("%s booked a table at %.2f." % (name, env.now))
            booking_finish = env.now
            has_table = True
            pre_booking = True
        else:
            pass
            # print("looks like no vacant places for me, %s" % name)

    # the customer requests an order
    queueing_start = env.now
    with cafe.food.request() as request_food:
        yield request_food
        # print("%s starts forming the order at %.2f." % (name, env.now))
        yield env.process(cafe.order(name))
        # print("%s proceeds to the checkout at %.2f." % (name, env.now))
    queueing_finish = env.now

    # and requests completion of the payment procedure
    payment_start = env.now
    with cafe.pay.request() as request_pay:
        yield request_pay
        # print("%s starts the payment procedure at %.2f." % (name, env.now))
        yield env.process(cafe.payment(name))
        # print("%s finishes the payment procedure at %.2f." % (name, env.now))
    payment_finish = env.now

    # check if the customer has a booked table
    if not has_table:
        # customer looks for a table because hasn't booked in advance
        # print("%s has no choice but to try to book a table for %d at %.2f." % (name, seats_required, env.now))
        booking_start = env.now
        table = yield cafe.table_res_list.get(lambda table: table.seats >= seats_required)
        booking_time_random = rdm.uniform(0.5, BOOKING_TIME)
        yield cafe.env.timeout(booking_time_random)
        # print("%s booked a table at %.2f." % (name, env.now))
        booking_finish = env.now

    # client eats
    # print("%s starts eating at %.2f." % (name, env.now))
    # eating requires no less than 5 minutes
    eating_start = env.now
    eating_random = rdm.uniform(5, EATING_TIME)
    yield env.timeout(eating_random)
    eating_finish = env.now
    # print("%s eats for %.2f." % (name, eating_random))
    # client leaves the cafeteria, the place is now vacant
    # print("%s left at %.2f. the table is now free." % (name, env.now))
    yield cafe.table_res_list.put(table)

    # fill-in the statistics
    data = [name, seats_required, arrival_time,
            pre_booking, queueing_start, queueing_finish,
            payment_start, payment_finish, booking_start,
            booking_finish, table, eating_start, eating_finish]
    df_curr = pd.DataFrame(data=[data],
                           columns=['Customer', 'SeatsRequired', 'ArrivalTime',
                                    'PreBooking', 'QueueingStart', 'QueueingFinish',
                                    'PaymentStart', 'PaymentFinish', 'BookingStart',
                                    'BookingFinish', 'Table', 'EatingStart', 'EatingFinish'])
    df_stats = pd.concat([df_stats, df_curr])


def setup(env, food_num, food_time, pay_num, pay_time, c_amount, c_interval, table_list):
    global df_stats
    # creation of cafeteria
    cafeteria = Cafeteria(env, food_num, food_time, pay_num, pay_time, table_list)

    # customers generator
    for i in range(c_amount):
        env.process(customer(env, "Customer %d" % i, rdm.randrange(1, 5), cafeteria, False))

        # print("Customer %d appears at %.2f" % (i, env.now))

        # arbitrary delay before the next customer
        c_interval_random = rdm.uniform(0.5, c_interval)
        yield env.timeout(c_interval_random)


def launcher():
    print("Welcome to the Cafeteria!")
    rdm.seed(THE_SEED)
    # Create an environment and start the setup process
    for _ in range(N):
        env = sp.Environment()
        env.process(setup(env, FOOD_NUM, FOOD_TIME, PAY_NUM, PAY_TIME, C_AMOUNT, C_INTERVAL, TABLE_LIST))
        # launch
        env.run()
    return df_stats


# creation of a DataFrame for collecting statistics
df_stats = pd.DataFrame(data=[], columns=['Customer', 'SeatsRequired', 'ArrivalTime',
                                          'PreBooking', 'QueueingStart', 'QueueingFinish',
                                          'PaymentStart', 'PaymentFinish', 'BookingStart',
                                          'BookingFinish', 'Table', 'EatingStart', 'EatingFinish'])

if __name__ == '__main__':
    print(launcher())
