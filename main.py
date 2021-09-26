# This is the first file created to get a bit used with the data
# Here are several function, not really organized splitting larges data files into smaller files.
# Some function try to make sense of the data, clean missing information...

import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt


def extract_date(line):
    # Extract the date for a line from a csv, used to prepare the data
    date = line.split(",")[1]
    date = date.split(" ")[0]
    return date


def splitting_rssi_files():

    with open("./data/rssi.csv") as fichier:
        frontline = fichier.readline()
        # print(line)
        line = fichier.readline()
        curr_date = extract_date(line)
        curr_file = open(f"./data/prepared_rssi/rssi_{curr_date}.csv", "w")
        curr_file.write(frontline)
        while line:
            new_date = extract_date(line)
            if new_date != curr_date:
                curr_date = new_date
                print(f"new file: {curr_date}")
                curr_file.close()
                curr_file = open(f"./data/prepared_rssi/rssi_{curr_date}.csv", "w")
                curr_file.write(frontline)
            curr_file.write(line)
            line = fichier.readline()

    print("here")


def splitting_speed_files():

    with open("./data/velocities.csv") as fichier:
        frontline = fichier.readline()
        # print(line)
        line = fichier.readline()
        curr_date = extract_date(line)
        curr_file = open(f"./data/prepared_speed/velocity_{curr_date}.csv", "w")
        curr_file.write(frontline)
        while line:
            new_date = extract_date(line)
            if new_date != curr_date:
                curr_date = new_date
                print(f"new file: {curr_date}")
                curr_file.close()
                curr_file = open(f"./data/prepared_speed/velocity_{curr_date}.csv", "w")
                curr_file.write(frontline)
            curr_file.write(line)
            line = fichier.readline()

    print("here")


def clean_csv():
    # Index(['ID', 'DateTime', 'AreaNumber', 'Track', 'Position', 'PositionNoLeap',
    #        'Latitude', 'Longitude', 'A1_TotalTel', 'A1_ValidTel', 'A2_RSSI',
    #        'A2_TotalTel', 'A2_ValidTel'],

    # Indexcleaned(['ID', 'DateTime', 'PositionNoLeap', 'A1_TotalTel', 'A1_ValidTel',
    #        'A2_RSSI', 'A2_TotalTel', 'A2_ValidTel'],
    #       dtype='object')
    for i in range(31):
        in_name = f"./data/rssi_{i}.csv"
        out_name = f"./data/rssi_{i}_light.csv"
        print(in_name)
        with open(in_name) as f:
            with open(out_name, 'w') as f_out:
                line = f.readline()
                while line:
                    line = line.split(",")
                    new_line = f"{line[0]},{line[1]},{line[5]},{line[8]},{line[9]},{line[10]},{line[11]},{line[12]}"
                    f_out.write(new_line)
                    line = f.readline()


def get_mean_v():

    rssi = pd.read_csv("./data/prepared_rssi/2020.csv")
    print(rssi.columns)
    volt = rssi["A2_RSSI"].tolist()
    print(f"Mean: {np.mean(volt)}")
    print(f"Std: {np.std(volt)}")


def display_date_time(date, time, window):
    # Display a graph using matplotlib of the date and time with a window of a few minutes
    file = pd.read_csv(f"./data/prepared_rssi/{date}.csv")


def find_event_no_data_2020_09_09():
    # On the 2020-09-09 @ 13:20:04, I have an event (and a lot around this time), but no data in the rssi.csv
    # This function will try to identify all the event with no data
    print("Checking the rssi.csv file")

    with open("./data/rssi.csv") as fichier:
        fichier.readline()  # skip the first line
        line = fichier.readline()
        while line:
            # Get the date
            line = line.split(",")[1]

            date, time = line.split(" ")
            if date == "2020-09-09" and time[:3] == "00:":
                print(f"Found this: {date} {time}")

            line = fichier.readline()
    print("FInished")


def compare_date(date1, date2):
    # Return the diff in second between the two dates
    f_date1 = time.strptime(date1, "%Y-%m-%d %H:%M:%S")
    f_date2 = time.strptime(date2, "%Y-%m-%d %H:%M:%S")
    diff = time.mktime(f_date1) - time.mktime(f_date2)
    return diff


def closest(lst, k):
    lst = np.asarray(lst)
    idx = (np.abs(lst - k)).argmin()
    return np.abs(lst[idx] - k)


