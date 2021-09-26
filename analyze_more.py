# This is the last file to analyze data
# The most interesting subset of data appears always in the same position: between 280 000 and 300 000,
# and between 320 000 and 340 000. So we extract each train travel (usually two per day) for this two area and save
# then into clean and easy to process csv files. A few change in the parameters could increase or decrease the number
# of data points (every xx meters)
# There is a bug on the second travel that crash the data extract. I did not found out why, let alone corrected it.

import pandas as pd
import numpy as np
from os.path import exists, isfile, join
from os import listdir


def mean_std_signal_quality_location():

    # Get all the files from day to day
    # We know the mean max location, we go by every meter (we devide by 10)
    # we add every value we have for each position, and how many value were added.
    # in the end, we

    temp_path = './data/prepared_rssi/'
    onlyfiles = [f for f in listdir(temp_path) if isfile(join(temp_path, f))]
    onlyfiles.sort()

    min_val, max_val = 9600, 43000
    list_a2_rssi = [[] for x in range(min_val, max_val+1)]
    mean_a2_rssi = [0 for x in range(min_val, max_val+1)]
    std_a2_rssi = [0 for x in range(min_val, max_val+1)]

    for file in onlyfiles:
        print(f"{file}")
        curr_day = pd.read_csv(temp_path+file)
        for index, row in curr_day.iterrows():
            curr_val = row["A2_RSSI"]
            curr_pos = int(row["PositionNoLeap"]/10)
            list_a2_rssi[curr_pos-min_val].append(curr_val)

    for i, a2 in enumerate(list_a2_rssi):
        if len(a2) == 0:
            mean_a2_rssi[i] = 0
            std_a2_rssi[i] = 0
        else:
            mean_a2_rssi[i] = np.mean(a2)
            std_a2_rssi[i] = np.std(a2)

    with open("./data/test_mean.csv", "w") as file:
        file.write("Position,Mean,Std\n")
        for i in range(len(mean_a2_rssi)):
            file.write(f"{i+min_val},{mean_a2_rssi[i]},{std_a2_rssi[i]}\n")


def find_location_disruptions():

    disruption = pd.read_csv("./data/disruption_15.csv")
    disruption['DateTime'] = pd.to_datetime(disruption["DateTime"])
    curr_dis = 0

    while curr_dis < len(disruption.index):
        event_time = disruption.loc[curr_dis]["DateTime"]
        date = str(event_time).split(" ")[0]
        day_data = pd.read_csv(f"./data/prepared_rssi/rssi_{date}.csv")
        day_data['DateTime'] = pd.to_datetime(day_data["DateTime"])
        curr_day = 0
        while curr_day < len(day_data.index)-1:
            if day_data.loc[curr_day]["DateTime"] <= event_time <= day_data.loc[curr_day+1]["DateTime"]:
                print(f"Event found at: {day_data.loc[curr_day]['PositionNoLeap']}")
            curr_day += 1
        curr_dis += 1


def mean_std_signal_selected_locations():
    temp_path = './data/prepared_rssi/'
    onlyfiles = [f for f in listdir(temp_path) if isfile(join(temp_path, f))]
    onlyfiles.sort()

    min_val, max_val = 320000, 340000
    max_delta = 500

    list_results = []

    for file in onlyfiles:
        if file.find("lock") != -1:
            continue

        if file.find("2020-02-15") != -1:
            continue
        if file.find("2020-03-11") != -1:
            continue
        if file.find("2020-03-25") != -1:
            continue
        if file.find("2020-09-06") != -1:
            continue
        if file.find("2021-01-09") != -1:
            continue
        if file.find("2021-") != -1:
            continue
        print(f"{temp_path+file}")
        day_data = pd.read_csv(temp_path+file)
        day_data['DateTime'] = pd.to_datetime(day_data["DateTime"])
        print(file)
        day_data['DateTime'] = pd.to_datetime(day_data["DateTime"])
        location_frame = day_data[(day_data['PositionNoLeap'] > min_val) & (day_data['PositionNoLeap'] < max_val)]

        if len(location_frame.index) == 0:
            continue

        print(f"{len(location_frame.index)}")
        # Check if there is a point where the train comes back
        curr_pos, curr_split = 0, -1
        while curr_pos < len(location_frame.index)-1:
            message_1 = location_frame.iloc[curr_pos]["A2_TotalTel"]
            message_2 = location_frame.iloc[curr_pos+1]["A2_TotalTel"]
            if message_2 - message_1 > max_delta:
                curr_split = message_1
                break
            curr_pos += 1
        # break the frame into two frames
        if curr_split >= 0:
            frame1 = location_frame[location_frame['A2_TotalTel'] <= curr_split]
            frame2 = location_frame[location_frame['A2_TotalTel'] > curr_split]
            print("There is a frame 2")
        else:
            frame1 = location_frame
            frame2 = None
            print("No frame 2")


        # Lets do frame one
        for i in range(min_val, max_val, 1000):
            curr_frame = frame1[(frame1['PositionNoLeap'] >= i) & (frame1['PositionNoLeap'] < i+1000)]
            curr_rssi = curr_frame["A2_RSSI"].tolist()
            mean_rssi = np.mean(curr_rssi)
            delta_ts = pd.Timedelta(curr_frame.iloc[-1]["DateTime"] - curr_frame.iloc[0]["DateTime"]).seconds
            delta_total = (curr_frame.iloc[-1]["A2_TotalTel"] - curr_frame.iloc[0]["A2_TotalTel"])/delta_ts
            delta_valid = (curr_frame.iloc[-1]["A2_ValidTel"] - curr_frame.iloc[0]["A2_ValidTel"])/delta_ts
            timestamp = frame1.iloc[0]["DateTime"]
            list_results.append([timestamp, i, mean_rssi, delta_total, delta_valid])

        if frame2 is not None:
            if len(frame2.index) > 10:
                for i in range(min_val, max_val, 1000):
                    curr_frame = frame2[(frame2['PositionNoLeap'] >= i) & (frame2['PositionNoLeap'] < i+1000)]
                    curr_rssi = curr_frame["A2_RSSI"].tolist()
                    mean_rssi = np.mean(curr_rssi)
                    # print("-------------")
                    # print(curr_frame.iloc[0]["DateTime"])
                    # print(curr_frame.iloc[-1]["DateTime"])
                    delta_ts = pd.Timedelta(curr_frame.iloc[-1]["DateTime"] - curr_frame.iloc[0]["DateTime"]).seconds
                    delta_total = (curr_frame.iloc[-1]["A2_TotalTel"] - curr_frame.iloc[0]["A2_TotalTel"]) / delta_ts
                    delta_valid = (curr_frame.iloc[-1]["A2_ValidTel"] - curr_frame.iloc[0]["A2_ValidTel"]) / delta_ts
                    timestamp = frame2.iloc[0]["DateTime"]
                    list_results.append([timestamp, i, mean_rssi, delta_total, delta_valid])

    out_csv = pd.DataFrame(list_results, columns=['DateTime', 'PositionNoLeap', 'A2_RSSI', 'A2_TotalTel', "A2_ValidTel"])
    out_csv.to_csv("./data/320_340.csv", index=False)


# mean_std_signal_quality_location()
# find_location_disruptions()
mean_std_signal_selected_locations()