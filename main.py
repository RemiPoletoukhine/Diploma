import simpy as sp
import numpy as np
import pandas as pd
from scipy import stats
from PyProbs import Probability as Pr
from collections import namedtuple

# chosen values:
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
BETA = 0.5
# list of tables in cafe: 6 tables for two, 4 tables for three, 5 tables for four
TABLE_LIST = [4, 4, 4, 4, 2, 2, 3, 2,
              4, 3, 2, 4, 2,  #- Shorter version
              3, 2, 4, 3, 4]
#TABLE_LIST = [4, 4, 2, 2, 3, 3, 4, 2, 2, 4]
# list to choose a seats_required value for customers from
SEATS_LIST = [1, 2, 3, 4]
# booking parameters for normal distribution
BOOKING_TIME_MEAN = 1
BOOKING_TIME_VAR = 0.1
# eating parameters for normal distribution
EATING_TIME_MEAN = 18
EATING_TIME_VAR = 2


class Cafeteria:#(object):

    def __init__(self, env, food_num, pay_num, table_list, seed):
        self.env = env
        # seed
        self.seed = seed
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

    def order(self, client):
        # the process of ordering
        #service_time_random = abs(np.random.normal(loc=FOOD_TIME_MEAN, scale=FOOD_TIME_VAR))
        service_time_random = abs(stats.norm.rvs(loc=FOOD_TIME_MEAN,
                                                 scale=FOOD_TIME_VAR,
                                                 random_state=self.seed + client))
        #service_time_random = 1.5
        yield self.env.timeout(service_time_random)
        # print("Serviceman Mark composed the %s's order in %.2f minutes." % (client, service_time_random))

    def payment(self, client):
        # the process of payment
        #payment_time_random = abs(np.random.normal(loc=PAY_TIME_MEAN, scale=PAY_TIME_VAR))
        payment_time_random = abs(stats.norm.rvs(loc=PAY_TIME_MEAN,
                                                 scale=PAY_TIME_VAR,
                                                 random_state=self.seed + client))
        #payment_time_random = 1
        yield self.env.timeout(payment_time_random)
        # print("Cashier Zuck finished the checkout of %s's order in %.2f minutes." % (client, payment_time_random))


def customer(env, name, seats_required, cafe, pre_booking, probability, seed, interval_after_me):
    global df_stats
    # the customer process (identified by "name") enters the cafeteria ("cafe")
    arrival_time = env.now
    # print("%s enters the cafeteria at %.2f." % (name, env.now))
    has_vacant_tables = False
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
            #booking_time_random = abs(np.random.normal(loc=BOOKING_TIME_MEAN, scale=BOOKING_TIME_VAR))
            booking_time_random = abs(stats.norm.rvs(loc=BOOKING_TIME_MEAN,
                                                     scale=BOOKING_TIME_VAR,
                                                     random_state=seed + name))
            #booking_time_random = 1
            yield cafe.env.timeout(booking_time_random)
            # print("%s has been booking a table for %.2f." % (name, booking_time_random))
            # print("%s booked a table at %.2f." % (name, env.now))
            booking_finish = env.now
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
    if not pre_booking:
        # customer looks for a table because hasn't booked in advance
        # print("%s has no choice but to try to book a table for %d at %.2f." % (name, seats_required, env.now))
        booking_start = env.now
        table = yield cafe.table_res_list.get(lambda table: table.seats >= seats_required)
        #booking_time_random = abs(np.random.normal(loc=BOOKING_TIME_MEAN, scale=BOOKING_TIME_VAR))
        booking_time_random = abs(stats.norm.rvs(loc=BOOKING_TIME_MEAN,
                                                 scale=BOOKING_TIME_VAR,
                                                 random_state=seed+name))
        #booking_time_random = 1
        yield cafe.env.timeout(booking_time_random)
        # print("%s booked a table at %.2f." % (name, env.now))
        booking_finish = env.now

    # client eats
    # print("%s starts eating at %.2f." % (name, env.now))
    # eating requires no less than 5 minutes
    eating_start = env.now
    #eating_random = abs(np.random.normal(loc=EATING_TIME_MEAN, scale=EATING_TIME_VAR))
    eating_random = abs(stats.norm.rvs(loc=EATING_TIME_MEAN,
                                       scale=EATING_TIME_VAR,
                                       random_state=seed+name))
    #eating_random = 15
    yield env.timeout(eating_random)
    eating_finish = env.now
    # print("%s eats for %.2f." % (name, eating_random))
    # client leaves the cafeteria, the place is now vacant
    # print("%s left at %.2f. the table is now free." % (name, env.now))
    yield cafe.table_res_list.put(table)

    # fill-in the statistics
    data = [name, nominal_possibility, interval_after_me, seats_required,
            arrival_time, pre_booking, queueing_start, queueing_finish,
            payment_start, payment_finish, booking_start,
            booking_finish, table, eating_start, eating_finish]
    df_curr = pd.DataFrame(data=[data],
                           columns=['Customer', 'NominalPossibility', 'CInterval', 'SeatsRequired',
                                    'ArrivalTime', 'PreBooking', 'QueueingStart', 'QueueingFinish',
                                    'PaymentStart', 'PaymentFinish', 'BookingStart',
                                    'BookingFinish', 'Table', 'EatingStart', 'EatingFinish'])
    df_stats = pd.concat([df_stats, df_curr], ignore_index=True)


