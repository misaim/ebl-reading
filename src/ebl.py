#!/usr/bin/env python3.9

"""
Convert E-MU Emulator X-3 EBL files to WAV.
"""

"""
MIT License

Copyright (c) 2022 https://github.com/misaim

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from pathlib import Path
import re

global DEBUG_MODE
global NO_WRITE
global PRESERVE_FILENAME
global ERROR_SAVE

DEBUG_MODE = False
NO_WRITE = False
PRESERVE_FILENAME = False
ERROR_SAVE = False

def debug(input: str):
    if DEBUG_MODE:
        print(input)

def valid():
    return False

# Read, and then attempt to Write an EBL file. 
def convert_file(input_file: Path, output_dir: Path, error_dir: Path):
    try:
        ebl_file = read_file(input_file, error_dir)
    except:
        print(f'EBL READ ERROR: {input_file.name}')
        if ERROR_SAVE:
            Path(error_dir, input_file.name).write_bytes(input_file.read_bytes())
    else:
        try:
            write_wav(input_file, output_dir, ebl_file)
        except:
            print(f"WAV WRITE ERROR:{input_file.name}")
            if ERROR_SAVE:
                Path(error_dir, input_file.name).write_bytes(input_file.read_bytes())
        else:
            return True
    return False
        
# This bad boy can read so many EBL files. 
def read_file(input_file: Path, error_dir: Path):
    file = {"filename": input_file.name, "path": input_file, "read": 0, "size": 0}
    with open(input_file, mode="rb") as file_reader:
        file_reader.seek(0, 2)
        file['size'] = file_reader.tell()
        file_reader.seek(0, 0)

        # Preliminary File Header is 8 bytes.
        file['header_1'] = {
                                "prefix": (byte := file_reader.read(4)), # "FORM"
                                "filesize": int.from_bytes(byte := file_reader.read(4), "big"), # FileSize - 8 (i.e how many bytes are left)
                                "read": file_reader.tell()
                            }
        file['read'] = file_reader.tell()

        # Header 2 just contains a size of metadata field. 12 bytes.
        file['header_2'] = {
                                "prefix": (byte := file_reader.read(8)),  # "E5B0TOC2"
                                "next_header_bytes": int.from_bytes(byte := file_reader.read(4), "big"), # Length of the next Chunk??? 78.
                                "read": file_reader.tell() - file['read']
                            }
        file['read'] = file_reader.tell()

        # Header 3 just contains the filename, and an updated metadata size and filesize for something different. 78 bytes (From header_2_data)
        file['header_3'] = {
                                "prefix": (byte := file_reader.read(4)), # "E5S1"
                                "data_size": int.from_bytes(byte := file_reader.read(4), "big"), # 343480. The Size after "header_4_data" below, i.e byte >= 108
                                "data": int.from_bytes(byte := file_reader.read(4), "big"),  # ??? 98
                                "zeros": file_reader.read(2), # 0's here. No idea why.
                                "filename": str((byte := file_reader.read(64)).decode("utf-8")), # The following 64 bytes are the track name, more or less encoded utf-8.
                                "read": file_reader.tell() - file['read']
                            }
        file['read'] = file_reader.tell()

        header_3_padding = file['header_3']['data'] - file['read']
        if header_3_padding > 0:
            file['padding'] = header_3_padding
            file_reader.read(header_3_padding)
            #debug(f"{file['read']} After Header 3, should be {file['header_3']['data']}, needing {header_3_padding} bytes of padding.")
        else:
            file['padding'] = 0

        # Another E5S1 header. 14 bytes. No idea why.
        file['header_4'] = {
                                'prefix': (byte := file_reader.read(4)),  # "E5S1"
                                'size': int.from_bytes(byte := file_reader.read(4), "big"), # 343482
                                'data': (byte := file_reader.read(6)), # 256 be, 1 le
                                'read': file_reader.tell() - file['read']
                            }
        file['read'] = file_reader.tell()

        # Start of Data Chunk 2
        file['header_data'] = {
                                'filename': (byte := file_reader.read(64)), # The file name repeated. 64 bytes.
                                'v1': int.from_bytes(byte := file_reader.read(4), "little"), # Unknown. 301 le
                                'v2': int.from_bytes(byte := file_reader.read(4), "little"), # Data Offset. 184 le,
                                'v3': int.from_bytes(byte := file_reader.read(4), "little"), # Data size (including offset). 171832 le. Aka channel 1 is 171832-184 = 171648 bytes.
                                'v4': int.from_bytes(byte := file_reader.read(4), "little"), # Data size - 2 (Not sure why?). 171830
                                'v5': int.from_bytes(byte := file_reader.read(4), "little"), # Close to the end of file_reader. 343478.
                                'v6': int.from_bytes(byte := file_reader.read(4), "little"), # Chanel 1 Data Offset. 184.
                                'v7': int.from_bytes(byte := file_reader.read(4), "little"), # Data size (including offset). 171832
                                'v8': int.from_bytes(byte := file_reader.read(4), "little"), # 184. Start of Audio Data?
                                'v9': int.from_bytes(byte := file_reader.read(4), "little"), # 171832. End of data for this channel?
                                'frequency': int.from_bytes(byte := file_reader.read(4), "little"),# Frequency. Typically 44100 (hz)
                                'v11': int.from_bytes(byte := file_reader.read(4), "little"),# 0. Unknown.
                                'v12': int.from_bytes(byte := file_reader.read(4), "little"),# Unknown but maybe number of channels, bitrate idk.
                                'comment': (byte := file_reader.read(64)),
                                'read': file_reader.tell() - file['read']
        }

        # This block was revealed to me in a dream
        file['channel_1_size'] = (file['header_data']['v3'] - file['header_data']['v2'])
        file['channel_2_size'] = (file['header_data']['v5'] - file['header_data']['v4'])  

        if file['channel_1_size'] == file['channel_2_size']:
            #debug("Channels same Length")
            if file['channel_1_size'] == 0:
                #debug(f"MONO DETECTED.")
                file['channel_1_size'] = file['header_data']['v4'] - file['header_data']['v3'] + 2
                file['channel_2_size'] = 0
        else:
            if file['channel_1_size'] * file['channel_2_size'] != 0:
                debug(f"Error: Channels Different length. C1: {file['channel_1_size']}, C2: {file['channel_2_size']}")

        file['data_size_calc'] = file['channel_1_size'] + file['channel_2_size']

        #data_padding = file['header_data']['v2'] - 180 + file['padding'] # v1
        #data_padding = file['header_data']['v2'] - 180 # + file['padding'] # v2
        data_padding = file['header_data']['v5'] - file['data_size_calc'] - 178 # v3. Probably can read 178 somewhere.
        if data_padding > 0:
            #debug(f"READ {data_padding} bytes of data padding!")
            file_reader.read(data_padding)

        file['read'] = file_reader.tell()
        file['header_read'] = file['read']

        file['data_size_est'] = file['size'] - file['header_read']

        file['channel_1_data'] = file_reader.read(file['channel_1_size'])
        file['channel_2_data'] = file_reader.read(file['channel_2_size'])

        end_of_data = file_reader.tell()
        file['read'] = file_reader.tell()

        if end_of_data != file['size']:
            if (file['size']-end_of_data) != 40:
                print(f"ERROR: Inconsistent filesize: Read: {end_of_data}, Expected: {file['size']}, Difference: {file['size']-end_of_data}")
            else:
                debug("WARN: Found 40 bytes. Additional data header.")
    return file

# Small generator to put EBL bytestreams (LLLL... LLLRRRR... RRRR) into WAV format (LLLL RRRR... LLLL RRRR)
def stereo_wav_byte_gen(a1, a2):
    i1 = iter(a1)
    i2 = iter(a2)
    while True:
        for it in i1, i1, i2, i2:
            try:
                yield next(it)
            except StopIteration:
                return

# Write a wav file from a previously read EBL file
def write_wav(input_file: Path, output_dir: Path, ebl_file):
    #ebl_file = dummy_file()

    wav_header_length = 16
    wav_pcm_mode = 1

    # Imported Variables:
    wav_sample_rate = ebl_file['header_data']['frequency']
    wav_channels = 2
    wav_bps = 16  # No idea from where lol
    
    # Calculated Variables
    wav_channels = 1 if ebl_file['channel_2_size'] == 0 else 2

    wav_byte_rate = int(
        wav_sample_rate * wav_channels * wav_bps * (1 / 8)
    )  # SampleRate * NumChannels * BitsPerSample/8
    wav_block_align = int(
        wav_channels * wav_bps * (1 / 8)
    )  #  NumChannels * BitsPerSample/8

    # Actual File Data
    if wav_channels == 1:
        wav_data = ebl_file['channel_1_data']
    else:
        wav_data = bytes(stereo_wav_byte_gen(ebl_file['channel_1_data'], ebl_file['channel_2_data']))

    # Size Blocks
    wav_data_size = ebl_file['channel_1_size'] + ebl_file['channel_2_size']
    wav_file_size = wav_data_size + 36

    if not NO_WRITE:
        if PRESERVE_FILENAME:
            output_file = input_file.stem + '.wav'
        else:
            # Strict rules (Windows friendly)
            output_file = re.sub('[^0-9a-zA-Z\.,:%\-_#]+', '', ebl_file['header_3']['filename']) # This Doesn't work.
            output_file = output_file + ".wav"
        with open(Path(output_dir, output_file), mode="wb") as file_writer:
            file_writer.write(b"RIFF")
            file_writer.write(wav_file_size.to_bytes(4, byteorder="little"))
            file_writer.write(b"WAVE")
            file_writer.write(b"fmt ")
            file_writer.write(
                wav_header_length.to_bytes(4, byteorder="little")
            )  # Write 16 (header length 32 bit)
            file_writer.write(wav_pcm_mode.to_bytes(2, byteorder="little"))  # Write 1 (16 bit)
            file_writer.write(
                wav_channels.to_bytes(2, byteorder="little")
            )  # Write # channels (16 bit)
            file_writer.write(
                wav_sample_rate.to_bytes(4, byteorder="little")
            )  # Write Sample Rate, 32 bit int

            file_writer.write(
                wav_byte_rate.to_bytes(4, byteorder="little")
            )  # write 88200 (32 bit)

            file_writer.write(wav_block_align.to_bytes(2, byteorder="little"))  # Write 4 (16 bit)
            file_writer.write(
                wav_bps.to_bytes(2, byteorder="little")
            )  # Write 16 Bits per sample (16 bit)
            file_writer.write(b"data")
            file_writer.write(
                wav_data_size.to_bytes(4, byteorder="little")
            )  # Write Size of actual audio...
            file_writer.write(wav_data)
    return

def dummy_file():
    test_file = {'header_data': {}, 'header_3': {}}
    test_file['header_data']['frequency'] = 44100
    test_file['channel_1_size'] = 8
    test_file['channel_2_size'] = 16
    test_file['channel_1_data'] = b'\x00\x01\x02\x03\x04\x05\x06\x0F'
    test_file['channel_2_data'] = b'\xE0\xE1\xE2\xE3\xE4\xE5\xE6\xEF\xF0\xF1\xF2\xF3\xF4\xF5\xF6\xFF'
    test_file['header_3']['filename'] = 'C\x004\x00 \x00L\x00F'
    return test_file