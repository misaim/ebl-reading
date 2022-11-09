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

def recursive_scan(input_dir: Path) -> None:
    print(f"Scanning {input_dir.absolute()}/ ...", end='')
    directory_dict = {}
    for p in input_dir.rglob("*"):
        if p.suffix == ".ebl":
            input_dir_suffix = str(p.parent).split(str(input_dir))[1]
            output_dir_stem = Path(str(output_dir) + input_dir_suffix)
            if input_dir_suffix in directory_dict:
                directory_dict[input_dir_suffix].append({'filename': p.name, 'input_dir': p.parent, 'output_dir': output_dir_stem})
            else:
                directory_dict[input_dir_suffix] = [{'filename': p.name, 'input_dir': p.parent, 'output_dir': output_dir_stem}]
    print("Done.")

    # Fucks off the "" element (root). Not required by pathlib but looks pretty.
    if "" in directory_dict: 
        directory_dict["/"] = directory_dict[""]
        directory_dict.pop("")

    for key in directory_dict:
        number_files = len(directory_dict[key])
        print(f"\t{key} - {number_files} file(s).")
        if not vars(args)['no_write']: 
            output_location = Path(str(output_dir)+key)
            output_location.mkdir(parents=True, exist_ok=True)
            #Path(output_dir, "errors").mkdir(parents=True, exist_ok=True)
            i = 1
            for file in directory_dict[key]:
                input_file = Path(file['input_dir'], file['filename'])
                #output_file = Path(file['output_dir'], file['filename'])
                print(f"Converting file {i}/{number_files}", end='\r')
                try:
                    convert_file(input_file, file['output_dir'], Path(output_dir, "errors"))
                except:
                    print(f"cant read {input_file}... ")
                else:
                    i += 1
            print(f"\nConverted {i} files.", end="\n")
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
                                "size": file_reader.tell()
                            }
        file['read'] = file_reader.tell()

        # Header 2 just contains a size of metadata field. 12 bytes.
        file['header_2'] = {
                                "prefix": (byte := file_reader.read(8)),  # "E5B0TOC2"
                                "next_header_bytes": int.from_bytes(byte := file_reader.read(4), "big"), # Length of the next Chunk??? 78.
                                "read": file_reader.tell()# - file['read']
                            }
        file['read'] = file_reader.tell()

        # Header 3 just contains the filename, and an updated metadata size and filesize for something different. 78 bytes (From header_2_data)
        file['header_3'] = {
                                "prefix": (byte := file_reader.read(4)), # "E5S1"
                                "data_size": int.from_bytes(byte := file_reader.read(4), "big"), # 343480. The Size after "header_4_data" below, i.e byte >= 108
                                "data": int.from_bytes(byte := file_reader.read(4), "big"),  # ??? 98
                                "zeros": file_reader.read(2), # 0's here. No idea why.
                                "filename": (byte := file_reader.read(64)).decode("utf-8"), # The following 64 bytes are the track name, more or less encoded utf-8.
                                "read": file_reader.tell()
                            }
        file['read'] = file_reader.tell()

        # Another E5S1 header. 14 bytes. No idea why.
        file['header_4'] = {
                                'prefix': (byte := file_reader.read(4)),  # "E5S1"
                                'size': int.from_bytes(byte := file_reader.read(4), "big"), # 343482
                                'data': (byte := file_reader.read(6)), # 256 be, 1 le
                                'read': file_reader.tell()
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
                                'v10': int.from_bytes(byte := file_reader.read(4), "little"),# Frequency. Typically 44100 (hz)
                                'v11': int.from_bytes(byte := file_reader.read(4), "little"),# 0. Unknown.
                                'v12': int.from_bytes(byte := file_reader.read(4), "little"),# Unknown but maybe number of channels, bitrate idk.
                                'padding': file_reader.read(72),
                                'read': file_reader.tell()
        }
        file['read'] = file_reader.tell()
        file['header_read'] = file['read']

        # How much data is in each channel? We minus 4 to avoid the empty byte.
        file['channel_1_size'] = (file['header_data']['v4'] - 186)
        file['channel_2_size'] = (file['header_data']['v5'] - file['header_data']['v4'] - 4)

        file['channel_2_size'] = 0 if file['channel_2_size'] == -4 else file['channel_2_size']
        
        file['data_size'] = file['size'] - file['header_read']

        file['channel_1_data'] = file_reader.read(file['channel_1_size'])
        data_padding = int.from_bytes(
            byte := file_reader.read(4), "little"
        )  # Should be zeros all the time. LOL
        file['channel_2_data'] = file_reader.read(file['channel_2_size'])

        #header_1_check = True if file['header_1']['prefix'] == b"FORM" else False
        #header_1_valid = (
        #    True if file['header_1']['filesize'] == file['size'] - file['header_1']['size'] else False
        #)  # Checks if the remaining bytes in header 1 is correct.
        #header_2_check = True if file['header_2']['prefix'] == b"E5B0TOC2" else False
        #header_3_check = True if file['header_2']['prefix'] == b"E5S1" else False
        #header_4_check = True if file['header_4']['prefix'] == b"E5S1" else False
        #data_size_valid = True if file['data_size'] == (channel_size * 2) + 4 else False
    return file


def convert_file(input_file: Path, output_dir: Path, error_dir: Path):
    try:
        ebl_file = read_ebl_file(input_file, error_dir)
    except:
        print(f'EBL READ ERROR: {input_file.name}')
        if vars(args)['error_save']:
            Path(error_dir, input_file.name).write_bytes(input_file.read_bytes())
    else:
        wav_header_length = 16
        wav_pcm_mode = 1

        # Imported Variables:
        wav_sample_rate = ebl_file['header_data']['v10']
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
                if vars(args)['preserve_filename']:
                    output_file = input_file.stem + '.wav'
                else:
                    output_file = ebl_file['header_3']['filename'].replace("\x00", "") # Dirty Hack to remove problem chars from output file names.
                    #output_file = re.sub('[^A-Za-z0-9 #-_]+', '', output_file) # This Doesn't work.
                    output_file = output_file.replace("\x22", "") # "
                    output_file = output_file.replace("\x5c", "") # \
                    output_file = output_file.replace("\x2f", "") # /
                    output_file = output_file.replace("\x2a", "") # *
                    output_file = output_file.replace("\x3e", "") # >
                    output_file = output_file.replace("\x3f", "") # ?
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



def main(input_dir, output_dir, args):
    """Main entry point of the app"""
    print("Starting File Convert")

    if __debug_mode__:
        debug_mode()

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
        "-d", "--debug", action="count", default=False, help="Debug <True|False>"
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
