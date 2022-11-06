#!/usr/bin/env python3
"""
Create .wav files from .ebl files
"""

__license__ = "MIT"
__version__ = "0.0.1"
__debug_mode__ = False

import argparse
from pathlib import Path
from syslog import LOG_LOCAL0

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
            Path(output_dir, "errors").mkdir(parents=True, exist_ok=True)
            i = 1
            for file in directory_dict[key]:
                input_file = Path(file['input_dir'], file['filename'])
                output_file = Path(file['output_dir'], file['filename'])
                print(f"Converting file {i}/{number_files}", end='\r')
                try:
                    convert_file(input_file, file['output_dir'])
                except:
                    print(f"cant read {input_file}... ")
                    if vars(args)['error_save']:
                        Path(output_dir, "errors/", file['filename']).write_bytes(input_file.read_bytes())
                else:
                    i += 1
            print(f"\nConverted {i} files.", end="\n")
    return None
    
            


def validate_directories(input_dir: Path, output_dir: Path) -> None:

    # We shouldn't be creating input dir's.
    # So just do it for outputs. 
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        print("Folder is already there")
    else:
        print("Folder was created")
    finally:
        print(f"Checked dir: {output_dir.name}")
    return None

def convert_file(input_file: Path, output_dir: Path):
    with open(input_file, mode="rb") as file:

        file.seek(0, 2)
        actual_file_size = file.tell()
        file.seek(0, 0)

        # Preliminary File Header is 8 bytes.
        header_1_prefix = (byte := file.read(4))  # "FORM"
        header_1_filesize = int.from_bytes(
            byte := file.read(4), "big"
        )  # FileSize - 8 (i.e how many bytes are left)
        header_1_read = file.tell()

        # Header 2 just contains a size of metadata field. 12 bytes.
        header_2_prefix = (byte := file.read(8))  # "E5B0TOC2"
        header_2_data = int.from_bytes(
            byte := file.read(4), "big"
        )  # Length of the next Chunk. 78.
        header_2_read = file.tell()

        # Header 3 just contains the filename, and an updated metadata size and filesize for something different. 78 bytes (From header_2_data)
        header_3_prefix = (byte := file.read(4))  # "E5S1"
        header_3_filesize = int.from_bytes(
            byte := file.read(4), "big"
        )  # 343480. The Size after "header_4_data" below, i.e byte >= 108
        header_3_data = int.from_bytes(byte := file.read(4), "big")  # ??? 98.
        file.read(2)  # 0's here. No idea why.
        file_name_1 = (byte := file.read(64)).decode(
            "utf-8"
        )  # The following 64 bytes are the track name, more or less encoded utf-8.
        header_3_read = file.tell()

        # Another E5S1 header. 14 bytes. No idea why.
        header_4_prefix = (byte := file.read(4))  # "E5S1"
        header_4_filesize = int.from_bytes(byte := file.read(4), "big")  # 343482
        header_4_data = (byte := file.read(6))  # 256 be, 1 le
        header_4_read = file.tell()

        # Start of Data Chunk 2? 184 bytes to go till start of file.
        file_name_2 = (byte := file.read(64))  # The file name repeated. 64 bytes.
        # Need to read this properly... Unknown if static sizes.
        variable_1 = int.from_bytes(byte := file.read(4), "little")  # Unknown. 301 le

        variable_2 = int.from_bytes(
            byte := file.read(4), "little"
        )  # Data Offset. 184 le
        variable_3 = int.from_bytes(
            byte := file.read(4), "little"
        )  # Data size (including offset). 171832 le. Aka channel 1 is 171832-184 = 171648 bytes.
        variable_4 = int.from_bytes(
            byte := file.read(4), "little"
        )  # Data size - 2 (Not sure why?). 171830
        variable_5 = int.from_bytes(
            byte := file.read(4), "little"
        )  # Close to the end of file. 343478.

        variable_6 = int.from_bytes(
            byte := file.read(4), "little"
        )  # Chanel 1 Data Offset. 184.
        variable_7 = int.from_bytes(
            byte := file.read(4), "little"
        )  # Data size (including offset). 171832
        variable_8 = int.from_bytes(
            byte := file.read(4), "little"
        )  # 184. Start of Audio Data?
        variable_9 = int.from_bytes(
            byte := file.read(4), "little"
        )  # 171832. End of data for this channel?

        variable_10 = int.from_bytes(
            byte := file.read(4), "little"
        )  # Frequency. Typically 44100 (hz)
        variable_11 = int.from_bytes(byte := file.read(4), "little")  # 0. Unknown.
        variable_12 = int.from_bytes(
            byte := file.read(4), "little"
        )  # Unknown but maybe number of channels, bitrate idk.

        data_header_padding = file.read(72)

        channel_size = (
            variable_3 - variable_2 - 4
        )  # How much data is in each channel? We minus 4 to avoid the empty byte.

        actual_header_size = file.tell()
        actual_data_size = actual_file_size - actual_header_size

        channel_1_data = file.read(channel_size)
        data_padding = int.from_bytes(
            byte := file.read(4), "little"
        )  # Should be zeros all the time. LOL
        channel_2_data = file.read(channel_size)

        # print(f"Read file {input_file} - {actual_file_size} Bytes.")
        # print(f"Read {actual_header_size} bytes as header.")
        # print(f"Channel size: {channel_size} bytes.")

        header_1_check = True if header_1_prefix == b"FORM" else False
        header_1_valid = (
            True if header_1_filesize == actual_file_size - header_1_read else False
        )  # Checks if the remaining bytes in header 1 is correct.
        header_2_check = True if header_2_prefix == b"E5B0TOC2" else False
        header_3_check = True if header_3_prefix == b"E5S1" else False
        header_4_check = True if header_4_prefix == b"E5S1" else False
        data_size_valid = True if actual_data_size == (channel_size * 2) + 4 else False

    wav_header_length = 16
    wav_pcm_mode = 1

    # Imported Variables:
    wav_sample_rate = variable_10
    wav_channels = 2
    wav_bps = 16  # No idea from where lol

    # Calculated Variables
    wav_byte_rate = int(
        wav_sample_rate * wav_channels * wav_bps * (1 / 8)
    )  # SampleRate * NumChannels * BitsPerSample/8
    wav_block_align = int(
        wav_channels * wav_bps * (1 / 8)
    )  #  NumChannels * BitsPerSample/8

    # Actual File Data
    if wav_channels == 1:
        wav_data = channel_2_data
    else:
        wav_data = b""
        for i in range(0, channel_size, 2):
            wav_data += channel_1_data[i : i + 2]
            wav_data += channel_2_data[i : i + 2]

    # Size Blocks
    wav_data_size = channel_size * wav_channels
    wav_file_size = wav_data_size + 36

    if vars(args)['no_write']:
        print('Not Writing to disk...')
    else:
        if vars(args)['preserve_filename']:
            xx = input_file.stem + '.wav'
        else:
            xx = file_name_1.replace("\x00", "") + ".wav"
        with open(Path(output_dir, xx), mode="wb") as file:
            file.write(b"RIFF")
            file.write(wav_file_size.to_bytes(4, byteorder="little"))
            file.write(b"WAVE")
            file.write(b"fmt ")
            file.write(
                wav_header_length.to_bytes(4, byteorder="little")
            )  # Write 16 (header length 32 bit)
            file.write(wav_pcm_mode.to_bytes(2, byteorder="little"))  # Write 1 (16 bit)
            file.write(
                wav_channels.to_bytes(2, byteorder="little")
            )  # Write # channels (16 bit)
            file.write(
                wav_sample_rate.to_bytes(4, byteorder="little")
            )  # Write Sample Rate, 32 bit int

            file.write(
                wav_byte_rate.to_bytes(4, byteorder="little")
            )  # write 88200 (32 bit)

            file.write(wav_block_align.to_bytes(2, byteorder="little"))  # Write 4 (16 bit)
            file.write(
                wav_bps.to_bytes(2, byteorder="little")
            )  # Write 16 Bits per sample (16 bit)
            file.write(b"data")
            file.write(
                wav_data_size.to_bytes(4, byteorder="little")
            )  # Write Size of actual audio...
            file.write(wav_data)


def main(input_dir, output_dir, args):
    """Main entry point of the app"""
    print("Starting File Convert")

    if __debug_mode__:
        debug_mode()

    recursive_scan(input_dir)
    #validate_directories(input_dir, output_dir)
    #read_files(input_dir)


if __name__ == "__main__":
    """This is executed when run from the command line"""
    parser = argparse.ArgumentParser()

    default_input_dir = Path.cwd().joinpath("input")
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
