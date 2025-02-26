from psychopy import visual, core, event, monitors  # import some libraries from PsychoPy
from psychopy.visual import circle
from psychopy.hardware import keyboard
import os
import numpy as np
import pandas as pd
import json
import websockets
import time
import asyncio
import pickle
import random
import math
import matplotlib.pyplot as plt
from scipy import signal
import numpy
import sys
import shutil
import queue
from copy import deepcopy
numpy.set_printoptions(threshold=sys.maxsize)

##  Hyper-parameter

subject_name = "Francis_sep_6_long_test"
data_path = "data/" + subject_name
if os.path.exists(data_path):
    shutil.rmtree(data_path)
os.mkdir(data_path)

##
# Experiment Structure
## 

# define how many sections to collect data
global section_nums

# initialize both section and phase into 0
global current_section

# other global variables 
global listen_num
global experiment_num
global initTime
global instruction
global q
global run
global testison
global iterator
global open_data_holder
global close_data_holder
global rest_data_holder

############################################################

async def wait_until_i_larger_than_j(i, j, t):
    while i <= j:
        # print("i is {}, j is {}".format(i,j))
        await asyncio.sleep(t)
        
############################################################

# function to listen to wristband return data holder object
async def listen():
    url = 'ws://127.0.0.1:9999'
    global q
    global listen_num
    global concatenating
    global instruction
    async with websockets.connect(url) as ws:
        # begin data stream from wristband
        await ws.send(json.dumps({
            "api_version": "0.12",
            "api_request": {
                "request_id": 1,
                "start_stream_request": {
                    "stream_id": "test_stream_id",
                    "app_id": "my-application",
                    "raw_emg": {}
                }
            }
        }))  # start data stream
        global testison
        global run
        result = await ws.recv()  # get rid of junk from first call to ws.recv()
        while run:
            result = await ws.recv()  # read data from wristband
            instruction_curr = instruction
            temp = json.loads(result)  # convert into readable format
            # samples is a nested list which is indexed as samples[data batch][data type]
            #   data batch: data from all channels collected at a single timepoint (timestamp_s); batch is indexed from
            #               0 to Nsamples-1
            #   data type: either raw emg data or two different timestamps, indexed as one of the below fields
            #              'data': the raw emg data; this is further indexed by channel from 0 to 15
            #              'timestamp_s': the time at which the data batch was collected
            #              'produced_timestamp_s': I think this is the time that ws.recv() is called, but not sure

            samples = temp['stream_batch']['raw_emg']['samples']
            Nsamples = len(samples)
            channel = np.zeros([Nsamples, 21])
            for j in range(Nsamples):
                channel[j, 0:16] = samples[j]['data']
                channel[j, 16] = instruction_curr
                channel[j, 17] = samples[j]['timestamp_s']-initTime  # signal time
                channel[j, 18] = samples[j]['produced_timestamp_s']-initTime  # Batch time
            if listen_num > 1:
                batch_start_time = samples[0]['timestamp_s']
                time_between = batch_start_time - batch_finished_time
                if time_between > 0.0006:
                    print("dataloss in listen")
            batch_finished_time = samples[Nsamples - 1]['timestamp_s']
            # delete later
            if testison:
                print("TEMP this is")
                print(temp)
                print("Channel this is")
                print(channel)
            testison = False
            q.put(deepcopy(channel))
            listen_num = listen_num + 1
            if q.qsize() > 7:
                print("--------------------warning, q size is {}------------------------".format(q.qsize()))
        await ws.send(json.dumps({
            "api_version": "0.12",
            "api_request": {
                "request_id": 1,
                "end_stream_request": {
                    "stream_id": "test_stream_id",
                }
            }
        }))

#################################################################

