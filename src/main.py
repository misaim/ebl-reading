#!/usr/bin/env python3
"""
Create .wav files from .ebl files
"""

__license__ = "MIT"
__version__ = "0.0.1"
__debug_mode__ = False

import argparse
from pathlib import Path
import re
from datetime import timedelta
import time
#from syslog import LOG_LOCAL0

# TODO: import logging
# this is currently BROKEN
def debug_mode(header: dict) -> None:
    print(
        f"Header 1 Tag: {header_1_check}, Header 1 Valid: {header_1_valid}, Read {header_1_read}/8 bytes."
    )
    print(f"Header 2: {header_2_check}, read {header_2_read-header_1_read}/12 bytes.")
    print(
        f"Header 3: {header_3_check}, read {header_3_read-header_2_read}/{header_2_data} bytes."
    )
    print(f"Header 4: {header_4_check}, read {header_4_read-header_3_read}/14 bytes.")
    print(f"Data Size Valid: {data_size_valid}, read {actual_data_size} bytes.")
    return None

def debug(input: str):
    #print('Entered...' + str(DEBUG_MODE))
    if DEBUG_MODE:
        print(input)

def recursive_scan(input_dir: Path) -> None:
    print(f"Scanning {input_dir.absolute()}/ ...", end='')
    number_files_total = 0
    number_files_converted = 0

    directory_dict = {}
    for p in input_dir.rglob("*"):
        if p.suffix == ".ebl":
            number_files_total += 1
            input_dir_suffix = str(p.parent).split(str(input_dir))[1]
            output_dir_stem = Path(str(output_dir) + input_dir_suffix)
            if input_dir_suffix in directory_dict:
                directory_dict[input_dir_suffix].append({'filename': p.name, 'input_dir': p.parent, 'output_dir': output_dir_stem})
            else:
                directory_dict[input_dir_suffix] = [{'filename': p.name, 'input_dir': p.parent, 'output_dir': output_dir_stem}]
    print(f"Done.\nPlanning to process {number_files_total} EBL files.")

    # Fucks off the "" element (root). Not required by pathlib but looks pretty.
    if "" in directory_dict: 
        directory_dict["/"] = directory_dict[""]
        directory_dict.pop("")
    start_time = time.monotonic()
    for key in directory_dict:
        number_files = len(directory_dict[key])
        print(f"\t{key} - {number_files} file(s).")
        if not vars(args)['no_write']: 
            output_location = Path(str(output_dir)+key)
            output_location.mkdir(parents=True, exist_ok=True)
            #Path(output_dir, "errors").mkdir(parents=True, exist_ok=True)
            i = 0
            for file in directory_dict[key]:
                input_file = Path(file['input_dir'], file['filename'])
                #output_file = Path(file['output_dir'], file['filename'])
                #print(f"Converting file {i}/{number_files}", end='\r')
                try:
                    convert_file(input_file, file['output_dir'], Path(output_dir, "errors"))
                except:
                    print(f"ERROR: unable to read {input_file}... ")
                else:
                    i += 1
                    number_files_converted += 1
            print(f"Converted {i} files in folder.", end="\n")
    end_time = time.monotonic()
    print(f"Converted {number_files_converted}/{number_files_total} files. Duration: {timedelta(seconds=end_time - start_time)}")
    return None

def stereo_wav_byte_gen(a1, a2):
    i1 = iter(a1)
    i2 = iter(a2)
    while True:
        for it in i1, i1, i2, i2:
            try:
                yield next(it)
            except StopIteration:
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

