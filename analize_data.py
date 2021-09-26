# This is the second file used to analyze the data.
# The function try to extract some information and create images or gif to visualize the data over a single day
# or over several days


import pandas as pd
import numpy as np
from os.path import exists, isfile, join
from os import listdir, remove
import time
import matplotlib.pyplot as plt
import imageio


def interpolate_volt_position(list_v, list_position):

    pos_v, sum_v = {}, {}
    max_pos, min_pos = 0, 10000000
    # Create a dictionary with all positions and the sum of the V for each position
    for v, pos in zip(list_v, list_position):
        max_pos = max(max_pos, pos)
        min_pos = min(min_pos, pos)
        if pos in pos_v:
            pos_v[pos] += v
            sum_v[pos] += 1
        else:
            pos_v[pos] = v
            sum_v[pos] = 1
    # Create an interpolated value for each point
    new_v, new_pos = [-1 for x in range(min_pos, max_pos + 1)], [x for x in range(min_pos, max_pos + 1)]
    # Correct the sum for each position to the mean for each position
    for key in pos_v:
        pos_v[key] /= sum_v[key]
        new_v[key-min_pos] = pos_v[key]

    curr_pos, next_pos = 0, 1
    while curr_pos < len(new_v) and next_pos < len(new_v):
        while new_v[next_pos] == -1:  # we should never get out of this table like that
            next_pos += 1
        val1, val2 = new_v[curr_pos], new_v[next_pos]
        for i in range(curr_pos+1, next_pos):
            cur_val = (val1*(next_pos-i) + val2*(i-curr_pos))/(next_pos-curr_pos)
            new_v[i] = cur_val
        curr_pos = next_pos
        next_pos = next_pos + 1

    return new_v, new_pos


def find_low_voltage(date):

    # We open the file containing the data of the given date
    # We extract the voltage and the time stamp
    # We interpolate per second if the time diff is less than 2 minutes.
    # We compute the mean and std dev.
    # We check for drop below mean-std_dev or below 1.2/1.6 volt for more than x seconds.

    min_v = 1.3  # This is the minimum voltage to have a decent signal (can be changed)
    min_streak = 100  # Number of 1/10 of meter to start worrying

    dataset = pd.read_csv(f"./data/prepared_rssi/rssi_{date}.csv")

    list_pos = dataset["PositionNoLeap"].tolist()
    list_v = dataset["A2_RSSI"].tolist()

    list_v, list_pos = interpolate_volt_position(list_v, list_pos)

    mean_v = np.mean(list_v)
    std_v = np.std(list_v)

    print(f"Mean: {mean_v}, std: {std_v}")

    curr_pos, begin_streak, size_streak = 0, 0, 0
    list_streak = []

    while curr_pos < len(list_v):
        if list_v[curr_pos] > mean_v - std_v and list_v[curr_pos] > min_v:  # Signal is good enough
            if size_streak >= min_streak:
                list_streak.append([begin_streak, begin_streak+size_streak])
                size_streak = 0
        else:
            if size_streak == 0:
                begin_streak = list_pos[curr_pos]
            size_streak += 1
        curr_pos += 1

    print(f"Did we find streak: {len(list_streak)}")
    for streak in list_streak:
        print(f"\t{streak}")


def remove_emergency_brake():
    # In the file disruption.csv, we have a huge amount of emergency brakes.
    # But in fact most of them are when the train is not moving, i.e. the driver is testing the brakes, and it is
    # logged in the file.
    # Here, I will try to remove them.

    time_delta = 8

    file_disruptions = pd.read_csv("./data/disruptions.csv")
    file_disruptions['DateTime'] = pd.to_datetime(file_disruptions["DateTime"])

    date_open = "2020-02-08"
    file_data = pd.read_csv(f"./data/prepared_rssi/rssi_{date_open}.csv")
    file_data['DateTime'] = pd.to_datetime(file_data["DateTime"])

    out_list = []

    curr_disruption = 0
    while curr_disruption < len(file_disruptions.index):
        date_disruption = file_disruptions.loc[curr_disruption]["DateTime"]
        date = str(date_disruption).split(" ")[0]
        # Check we have the proper file open
        if date != date_open:
            date_open = date
            curr_path = f"./data/prepared_rssi/rssi_{date_open}.csv"
            if not exists(curr_path):
                curr_disruption += 1
                continue
            file_data = pd.read_csv(curr_path)
            file_data['DateTime'] = pd.to_datetime(file_data["DateTime"])
        # Extract data around the time of the event
        begin_datetime = pd.to_datetime(date_disruption) - pd.Timedelta(seconds=time_delta)
        end_datetime = pd.to_datetime(date_disruption) + pd.Timedelta(seconds=time_delta)
        partial_day = file_data[(file_data['DateTime'] > begin_datetime) & (file_data['DateTime'] < end_datetime)]

        if len(partial_day.index) < 2:  # No data to check we skip it
            curr_disruption += 1
            continue
        # Extract the different position, check if we moved more than let say 10m
        list_positions = partial_day["PositionNoLeap"].tolist()
        vmin, vmax = min(list_positions), max(list_positions)
        if vmax-vmin > 150:  # We keep this one, the train is moving
            out_list.append(file_disruptions.loc[curr_disruption].tolist())
        curr_disruption += 1

    print(f"Size of the output: {len(out_list)}")

    out_csv = pd.DataFrame(out_list, columns=['ID', 'DateTime' ,'DisruptionCode', 'Description'])
    out_csv.to_csv("./data/new_disruption.csv", index=False)


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


