# adinstruments_sdk_python

Use this code to read .adicht (Labchart) files into Python. Interfacing with the ADIstruments DLL is done via [cffi](https://cffi.readthedocs.io/en/latest/).

- The code utilizes the SDK from ADIstruments to read files in Python as NumPy arrays.
- **Currently only works for Windows. Not fixable by me, requires changes by ADInstruments**
- A slightly more fleshed out MATLAB version can be found [here](https://github.com/JimHokanson/adinstruments_sdk_matlab).
- Currently requires Python 3.6-3.14 with some of the newer versions requiring 64 bit Python (this can change but requires some work on my end)

## Installation ##

	pip install adi-reader

## Support Notes ##

My ability to work on this code was supported, in part, by a grant from the NIH NIDDK ([grant: R21DK140694](https://reporter.nih.gov/project-details/11232104))


## Dependencies ##

- [cffi](https://cffi.readthedocs.io/en/latest/)
- [NumPy](https://numpy.org/)
- Python 3.6-3.14


## Demo code ##

```python
import adi
f = adi.read_file(r'C:\Users\RNEL\Desktop\test\test_file.adicht')
# All id numbering is 1 based, first channel, first block
# When indexing in Python we need to shift by 1 for 0 based indexing
# Functions however respect the 1 based notation ...

# These may vary for your file ...
channel_id = 2
record_id = 1
data = f.channels[channel_id-1].get_data(record_id)

import matplotlib.pyplot as plt
plt.plot(data)
plt.show()
	
```

Grabbing data from a specific channel. Some advanced data retrieval functionality is also shown.
```python
import adi
f = adi.read_file(r'C:\Users\RNEL\Desktop\test\test_file.adicht')
#Note, this defaults to a partial, case insensitive match
p = f.get_channel_by_name('pres')

record_id = 1
#time units are in seconds
time,data = p.get_data(record_id,start_time=10,return_time=True)


plt.plot(time,data)
plt.xlabel('time (s)')
plt.ylabel(f'{p.name} ({p.units[record_id]})')
plt.show()

```

Here's an example of working with comment data.
```
import adi

fp = r"D:\Data\Duke\PGE2_2017\140414_C_01_pelvic and hypogastric recording PGE2 model .adicht"

f = adi.read_file(fp)

#default is a list, could also return as a dataframe
comments = f.get_comments(return_as='object')

#You can throw a warning or an error (or ignore) unmatched pairs
# - 'ignore'
# - 'error'
# - 'warn'
#You can skip, allow, or throw an error for matches spanning records
# - 'skip'
# - 'allow'
# - 'error'
pairs = comments.get_comment_pairs("start pump","stop pump",unmatched='ignore',record_split="skip")

p_chan = adi.get_channel_by_name('pres')
id_pair = [pairs.id1[0],pairs.id2[0]]
#Passing in a pair of IDs for comment_range is sufficient to identify
#the time range. Note they currently need to be in the same record_id
#
#The record_id input is ignored, so I just pass in -1
time,data = p_chan.get_data(-1, comment_range=id_pair,return_time=True)

import matplotlib.pyplot as plt
plt.plot(time,data)
plt.show()

```



## Data Model ##

Data are collected in blocks or records, starting at record 1. For each record the channel properties can change (units, sampling rate). Every time settings are changed or recording stops, a new block is created (once recording starts again).

The two primary data types that are exposed through the SDK are:
- channel data
- comments - time of comment and text information (along with an id and info on which channel the comment applies to)

There are other things that are collected in LabChart files, but these are not exposed via the SDK.

- file
  - records
     - timing info
	 - comments
  - channels
     - data


## Improvements ##

Feel free to open pull requests or to open issues.

Things I would like to add at some point:
- a general review tool that plots a file
- even simpler, plotting a channel with comments
- better method support for getting specific info
- better functionality of data retrieval


## Change Notes ##

- 2026-04-12 :
  - Added 3.14 support
  - Improved documentation