def read_ebl_file(input_file: Path, error_dir: Path):
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
        
        #print(str(file['header_3']['filename']))

        # Another E5S1 header. 14 bytes. No idea why.
        file['header_4'] = {
                                'prefix': (byte := file_reader.read(4)),  # "E5S1"
                                'size': int.from_bytes(byte := file_reader.read(4), "big"), # 343482
                                'data': (byte := file_reader.read(6)), # 256 be, 1 le
                                'read': file_reader.tell() - file['read']
                            }
        file['read'] = file_reader.tell()

        # Start of Data Chunk 2? 184 bytes to go till start of file_reader.
        # Need to read this properly... Unknown if static sizes.
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
        #debug(f"Data Size: {file['header_read']}")
        #debug(f"Padding: {data_padding}")
        #debug(f"Header Read: {testing_header_read}, Padding: {file['header_read']}")
        #debug(f"C1: {file['channel_1_size']}, C2: {file['channel_2_size']}")
        #debug(f"C1: {c1}, C2: {c2}")
        #debug(input_file.name)
        #debug(f"C1 s: {file['channel_1_data'][0:8]}")
        #debug(f"WARN: Inconsistent filesize: Read: {end_of_data}, Expected: {file['size']}, Difference: {file['size']-end_of_data}")
        
        if end_of_data != file['size']:
            if (file['size']-end_of_data) != 40:
                print(f"ERROR: Inconsistent filesize: Read: {end_of_data}, Expected: {file['size']}, Difference: {file['size']-end_of_data}")
            else:
                debug("WARN: Found 40 bytes. Additional data header.")
    return file

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

    if vars(args)['no_write']:
        print('Not Writing to disk...')
    else:
        try:
        #if True:
            if vars(args)['preserve_filename']:
                output_file = input_file.stem + '.wav'
            else:
                #output_file = ebl_file['header_3']['filename'].replace("\x00", "") # Dirty Hack to remove problem chars from output file names.
                # Strict rules (Windows friendly)
                output_file = re.sub('[^0-9a-zA-Z\.,:%\-_#]+', '', ebl_file['header_3']['filename']) # This Doesn't work.

                #output_file = output_file.replace("\x22", "") # "
                #output_file = output_file.replace("\x5c", "") # \
                #output_file = output_file.replace("\x2f", "") # /
                #output_file = output_file.replace("\x2a", "") # *
                #output_file = output_file.replace("\x3e", "") # >
                #output_file = output_file.replace("\x3f", "") # ?

                # Some more problem files (on large dataset...)
                #.waved to write T.Bansuri B2
                # Failed to write T.Bansuri C#4♦.wav
                #Failed to write T.Bansuri F#4↕▼♠.wav
                #Failed to write Bon Di L C#3   ↕.wav
                #Failed to write Bon Di L D#3   →.wav
                #Failed to write Bon Di L E3#2 §☼.wav
                #Failed to write Bon Di L A#4   §.wav
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
        except:
            print(f"Failed to write {output_file}")
    return

def convert_file(input_file: Path, output_dir: Path, error_dir: Path):
    try:
        ebl_file = read_ebl_file(input_file, error_dir)
    except:
        print(f'EBL READ ERROR: {input_file.name}')
        if vars(args)['error_save']:
            Path(error_dir, input_file.name).write_bytes(input_file.read_bytes())
    else:
        write_wav(input_file, output_dir, ebl_file)
        

def main(input_dir, output_dir, args):
    """Main entry point of the app"""
    print("Starting File Convert")

    #if __debug_mode__:
    #    debug_mode()
    
    global DEBUG_MODE 
    DEBUG_MODE = True if vars(args)['debug'] else False

    if not vars(args)['no_write']: Path(output_dir, "errors").mkdir(parents=True, exist_ok=True)
    
    if input_dir.is_dir():
        recursive_scan(input_dir)
    elif input_dir.is_file():
        if not vars(args)['no_write']:
            convert_file(input_dir, output_dir, Path(output_dir, "errors"))
    else:
        print("Please select a real file or folder!")

if __name__ == "__main__":
    """This is executed when run from the command line"""
    parser = argparse.ArgumentParser()

    default_input_dir = Path.cwd().joinpath("input")
    #default_input_dir = Path("src/input/test.ebl") # Testing Single File Input
    default_output_dir = Path.cwd().joinpath("output")

    # input_dir = parser.add_argument("input_dir", action="store")
    input_dir = default_input_dir

    # output_dir = parser.add_argument("output_dir", action="store")
    output_dir = default_output_dir

    # --debug y/n
    parser.add_argument(
        "-d", "--debug", action="store_true", default=False, help="Debug <True|False>"
    )

    parser.add_argument(
        "-p", "--preserve_filename", action="store_true", default=False, help="Preserve Original Filenames."
    )

    parser.add_argument(
        "-n", "--no_write", action="store_true", default=False, help="Don't write to disk."
    )

    parser.add_argument(
        "-e", "--error_save", action="store_true", default=False, help="Save errors to /errors/"
    )

    # --version output
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__),
    )

    args = parser.parse_args()
    main(input_dir, output_dir, args)
