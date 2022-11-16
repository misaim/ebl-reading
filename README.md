# EBL to WAV Conversion Script
The following is python code to read proprietary E-MU Emulator X-3 EBL files into a more open and accessible format - WAV.

No encoding is being performed - EBL files store channel data in a similar format to WAV, although channels are split in EBL.

Original files are not modified in any way. 

Output filenames are taken from Emulator X-3 specified filenames encoded in header. Disable this with -p (Preserve Filenames).

## Latest test:
Testing on the archive.org 90's Sample CD Archive. Google it. 

Currently:
 - PASS: 42352 Files, 6.49gb
 - WARN: 0 files, 0gb
 - FAIL: 0 Files, 0gb

## Dependencies
Python 3.9+

## License
MIT

## Usage
Takes either a directory or individual file, and writes to an optionally specified output directory.

### Examples

Convert every .ebl file in `/path/to/input/` recursively. Outputs to `CWD/ebl_read_<unix-timestamp>/`, in the same structure as the original files.
    `python3 /path/to/code/main.py -i /path/to/input/`

Convert file.ebl. `Outputs to CWD/<filename>.wav`. Note that `<filename>` is taken from Emulator X-3 specified filenames encoded in header. Disable this with -p (Preserve Filenames).
    `python3 /path/to/code/main.py -i file.wav -o .`

Validate every .ebl file in `/path/to/input/` recursively. Attempts to open every ebl file without converting it, saving errors to `CWD/errors/`. Useful to check for ebl files which can't be read.
    `python3 /path/to/code/main.py -i /path/to/input/ -o . -n -d -e `

Convert every .ebl file in `/path/to/input/` recursively. Outputs to `/path/to/input/`, and removes everything that isn't a WAV. Useful for preparing files for upload, but be careful!
    `python3 /path/to/code/main.py -i /path/to/input/ -o /path/to/input/ && find /path/to/input/ -type f -not -name '*.wav' -delete`

### Options
 - -i: Input (Required). An input ebl file or folder containing preferably ebl files.
 - -o: Output Directory. Resultant output directory. Defaults to `CWD/ebl_read_<unix-timestamp>/`
 - -d: Debug - Prints Debug Messages, mostly EBL file read warnings. Catches extra data header bytes (40).
 - -p: Preserve Filename. Keeps original EBL filename, instead of the metadata encoded filename from Emulator X-3
 - -n: No-Write. Doesn't write anything to disk. Useful for verification of reads.
 - -e: Error Save. Writes files which can't be read to /output/errors/.
        
## EM-U and Emulator X-3
E-mu *was* a software sampler from 1997. They released a number of Sample CD's, containing many small audio files intended to be used with a sampler to make music.

Archive.org has (or had...) a large number of Sample CD's from the 90's and early 2000's archived. While the majority are in WAV format, there are several E-mu specific files that can only be read by Emulator X-3, a depreciated piece of software that is no longer available (You can find a copy on archive.org however, which will run under windows 10).

To avoid a huge job of loading and exporting thousands of files through Emulator X-3, I reverse engineered the EBL file format used by Emulator X-3.

## EBL Documentation
My notes on EBL files. They're pretty simple, with a couple weird tricks (both Big AND Little Endian? In one file?)

### WAVE FILES

WAVE (WAV) files are reasonably simple. For an in-depth explanation [check this out.](http://soundfile.sapp.org/doc/WaveFormat/)

Worth noting that WAV files use Little Endian byte order by default.

In order to write a WAV file, several variables are required to be read from each EBL file:

- The data size on disk (in bytes). Taken from EBL file header.
- Sample Rate. Taken from EBL file header, although typically 44100 (CD quality)
- The filename - encoded as a 64 byte string.
- Number of Channels - Taken from channel size equations. 

We can make assumptions for other variables:

- PCM Mode: Typically 1, for every WAV file ever.
- BitsPerSample: 16. The classic CD quality BPS. There is probably a way to read this from an EBL, but I currently assume it's 16.

### EXB "Files"
Standard "EXB" file structure looks like the following:

    Sample.exb/
      Sample.exb
      SamplePool/
        Sample1.ebl
        Sample1.ebl
        etc...
        
EXB Files contain a copy of file metadata for samples, stored in the SamplePool directory. I didn't find anything useful to convert in EXB files, so I left them alone.

### EBL Files
The following is my notes on EBL file structure.

EBL files are weird - the headers are mostly Big Endian byte order, although the data headers are in Little Endian.

Other then that: They're a Binary file, with audio encoded at 16 bit (as far as I can tell). 

#### Preliminary File Header is 8 bytes.
- header_1_prefix. "FORM"
- header_1_filesize. Big Endian 32 bit int. FileSize - 8 (i.e how many bytes are left from here)

#### Header 2 just contains a size of metadata field. 12 bytes.
- header_2_prefix. "E5B0TOC2"
- header_2_data. Big Endian 32 bit int . Length of the next Chunk. Typically 78.

#### Header 3 just contains the filename, and an updated metadata size and filesize for something different. 78 bytes (From header_2_data)
- header_3_prefix. "E5S1"
- header_3_filesize. Big Endian 32 bit int. The file size following the last E5S1 header.
- header_3_data = Big Endian 32 bit int. No idea what this is for. Typically 98.
- 2 empty bytes.
- file_name_1. 64 bytes, UTF-8 encoded string.
- (Optional) 0-padding. Based on header_2_data length of chunk.

#### Another E5S1 header. 14 bytes. No idea why.
- header_4_prefix. "E5S1"
- header_4_filesize. Big Endian 32 bit int. Remaining bytes following this section - 2.
- header_4_data. 32 bit int, unsure of byte-order. Typically 256 be, 1 le.

#### Start of Data Chunk 2? 184 bytes to go till start of audio data.
- file_name_2. 64 bytes, UTF-8 encoded string.

#### We then have several little endian 32-bit ints.
- variable_1 - Unsure.

- variable_2. Start of Channel 1, offset from byte 10 of E5S1 header 2.
- variable_3. End of Channel 1, offset from byte 10 of E5S1 header 2.
- variable_4. Start of Channel 2, offset from byte 12 of E5S1 header 2.
- variable_5. End of Channel 2, offset from byte 12 of E5S1 header 2.

- variable_6. Unknown and Unused. Could be Channel 1 start replicated but not consistent.
- variable_7. Unknown and Unused. Could be Channel 1 end replicated but not consistent.
- variable_8. Unknown and Unused.
- variable_9. Unknown and Unused.

- variable_10. Frequency. Typically 44100 (hz)
- variable_11. Always 0. Unused.
- variable_12. Unknown but maybe number of channels, bitrate and some other things go here. Unused.

- data_description. 64 bytes, UTF-8 encoded string.

- Padding. Sometimes has data, seems to be when data_description contains data. Calculated at V5 - (V3-V2 + V5-V4) - 178. Don't ask me why but it works.

### Data (Remaining Bytes)
Audio data appears to be 16bit audio, however the format is different from a wav.
WAV Files store samples as paired Left and Right Channels - i.e

    LLLL RRRR
    LLLL RRRR
    ...
    LLLL RRRR

EBL Files take a different tact, splitting Left and Right into continuous chunks.

    LLLL LLLL
    LLLL LLLL
    ...
    0000 RRRR
    RRRR RRRR
    ...

Mono Tracks contain a single block of data, with the same header:

    LLLL LLLL
    LLLL LLLL
    ...