def create_single_graphic(time_frame, title, file):
    # plt.figure().clear()
    plt.close("all")

    plt.figure(figsize=(14, 6), dpi=100)

    np_date = time_frame["DateTime"].tolist()
    np_v = time_frame["A2_RSSI"].tolist()
    # Check the number of valid for the a2 sensor
    np_a2_valid = time_frame["A2_ValidTel"].tolist()
    np_a2_valid = [np_a2_valid[i] - np_a2_valid[i - 1] for i in range(1, len(np_a2_valid))]
    np_a2_valid.insert(0, np_a2_valid[0])
    np_a2_valid = average_telegram_per_second(list_tele=np_a2_valid, list_ts=np_date)
    # Check the number of received for the a2 sensor
    np_a2_total = time_frame["A2_TotalTel"].tolist()
    np_a2_total = [np_a2_total[i] - np_a2_total[i - 1] for i in range(1, len(np_a2_total))]
    np_a2_total.insert(0, np_a2_total[0])
    np_a2_total = average_telegram_per_second(list_tele=np_a2_total, list_ts=np_date)

    plt.plot(np_date, np_v, label="Volt")
    plt.plot(np_date, np_a2_valid, label="Valid per second")
    plt.plot(np_date, np_a2_total, label="Total per second")
    plt.legend()
    plt.title(title)
    plt.savefig(file)


def create_all_graphics():
    # Simple, I read the new disruption file
    # I read the file of data of the day if it exists
    # I extract for each event, the timeframe from the data.
    # I plot everything and save it in a file,

    time_delta = 60
    list_events = pd.read_csv("./data/new_disruption.csv")
    list_events['DateTime'] = pd.to_datetime(list_events["DateTime"])

    out_csv = []

    curr_event = 0
    while curr_event < len(list_events.index):
        event_id = list_events.loc[curr_event]["ID"]
        event_time = list_events.loc[curr_event]['DateTime']
        event_date = str(event_time).split(" ")[0]
        print(f"Creating:{event_id}")

        day_data = pd.read_csv(f"./data/prepared_rssi/rssi_{event_date}.csv")
        day_data['DateTime'] = pd.to_datetime(day_data["DateTime"])

        begin_datetime = pd.to_datetime(event_time) - pd.Timedelta(seconds=time_delta)
        end_datetime = pd.to_datetime(event_time) + pd.Timedelta(seconds=time_delta)

        time_frame = day_data[(day_data['DateTime'] > begin_datetime) & (day_data['DateTime'] < end_datetime)]
        event_title = f"[{list_events.loc[curr_event]['ID']}] {list_events.loc[curr_event]['DateTime']}\n"
        event_title += f"{list_events.loc[curr_event]['Description']},{day_data.iloc[-1]['PositionNoLeap']}\n"
        event_title += f"[{day_data.iloc[-1]['Latitude']},{day_data.iloc[-1]['Longitude']}]"
        out_file = f"./data/graphics/{event_id}.png"
        create_single_graphic(time_frame=time_frame, title=event_title, file=out_file)

        out_csv.append([list_events.loc[curr_event]['ID'], list_events.loc[curr_event]['DateTime'],
                        list_events.loc[curr_event]['Description'], day_data.iloc[-1]['PositionNoLeap'],
                        day_data.iloc[-1]['Latitude'], day_data.iloc[-1]['Longitude']])

        curr_event += 1

    out_csv = pd.DataFrame(out_csv, columns=['ID', 'DateTime', 'Description', 'PositionNoLeap',
                                             'Latitude', 'Longitude'])
    out_csv.to_csv("./data/disruption_coordinates.csv", index=False)


