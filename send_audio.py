import time
import wave
import pyaudio
import random
import time
import multiprocessing
from paho.mqtt import client as mqtt_client

import numpy as np
import scipy.io.wavfile as wavfile
from numpy import pi, polymul
from scipy.signal import bilinear, lfilter
import wave

def read_wav_stream(filename, chunk_size=1024):
    with wave.open(filename, 'rb') as wav_file:
        sample_width = wav_file.getsampwidth()
        num_channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        frames = wav_file.getnframes()

        while True:
            data = wav_file.readframes(chunk_size)
            if not data:
                break

            yield data, sample_rate

def A_weighting(fs):
    """Design of an A-weighting filter.
    fs: Sampling frequency.
    Returns:
        b, a: Coefficients of the A-weighting filter.
    """
    # Definition of analog A-weighting filter according to IEC/CD 1672.
    f1 = 20.598997
    f2 = 107.65265
    f3 = 737.86223
    f4 = 12194.217
    A1000 = 1.9997

    NUMs = [(2 * np.pi * f4) ** 2 * (10 ** (A1000 / 20)), 0, 0, 0, 0]
    DENs = polymul([1, 4 * np.pi * f4, (2 * np.pi * f4) ** 2],
                   [1, 4 * np.pi * f1, (2 * np.pi * f1) ** 2])
    DENs = polymul(polymul(DENs, [1, 2 * np.pi * f3]),
                   [1, 2 * np.pi * f2])

    # Use the bilinear transformation to get the digital filter.
    b, a = bilinear(NUMs, DENs, fs)

    return b, a

def calculate_sound_level(signal):
    # Calculate the squared mean of the signal
    squared_mean = np.mean(np.square(signal))

    # Calculate the sound level (in dB)
    sound_level = 20 * np.log10(squared_mean)

    return sound_level


# broker = 'h771fe96.ala.cn-hangzhou.emqxsl.cn'
# port = 8883
# # generate client ID with pub prefix randomly
# client_id = f'python-mqtt-{random.randint(0, 1000)}'
# username = 'jkloli'
# password = 'jkloli'
# # MQTT主题
# mqtt_topic = "audio_stream"

broker = 'h771fe96.ala.cn-hangzhou.emqxsl.cn'
port = 8883
# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 1000)}'
username = 'jkloli'
password = 'jkloli'
# MQTT主题
mqtt_topic = "audio_stream"



def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.tls_set(ca_certs='/home/a/cpy/cython_tutorial/ch1/2_math/temp/audio/release/emqxsl-ca.crt')
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client




# 录音参数
audio_format = pyaudio.paInt16
channels = 2
old_sample=48000
sample_rate = 16000
chunk_size = 51200
record_duration = 10 # 录音持续时间（秒）
wav_dir="raw_wav"

#
frames = multiprocessing.Queue()
def save_audio():
    print("进入存储")
    buff=[]
    
    while True:

        buff.append(frames.get())
        print(len(buff) * chunk_size / old_sample)
        
        if  len(buff) * chunk_size / old_sample >=  record_duration:

            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"audio_{timestamp}.wav"
            filename=wav_dir+"/"+filename
            print(filename)
            # 创建WAV文件
            wave_file = wave.open(filename, 'wb')
            wave_file.setnchannels(channels)
            wave_file.setsampwidth(pyaudio.get_sample_size(audio_format))
            wave_file.setframerate(sample_rate)

            # 写入音频数据
            wave_file.writeframes(b''.join(buff))

            # 关闭WAV文件
            wave_file.close()

            print(f"音频文件保存为 {filename}")
            buff=[]
        else:
            # print("很小啊")
            # time.sleep(0.05)
            None

import numpy as np
import scipy.signal as signal
def send_audio():

    #创建连接
    # client = connect_mqtt()
    # client.loop_start()

    
    audio = pyaudio.PyAudio()
    info = audio.get_host_api_info_by_index(0) 
    numdevices = info.get('deviceCount') 
    
    exist_mic=[]
    for i in range(0, numdevices): 
        if (audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0: 
            exist_mic.append(   (  i, audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')  )   )
            print("Input Device id ", i, " - ", audio.get_device_info_by_host_api_device_index(0, i).get('name')  ,"channel is " ,audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels'))
    for d,n in exist_mic:
        if n==2:
            input_device_index=d
    print("select device" ,input_device_index )
    # 打开音频流
    stream = audio.open(format=audio_format,
                        channels=channels,
                        rate=old_sample,
                        input=True,
                        input_device_index=input_device_index,
                        frames_per_buffer=chunk_size)

    print("开始录音...")

    b, a = A_weighting(sample_rate)

    while True:
        print("chunk_size",chunk_size)
        
        audio_data = stream.read(chunk_size)

        #降采样
        audio_data = np.frombuffer(audio_data, dtype=np.int16)
        audio_data = signal.resample(audio_data, int(len(audio_data) *  sample_rate / old_sample)).astype(np.int16)

        # sound_level = calculate_sound_level(audio_data)

        # print("SPL:", sound_level)

        filtered_signal = lfilter(b, a, audio_data)

        # Calculate the sound level
        sound_level = calculate_sound_level(filtered_signal)

        print("A-weighted SPL:", sound_level)
        audio_data=audio_data.tostring()


        frames.put(audio_data)
        # print(str(len(frames))+"我有这么大")
        print(len(audio_data))
        # client.publish("audio_stream", audio_data , qos=1)




import os 
# 主程序
if __name__ == '__main__':


    send_audio()

    # #存储音频
    # process1 = multiprocessing.Process(target=save_audio)
    # process1.start()

    

    # #发送音频
    # process2 = multiprocessing.Process(target=send_audio)
    # process2.start()




