# EBL to WAV Converion Script
The following is a rudimentary script to convert propritary E-mu EBL files into a usable audio format - WAV.

Code mostly works - I've tested on a large number of files, with only a few problems. I'll collect all of those and build a test suite.

## Dependancies
Python 3.9+

## Usage
Reads EXB folders in "input" folder. Writes to output. Need to add usage flags but i'm lazy. Structure looks like the following:

    Sample.exb/
      Sample.exb
      SamplePool/
        Sample1.ebl
        Sample1.ebl
        etc...
        
## EM-U and Emulator X-3
E-mu *was* a software sampler from 1997. They released a number of Sample CD's, containing many small audio files intended to be used with a sampler to make music.

Archive.org has (or had...) a large number of Sample CD's from the 90's and early 2000's archived. While the majority are in WAV format, there are several E-mu specific files that can only be read by Emulator X-3, a depreciated piece of software that is no longer available (You can find a copy on archive.org however, which will run under windows 10).

To avoid a huge job of loading and exporting thousands of files through Emulator X-3, I reverse engineered the EBL file format used by Emulator X-3.

## WAVE FILES
WAVE (WAV) files are reasonably simple. For an in-depth explanation [check this out.](http://soundfile.sapp.org/doc/WaveFormat/)

Worth noting that WAV files use Little Endian byte order by default.

In order to write a WAV file, several variables are required to be read from each EBL file:

- The data size on disk (in bytes). Taken from EBL file header.
- Sample Rate. Taken from EBL file header, although typically 44100 (CD quality)
- The filename - encoded as a 64 byte string.

We can make assumptions for other variables:

- PCM Mode: Typically 1, for every WAV file ever.
- Number of Channels: 2 (For stereo audio). All EBL files I've come across have been stereo, but Mono files are possible. Currently we assume Stereo (2).
- BitsPerSample: 16. The classic CD quality BPS. There is probably a way to read this from an EBL, but I currently assume it's 16.

## EBL Files
The following is my notes from reading a few dozen EBL files.

EBL files are weird - the headers are mostly Big Endian byte order, although the data headers are in Little Endian.

### Preliminary File Header is 8 bytes.
- header_1_prefix. "FORM"
- header_1_filesize. Big Endian 32 bit int. FileSize - 8 (i.e how many bytes are left from here)

### Header 2 just contains a size of metadata field. 12 bytes.
- header_2_prefix. "E5B0TOC2"
- header_2_data. Big Endian 32 bit int . Length of the next Chunk. Typically 78.

### Header 3 just contains the filename, and an updated metadata size and filesize for something different. 78 bytes (From header_2_data)
- header_3_prefix. "E5S1"
- header_3_filesize. Big Endian 32 bit int. The file size following the last E5S1 header.
- header_3_data = Big Endian 32 bit int. No idea what this is for. Typically 98.
- 2 empty bytes.
- file_name_1. 64 bytes, UTF-8 encoded string.

### Another E5S1 header. 14 bytes. No idea why.
- header_4_prefix. "E5S1"
- header_4_filesize. Big Endian 32 bit int. Remaining bytes following this section - 2.
- header_4_data. 32 bit int, unsure of byte-order. Typically 256 be, 1 le.

### Start of Data Chunk 2? 184 bytes to go till start of audio data.
- file_name_2. 64 bytes, UTF-8 encoded string.

#### We then have several little endian 32-bit ints.
- variable_1 - Unsure.

- variable_2. Data Offset. Typically 184.
- variable_3. Data size (including offset).
- variable_4. Data size - 2 (Not sure why?).
- variable_5. Close to the end of file in bytes. Not sure. Could also be all Audio Data.

- variable_6. Chanel 1 Data Offset.
- variable_7. Chanel 1 Data size (including offset).
- variable_8. Chanel 2 Data Offset?
- variable_9. End of data for this channel?

- variable_10. Frequency. Typically 44100 (hz)
- variable_11. Always 0.
- variable_12. Unknown but maybe number of channels, bitrate and some other things go here.
- data_header_padding. 72 Bytes of 0.

### Data (Remaining Bytes)
Audio data appears to be 16bit audio, however the format is different from a wav.
WAV Files store samples as paired Left and Right Channels - i.e

    LLLL RRRR
    LLLL RRRR
    ...
    LLLL RRRR

EBL Files take a different tact, splitting Left and Right into continuous chunks, with 4 null bytes padding.

    LLLL LLLL
    LLLL LLLL
    ...
    0000 RRRR
    RRRR RRRR
    ...

Sizes of each chunk are taken from variable_3 - variable_2.
