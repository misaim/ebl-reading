#!/usr/bin/env python3.9

"""
CLI Tool to convert E-MU Emulator X-3 EBL files to WAV.
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

__license__ = "MIT"
__version__ = "1.0.0"

import argparse
from pathlib import Path
import time
import ebl

#from syslog import LOG_LOCAL0

def recursive_scan(input_dir: Path, output_dir: Path) -> None:
    print(f"Scanning {input_dir.absolute()}/ ...", end='')
    number_files_total = 0
    number_files_converted = 0

    # Read every EBL file recursively. Assign to a dict with the dir as key, so we can do things on a folder-by-folder basis.
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
    print(f"Done.\nPlanning to process {number_files_total} EBL files in {input_dir}/")

    # Fucks off the "" element (root). Not required by pathlib but looks pretty.
    if "" in directory_dict: 
        directory_dict["/"] = directory_dict[""]
        directory_dict.pop("")
    
    # Run convert_file for every file in each directory.
    start_time = time.perf_counter()
    for key in directory_dict:
        number_files = len(directory_dict[key])
        print(f"{key} - {number_files} file(s).")
        #if not vars(args)['no_write']: 
        output_location = Path(str(output_dir)+key)
        if not ebl.NO_WRITE:
            output_location.mkdir(parents=True, exist_ok=True)
        i = 0
        for file in directory_dict[key]:
            input_file = Path(file['input_dir'], file['filename'])
            #print(f"Converting file {i}/{number_files}", end='\r')
            file_status = ebl.convert_file(input_file, file['output_dir'], Path(output_dir, "errors"))
            if file_status:
                i += 1
                number_files_converted += 1
        print(f"Converted {i} files in folder.", end="\n")

    end_time = time.perf_counter()
    print(f"Converted {number_files_converted}/{number_files_total} files. Duration: {end_time - start_time}s")
    return None

def main(args):
    """Main entry point of the app"""

    ebl.debug(f"DEBUG MODE: {ebl.DEBUG_MODE}, WRITE: {not ebl.NO_WRITE}, ERROR SAVE: {ebl.ERROR_SAVE}")
    
    input_dir = vars(args)['input']
    output_dir = vars(args)['output']

    if output_dir == None:
        output_dir = Path.cwd().joinpath("ebl_read_" + str(int(time.time())))
        print(f"No output directory selected - Defaulting to {output_dir}")

    # Create error folder if we have to.
    if not ebl.NO_WRITE:
        output_dir.mkdir(parents=True, exist_ok=True)
        if ebl.ERROR_SAVE:
            Path(output_dir, "errors").mkdir(parents=True, exist_ok=True)

    if input_dir.is_dir():
        recursive_scan(input_dir, output_dir)
    elif input_dir.is_file():
        if not vars(args)['no_write']:
            if input_dir.suffix == '.ebl':
                file_status = ebl.convert_file(input_dir, output_dir, Path(output_dir, "errors"))
                if file_status:
                    print(f"Converted {input_dir.name}.")
                else:
                    print(f"Failed to convert {input_dir.name}.")
            else:
                print("Input file must be EBL.")
    else:
        print("Input must be a file or directory.")

if __name__ == "__main__":
    """This is executed when run from the command line"""
    parser = argparse.ArgumentParser()
    
    default_input_dir = Path.cwd().joinpath("input")
    default_output_dir = Path.cwd().joinpath("ebl_read_" + str(int(time.time())))

    parser.add_argument(
        "-i", "--input", type=Path, required=True, help="Input File/Directory. Required."
    )

    parser.add_argument(
        "-o", "--output", type=Path, default=default_output_dir, help="Output location. Defaults to CWD."
    )

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
        "-e", "--error_save", action="store_true", default=False, help="If present, save files with errors to /output/errors/"
    )

    # --version output
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__),
    )

    args = parser.parse_args()

    ebl.DEBUG_MODE = True if vars(args)['debug'] else False
    ebl.NO_WRITE = True if vars(args)['no_write'] else False
    ebl.PRESERVE_FILENAME = True if vars(args)['preserve_filename'] else False
    ebl.ERROR_SAVE = True if vars(args)['error_save'] else False

    main(args)