def setup(env, food_num, pay_num, c_amount, table_list, probability, seed_val, c_interv):
    # creation of a DataFrame for collecting statistics
    global df_stats
    df_stats = pd.DataFrame(data=[], columns=['Customer', 'NominalPossibility', 'CInterval', 'SeatsRequired',
                                              'ArrivalTime', 'PreBooking', 'QueueingStart', 'QueueingFinish',
                                              'PaymentStart', 'PaymentFinish', 'BookingStart',
                                              'BookingFinish', 'Table', 'EatingStart', 'EatingFinish'])
    # creation of cafeteria
    cafeteria = Cafeteria(env, food_num, pay_num, table_list, seed_val)

    # customers generator
    for i in range(c_amount):
        # let's set the seed
        np.random.seed(seed_val + i)
        # arbitrary delay before the next customer
        if c_interv is None:
            print('No c_interval given')
            c_interval_random = abs(stats.norm.rvs(loc=0.3, scale=0.3 / 3, random_state=seed_val + i))
        else:
            # fixed_interval situation
            # c_interval_random = round(c_interv, 2)  # in order to avoid the 0.60000..01 cases
            # normal distibution (here the c_interv input is a mean)
            # c_interval_random = abs(stats.norm.rvs(loc=c_interv, scale=c_interv / 3, random_state=seed_val))
            # exponential distribution (here the c_interv is a scale)
            c_interval_random = stats.expon.rvs(loc=0, scale=c_interv, random_state=seed_val)
            # different interv for one launch: if the number is even:
            # if i % 2 == 0:
                # c_interval_random = round(c_interv, 2)
            # else:
                # c_interval_random = stats.expon.rvs(loc=0, scale=c_interv, random_state=seed_val)

        # version with name: env.process(customer(env, "Customer %d" % i, np.random.randint(1, 5), cafeteria, False))
        env.process(customer(env, i, np.random.choice(SEATS_LIST, p=[0.3, 0.4, 0.2, 0.1]),
                             cafeteria, 0, probability, seed_val, c_interval_random))
        # print("Customer %d appears at %.2f" % (i, env.now))

        #c_interval_random = np.random.exponential(scale=BETA)
        #c_interval_random = min(0.5, stats.expon.rvs(loc=0, scale=BETA, random_state=seed_val + i))
        #c_interval_random = stats.erlang.rvs(a=2, loc=0.25, scale=0.1, random_state=seed_val + i)
        #c_interval_random = abs(stats.norm.rvs(loc=2, scale=0.5, random_state=seed_val + i))

        yield env.timeout(c_interval_random)


def launcher(probability, seed_value, client_intervals=None):
    # let's do the seed to compare identical random values
    # np.random.seed(seed_value)
    # Create an environment and start the setup process
    env = sp.Environment()
    env.process(setup(env, FOOD_NUM, PAY_NUM, C_AMOUNT, TABLE_LIST, probability, seed_value, client_intervals))
    # launch
    env.run()

    return df_stats


# New function for stats
# repeating for several probs and c_interval
def several_intervals(intervals, probabilities):
    # yes, another df
    data_out = pd.DataFrame(data=[], columns=['Customer', 'NominalPossibility', 'CInterval', 'SeatsRequired',
                                              'ArrivalTime', 'PreBooking', 'QueueingStart', 'QueueingFinish',
                                              'PaymentStart', 'PaymentFinish', 'BookingStart',
                                              'BookingFinish', 'Table', 'EatingStart', 'EatingFinish'])
    seed_val = np.random.randint(1, 12345678)
    for interval in intervals:
        for probability in probabilities:
            data_out = pd.concat([data_out, launcher(probability, seed_val, interval)],
                                 ignore_index=True)

    return data_out


#several_intervals(intervals=np.arange(0.0, 2, 0.25),
                  #probabilities=np.arange(0.0, 1.01, 0.01)).to_csv('analysis5_13.csv', index=False)
launcher(0.5, 2, 0.5).to_csv('latex_sample.csv', index=False)