import main
import pandas as pd
import numpy as np


# process of aggregated analysis, i.e. analysis of a series of launches


# repeating the process of getting the data for each probability in list
def several_probs(probs):
    # and yet another DataFrame for overall data
    inter_data = pd.DataFrame(data=[], columns=['Customer', 'Possibility', 'PreBooking',
                                                'QueueingTime', 'PaymentTime', 'BookingTime',
                                                'EatingTime', 'TotalTime'])

    # repeating for each possibility: 0.1, 0.2, ..., 1 with identical random values each times
    seed_val = np.random.randint(1, 12345678)
    for possibility in probs:
        # firstly, create a DataFrame for each current data
        aggr_data = pd.DataFrame(data=[], columns=['Customer', 'Possibility', 'PreBooking',
                                                   'QueueingTime', 'PaymentTime', 'BookingTime',
                                                   'EatingTime', 'TotalTime'])
        # get data from the process
        data = main.launcher(possibility, seed_value=seed_val)
        # and sort it
        data.sort_values(by=['NominalPossibility', 'Customer'], inplace=True, ignore_index=True)
        # calculate the values
        queueing_time = data['QueueingFinish'].subtract(data['QueueingStart'])
        payment_time = data['PaymentFinish'].subtract(data['PaymentStart'])
        booking_time = data['BookingFinish'].subtract(data['BookingStart'])
        eating_time = data['EatingFinish'].subtract(data['EatingStart'])
        total_time = data['EatingFinish'].subtract(data['ArrivalTime'])
        # and fill them
        aggr_data['Customer'] = data['Customer']
        aggr_data['Possibility'] = data['NominalPossibility']  # .astype(float)
        aggr_data['PreBooking'] = data['PreBooking']
        aggr_data['QueueingTime'] = queueing_time
        aggr_data['PaymentTime'] = payment_time
        aggr_data['BookingTime'] = booking_time
        aggr_data['EatingTime'] = eating_time
        aggr_data['TotalTime'] = total_time
        # concatenate data for each possibility together
        inter_data = pd.concat([inter_data, aggr_data], ignore_index=True)

    return inter_data


# repeating the function above n times
def several_times_probs(probs, n):
    # another df
    final_data = pd.DataFrame(data=[], columns=['Customer', 'Possibility', 'PreBooking',
                                                'QueueingTime', 'PaymentTime', 'BookingTime',
                                                'EatingTime', 'TotalTime'])
    for _ in range(n):
        # concatenate all data together
        final_data = pd.concat([final_data, several_probs(probs)], ignore_index=True)

    return final_data


# export the data
several_times_probs(np.arange(0.0, 1.05, 0.05), 10).to_csv('analysis5_7.csv', index=False)
