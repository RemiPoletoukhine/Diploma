import simpy as sp
import numpy as np
import pandas as pd
from PyProbs import Probability as Pr
from collections import namedtuple

# chosen values:
#THE_SEED = 212121212
FOOD_NUM = 1
PAY_NUM = 1
# serving parameters for normal distribution
FOOD_TIME_MEAN = 1.5
FOOD_TIME_VAR = 0.4
# payment parameters for normal distribution
PAY_TIME_MEAN = 1
PAY_TIME_VAR = 0.1
# number of customers
C_AMOUNT = 100
# client occurrences rate for exponential distribution (beta = 1 / lambda)
BETA = 1
# list of tables in cafe: 6 tables for two, 4 tables for three, 5 tables for four
TABLE_LIST = [2, 4, 2, 3, 2,
              4, 3, 2, 4, 2,
              3, 2, 4, 3, 4]
# booking parameters for normal distribution
BOOKING_TIME_MEAN = 1
BOOKING_TIME_VAR = 0.1
# eating parameters for normal distribution
EATING_TIME_MEAN = 18
EATING_TIME_VAR = 2


class Cafeteria(object):

    def __init__(self, env, food_num, pay_num, table_list):
        self.env = env
        # resource 1: serviceperson who forms the order
        self.food = sp.Resource(env, food_num)
        # resource 2: checkout where customers pay for the order
        self.pay = sp.Resource(env, pay_num)
        # resource 3: list of tables in the cafeteria; each table is a resource
        self.table_res_list = sp.FilterStore(env, capacity=len(table_list))
        Table = namedtuple('Table', 'id, seats')
        table_list = list(zip(list(range(len(table_list))), table_list))
        for element in table_list:
            self.table_res_list.items.append(Table(element[0], element[1]))

    def order(self, customer):
        # the process of ordering
        service_time_random = abs(np.random.normal(loc=FOOD_TIME_MEAN, scale=FOOD_TIME_VAR))
        yield self.env.timeout(service_time_random)
        # print("Serviceman Mark composed the %s's order in %.2f minutes." % (customer, service_time_random))

    def payment(self, customer):
        # the process of payment
        payment_time_random = abs(np.random.normal(loc=PAY_TIME_MEAN, scale=PAY_TIME_VAR))
        yield self.env.timeout(payment_time_random)
        # print("Cashier Zuck finished the checkout of %s's order in %.2f minutes." % (customer, payment_time_random))


def customer(env, name, seats_required, cafe, has_table, probability):
    global df_stats
    # the customer process (identified by "name") enters the cafeteria ("cafe")
    arrival_time = env.now
    # print("%s enters the cafeteria at %.2f." % (name, env.now))
    has_vacant_tables = False
    pre_booking = 0
    for i in range(len(cafe.table_res_list.items)):
        # print(cafe.table_res_list.items[i])
        if cafe.table_res_list.items[i].seats >= seats_required:
            has_vacant_tables = True
    # the process of table booking
    # the customer books a table in advance with a certain possibility
    nominal_possibility = probability
    if Pr.Prob(nominal_possibility):
        # the option with pre-booking works only if no one seeks for the place (queue is empty)
        # TODO: if a company enters the cafe, they stand in the queue for booking (not just to get a table try for once)
        if has_vacant_tables:
            # print("hmm, looks like I, %s, can book a table here" % name)
            booking_start = env.now
            table = yield cafe.table_res_list.get(lambda table: table.seats >= seats_required)
            booking_time_random = abs(np.random.normal(loc=BOOKING_TIME_MEAN, scale=BOOKING_TIME_VAR))
            yield cafe.env.timeout(booking_time_random)
            # print("%s has been booking a table for %.2f." % (name, booking_time_random))
            # print("%s booked a table at %.2f." % (name, env.now))
            booking_finish = env.now
            has_table = True
            pre_booking = 1
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
        booking_time_random = abs(np.random.normal(loc=BOOKING_TIME_MEAN, scale=BOOKING_TIME_VAR))
        yield cafe.env.timeout(booking_time_random)
        # print("%s booked a table at %.2f." % (name, env.now))
        booking_finish = env.now

    # client eats
    # print("%s starts eating at %.2f." % (name, env.now))
    # eating requires no less than 5 minutes
    eating_start = env.now
    eating_random = abs(np.random.normal(loc=EATING_TIME_MEAN, scale=EATING_TIME_VAR))
    yield env.timeout(eating_random)
    eating_finish = env.now
    # print("%s eats for %.2f." % (name, eating_random))
    # client leaves the cafeteria, the place is now vacant
    # print("%s left at %.2f. the table is now free." % (name, env.now))
    yield cafe.table_res_list.put(table)

    # fill-in the statistics
    data = [name, nominal_possibility, seats_required, arrival_time,
            pre_booking, queueing_start, queueing_finish,
            payment_start, payment_finish, booking_start,
            booking_finish, table, eating_start, eating_finish]
    df_curr = pd.DataFrame(data=[data],
                           columns=['Customer', 'NominalPossibility', 'SeatsRequired', 'ArrivalTime',
                                    'PreBooking', 'QueueingStart', 'QueueingFinish',
                                    'PaymentStart', 'PaymentFinish', 'BookingStart',
                                    'BookingFinish', 'Table', 'EatingStart', 'EatingFinish'])
    df_stats = pd.concat([df_stats, df_curr], ignore_index=True)


def setup(env, food_num, pay_num, c_amount, table_list, probability):
    # creation of a DataFrame for collecting statistics
    global df_stats
    df_stats = pd.DataFrame(data=[], columns=['Customer', 'NominalPossibility', 'SeatsRequired', 'ArrivalTime',
                                              'PreBooking', 'QueueingStart', 'QueueingFinish',
                                              'PaymentStart', 'PaymentFinish', 'BookingStart',
                                              'BookingFinish', 'Table', 'EatingStart', 'EatingFinish'])
    # creation of cafeteria
    cafeteria = Cafeteria(env, food_num, pay_num, table_list)

    # customers generator
    for i in range(c_amount):
        # version with name: env.process(customer(env, "Customer %d" % i, np.random.randint(1, 5), cafeteria, False))
        env.process(customer(env, i, np.random.randint(1, 5), cafeteria, False, probability))
        # print("Customer %d appears at %.2f" % (i, env.now))

        # arbitrary delay before the next customer
        c_interval_random = np.random.exponential(scale=BETA)
        yield env.timeout(c_interval_random)


def launcher(probability, seed_value):
    # let's do the seed to compare identical random values
    np.random.seed(seed_value)
    # Create an environment and start the setup process
    env = sp.Environment()
    env.process(setup(env, FOOD_NUM, PAY_NUM, C_AMOUNT, TABLE_LIST, probability))
    # launch
    env.run()

    return df_stats