def find_event_no_data():
    # Open the event file with pandas
    # Open the rssi file and read it line by line until you reach the time of the first event
    # If you pass the time of the event without anything around, there is an issue

    events = pd.read_csv("./data/events.csv")
    curr_event = 0

    events_found = events.copy(deep=True)
    events_not_found = events.copy(deep=True)

    # First read the rssi file and store all the minutes we have
    # We read the second column, convert to time since epoch, then save it in a dic %60
    # Then we read the event and look if there is something close
    list_time = []
    print("Creation of the dic")
    with open("./data/rssi.csv") as file:
        file.readline()
        line = file.readline()
        cpt = 0
        while line:
            if cpt % 50000 == 49999:
                print(f"{cpt+1}")
            cpt += 1
            datetime = line.split(",")[1]
            datetime = time.strptime(datetime, "%Y-%m-%d %H:%M:%S")
            time_epoch = time.mktime(datetime)
            list_time.append(int(time_epoch))
            line = file.readline()
    print("Dic created")

    while curr_event < len(events.index):
        # Open the current file with the date
        print(f"Event: {events.loc[curr_event]['DateTime']}")
        datetime = events.loc[curr_event]['DateTime']
        datetime = time.strptime(datetime, "%Y-%m-%d %H:%M:%S")
        time_epoch = time.mktime(datetime)
        found = False
        best_dist = closest(list_time, time_epoch)
        if best_dist < 300:
            events_not_found = events_not_found[events_not_found.DateTime != events.loc[curr_event]['DateTime']]
        else:
            events_found = events_found[events_found.DateTime != events.loc[curr_event]['DateTime']]
        curr_event += 1

    events_found.to_csv("./data/event_found.csv")
    events_not_found.to_csv("./data/event_not_found.csv")

    print(f"#event found: {len(events_found.index)}")
    print(f"#event not found: {len(events_not_found.index)}")


def average_telegram_per_second(list_tele, list_ts):
    # sometime we have a hole in the data, i.e. no data point for 20 seconds.
    # But the counter for telegram seems to work. So we average the data to avoid stupid results
    new_list = []

    for i in range(1, len(list_ts)):
        time_diff = list_ts[i] - list_ts[i-1]
        if time_diff.total_seconds() != 0:
            tele_ave = list_tele[i] / time_diff.total_seconds()
            new_list.append(tele_ave)

    new_list.insert(0, new_list[0])
    return new_list


def display_single_event():

    index = 10
    time_delta = 5
    events = pd.read_csv("./data/events.csv")
    datetime = events.loc[index]['DateTime']
    date = datetime.split(" ")[0]

    print(f"Analyzing event at date: {datetime}")

    day_data = pd.read_csv(f"./data/prepared_rssi/rssi_{date}.csv")
    day_data['DateTime'] = pd.to_datetime(day_data["DateTime"])

    begin_datetime = pd.to_datetime(datetime) - pd.Timedelta(minutes=time_delta)
    end_datetime = pd.to_datetime(datetime) + pd.Timedelta(minutes=time_delta)

    partial_day = day_data[(day_data['DateTime'] > begin_datetime) & (day_data['DateTime'] < end_datetime)]

    if len(partial_day.index) < 2:
        print(f"There is no data found in the following time frame: [{begin_datetime}:{end_datetime}]")
        return

    np_date = partial_day["DateTime"].tolist()
    np_v = partial_day["A2_RSSI"].tolist()
    # Check the number of valid for the a2 sensor
    np_a2_valid = partial_day["A2_ValidTel"].tolist()
    np_a2_valid = [np_a2_valid[i]-np_a2_valid[i-1] for i in range(1, len(np_a2_valid))]
    np_a2_valid.insert(0, np_a2_valid[0])
    np_a2_valid = average_telegram_per_second(list_tele=np_a2_valid, list_ts=np_date)
    # Check the number of received for the a2 sensor
    np_a2_total = partial_day["A2_TotalTel"].tolist()
    np_a2_total = [np_a2_total[i] - np_a2_total[i - 1] for i in range(1, len(np_a2_total))]
    np_a2_total.insert(0, np_a2_total[0])
    np_a2_total = average_telegram_per_second(list_tele=np_a2_total, list_ts=np_date)

    plt.plot(np_date, np_v, label="Volt")
    plt.plot(np_date, np_a2_valid, label="Valid per second")
    plt.plot(np_date, np_a2_total, label="Total per second")
    plt.legend()
    plt.show()


# splitting_speed_files()
# clean_csv()
# get_mean_v()
# find_event_no_data_2020_09_09()
# find_event_no_data()
display_single_event()