async def experiment():
    global q
    global listen_num, data_holder
    global experiment_num
    global concatenating
    global run
    global current_section
    global open_data_holder
    global close_data_holder
    global rest_data_holder
    while run:
        while listen_num <= experiment_num:
            await asyncio.sleep(0.0005)
        experiment_num = experiment_num + 1
        # quit button
        keys = event.getKeys(keyList=['escape'])
        if keys:
            core.quit()
        while q.qsize() == 0:
            await asyncio.sleep(0.0005)
        mdata = q.get()
        curr_instruction = mdata[0][16]

        # Save data

        if curr_instruction == 1:
            rest_data_holder = np.vstack((rest_data_holder,  mdata))

        if curr_instruction == 2:
            open_data_holder = np.vstack((open_data_holder,  mdata))

        if curr_instruction == 0:
            close_data_holder = np.vstack((close_data_holder,  mdata))
        
        # Move Section 
        if iterator != current_section:

            # Make Section directory first. 

            section_path = data_path + "/Section_Number_" + str(current_section)
            if os.path.exists(section_path):
                shutil.rmtree(section_path)
            os.mkdir(section_path)

            # Save Open Data
            open_csv_data_path = data_path + "/Section_Number_" + str(current_section) + "/open.csv"
            df = pd.DataFrame(data = open_data_holder, columns = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11', 'C12',
                               'C13', 'C14', 'C15', 'C16', 'Instruction', 'Signal_Time', 'Batch_time','X','Y'])
            df.to_csv(open_csv_data_path,mode='a',header=False, index=False)

            # Save Close Data
            close_csv_data_path = data_path + "/Section_Number_" + str(current_section) + "/close.csv"
            df = pd.DataFrame(data = close_data_holder, columns = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11', 'C12',
                               'C13', 'C14', 'C15', 'C16', 'Instruction', 'Signal_Time', 'Batch_time','X','Y'])
            df.to_csv(close_csv_data_path,mode='a',header=False, index=False)

            # Save Rest Data
            rest_csv_data_path = data_path + "/Section_Number_" + str(current_section) + "/rest.csv"
            df = pd.DataFrame(data = rest_data_holder, columns = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11', 'C12',
                                'C13', 'C14', 'C15', 'C16', 'Instruction', 'Signal_Time', 'Batch_time','X','Y'])
            df.to_csv(rest_csv_data_path,mode='a',header=False, index=False)

            # update section number 
            current_section = iterator

            # clean up data holder array 
            open_data_holder = np.empty((1,21))
            rest_data_holder = np.empty((1,21))
            close_data_holder = np.empty((1,21))



# The screen prints out instructions on how to move. The functions gets data by changing the  variable "instruction"
# -1 means no data should be collected
# 0 means close, 1 means rest, 2 means open
async def print_messages():
    global instruction
    # t = 0
    global iterator 
    iterator = 0
    while iterator < section_nums:
        print(f"Section number: {iterator}")
        print("3 ready to OPEN")
        await asyncio.sleep(1)
        print("2")
        await asyncio.sleep(1)
        print("1, start opening")
        await asyncio.sleep(1)
        print("Open")
        instruction = 2
        # take data for 1 s
        await asyncio.sleep(8)  # open
        print("Rest")
        instruction = -1
        await asyncio.sleep(1)
        instruction = 1
        await asyncio.sleep(8)
        instruction = -1
        print("3 ready to CLOSE")
        # take data now for 1s for rest
        await asyncio.sleep(1)
        print("2")
        await asyncio.sleep(1)
        print("1 start to closing")
        await asyncio.sleep(1)
        print("CLOSE")
        instruction = 0
        # take data for 1s
        await asyncio.sleep(8)
        print("Rest")
        instruction = -1
        await asyncio.sleep(2)
        iterator = iterator + 1 
    core.quit()

async def main():
    global listen_num
    global experiment_num
    global initTime
    global instruction
    global q
    global run
    global testison
    global section_nums
    global current_section
    global open_data_holder
    global rest_data_holder
    global close_data_holder
    listen_num = 0
    experiment_num = 0
    instruction = -1
    q = queue.Queue()
    run = True
    testison = False
    initTime = time.time()

    ## How many sections to collect, initialize here
    section_nums = 4

    ## Initialize first phase and first section 
    current_section = 0

    open_data_holder = np.empty((1,21))
    rest_data_holder = np.empty((1,21))
    close_data_holder = np.empty((1,21))
    
    await asyncio.gather(listen(), print_messages(), experiment())

asyncio.get_event_loop().run_until_complete(main())  # run wristband
core.quit()
