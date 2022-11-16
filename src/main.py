#!/usr/bin/env python3
"""
Create .wav files from .ebl files
"""

__license__ = "MIT"
__version__ = "0.0.1"
__debug_mode__ = False

import argparse
from pathlib import Path
from datetime import timedelta
import time
import ebl

#from syslog import LOG_LOCAL0

def recursive_scan(input_dir: Path) -> None:
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
    print(f"Done.\nPlanning to process {number_files_total} EBL files.")

    # Fucks off the "" element (root). Not required by pathlib but looks pretty.
    if "" in directory_dict: 
        directory_dict["/"] = directory_dict[""]
        directory_dict.pop("")
    
    # Run convert_file for every file in each directory.
    start_time = time.perf_counter()
    for key in directory_dict:
        number_files = len(directory_dict[key])
        print(f"{key} - {number_files} file(s).")
        if not vars(args)['no_write']: 
            output_location = Path(str(output_dir)+key)
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

def main(input_dir, output_dir, args):
    """Main entry point of the app"""

    ebl.debug(f"DEBUG MODE: {ebl.DEBUG_MODE}, WRITE: {not ebl.NO_WRITE}, ERROR SAVE: {ebl.ERROR_SAVE}")
    
    # Create error folder if we have to.
    if not ebl.NO_WRITE:
        if ebl.ERROR_SAVE:
            Path(output_dir, "errors").mkdir(parents=True, exist_ok=True)

    # TODO Make this a bit nicer (Ideally add input/output from CLI)
    if input_dir.is_dir():
        recursive_scan(input_dir)
    elif input_dir.is_file():
        if not vars(args)['no_write']:
            ebl.convert_file(input_dir, output_dir, Path(output_dir, "errors"))
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

    ebl.DEBUG_MODE = True if vars(args)['debug'] else False
    ebl.NO_WRITE = True if vars(args)['no_write'] else False
    ebl.PRESERVE_FILENAME = True if vars(args)['preserve_filename'] else False
    ebl.ERROR_SAVE = True if vars(args)['error_save'] else False

    main(input_dir, output_dir, args)