def create_single_graph(date, position, id, description, cpt):

    # Open the file containing a given day.
    # Find the moment the train get to a given position (more or less).
    # Extract the 60 second before and after.
    # Create the image

    day_data = pd.read_csv(f"./data/prepared_rssi/rssi_{date}.csv")
    day_data['DateTime'] = pd.to_datetime(day_data["DateTime"])

    curr_pos = 0
    time_delta = 60

    while curr_pos < len(day_data.index)-1:
        pos_1 = day_data.loc[curr_pos]['PositionNoLeap']
        pos_2 = day_data.loc[curr_pos+1]['PositionNoLeap']
        if pos_1 <= position <= pos_2 or pos_1 >= position >= pos_2:
            # We found the position.
            event_time = day_data.loc[curr_pos]['DateTime']
            begin_datetime = pd.to_datetime(event_time) - pd.Timedelta(seconds=time_delta)
            end_datetime = pd.to_datetime(event_time) + pd.Timedelta(seconds=time_delta)
            time_frame = day_data[(day_data['DateTime'] > begin_datetime) & (day_data['DateTime'] < end_datetime)]
            event_title = f"[{id}] {event_time}\n{description}, {position}\n"
            event_title += f"[{day_data.iloc[curr_pos]['Latitude']},{day_data.iloc[curr_pos]['Longitude']}]"
            out_file = f"./data/gifs/temps/{id}_{cpt}.png"
            create_single_graphic(time_frame=time_frame, title=event_title, file=out_file)
            break
        curr_pos += 1


def draw_animation():
    # Ok so the idea is simple
    # We open the event leading to an emergency break.
    # We open the files for the days before the issue.
    # We get the data frame that happened at the same region on the track.
    # We create an image for each of them.
    # We create a gif from all images

    list_events = pd.read_csv("./data/disruption_15.csv")
    list_events['DateTime'] = pd.to_datetime(list_events["DateTime"])
    curr_event = 0

    while curr_event < len(list_events.index):
        event_time = list_events.loc[curr_event]["DateTime"]
        event_id = list_events.loc[curr_event]["ID"]
        event_description = list_events.loc[curr_event]["Description"]
        event_location = None
        event_date = str(event_time).split(" ")[0]
        day_data = pd.read_csv(f"./data/prepared_rssi/rssi_{event_date}.csv")
        day_data['DateTime'] = pd.to_datetime(day_data["DateTime"])
        # Find the approx location of the event.
        curr_day = 0
        while curr_day < len(day_data.index-1):
            if day_data.loc[curr_day]["DateTime"] <= event_time <= day_data.loc[curr_day+1]["DateTime"]:
                event_location = day_data.loc[curr_day]["PositionNoLeap"]
                break
            curr_day += 1
        print(f"location: {event_location}")
        if event_location is None:
            print("None")
            continue
        print("Creating event image")
        create_single_graph(event_date, event_location, event_id, event_description, 0)
        cpt = 1
        for i in range(1, 11):
            new_event_time = pd.to_datetime(event_time) - pd.Timedelta(days=i)
            new_event_date = str(new_event_time).split(" ")[0]
            print(f"New date: {new_event_date}")
            if exists(f"./data/prepared_rssi/rssi_{new_event_date}.csv"):
                create_single_graph(new_event_date, event_location, event_id, event_description, cpt)
                cpt += 1
        # Now create the gif and remove the temp images
        temp_path = './data/gifs/temps/'
        onlyfiles = [f for f in listdir(temp_path) if isfile(join(temp_path, f))]
        onlyfiles.sort()
        out_name = f"./data/gifs/{event_id}.gif"
        list_images = []
        for file in onlyfiles:
            list_images.append(imageio.imread(temp_path + file))
        imageio.mimsave(out_name, list_images, format='GIF', fps=1)

        for file in onlyfiles:
            remove(temp_path+file)

        curr_event += 1


def extract_couple_message_brake():
    # Count how many time we have the brake with the lack of message

    events = pd.read_csv("./data/disruptions.csv")
    curr_event = 0
    cpt = 0

    list_keep = []

    while curr_event < len(events.index)-1:

        curr_date = events.loc[curr_event]["DateTime"]
        next_date = events.loc[curr_event+1]["DateTime"]
        if curr_date == next_date:
            event_1 = events.loc[curr_event]["Description"]
            event_2 = events.loc[curr_event+1]["Description"]
            if event_1.find("Linienleitertelegramme") != -1 and event_2.find("Zwangsbremse") != -1:
                print(f"Date:{curr_date}: double event")
                code_1 = events.loc[curr_event]["DisruptionCode"]
                code_2 = events.loc[curr_event+1]["DisruptionCode"]
                id1 = events.loc[curr_event]["ID"]
                id2 = events.loc[curr_event+1]["ID"]
                list_keep.append([id1, curr_date, code_1, event_1])
                list_keep.append([id2, curr_date, code_2, event_2])
                cpt += 1
        curr_event += 1

    print(f"Number of double event: {cpt}")

    out_csv = pd.DataFrame(list_keep, columns=['ID', 'DateTime', 'DisruptionCode', 'Description'])
    out_csv.to_csv("./data/disruption_15.csv", index=False)


# remove_emergency_brake()
# find_low_voltage("2021-06-22")
# create_all_graphics()
draw_animation()
# extract_couple_message_brake()