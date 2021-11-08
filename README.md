# adinstruments_sdk_python

Use this code to read .adicht (Labchart) files into Python. Interfacing with the ADIstruments DLL is done via [cffi](https://cffi.readthedocs.io/en/latest/).

- The code utilizes the SDK from ADIstruments to read files in Python as NumPy arrays.
- Currently only works for Windows.
- A slightly more flushed out Matlab version can be found [here](https://github.com/JimHokanson/adinstruments_sdk_matlab).

---

## Installation ##

	pip install adi-reader

----

## Test code ##

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
----

## Dependencies ##
- [cffi](https://cffi.readthedocs.io/en/latest/)
- [NumPy](https://numpy.org/)
- Python 3.6-3.9
----

## Setup for other Python versions ##

- Running the code might require compiling the cffi code depending on your Python version. 
- This requires running cffi_build.py in the adi package. 
- This might require installing cffi as well as some version of Visual Studio. 
- The currently released code was compiled for Python 3.6-3.9 on Visual Studio 14.0 or greater was required.

For upgrading to 3.8, I installed Python 3.8. Within the interpreter I ran the following:

- Jim note to self, rather than installing Anaconda I simply:
  - download Python from https://www.python.org/downloads/windows/
  - cd to Python directory or run directly, these go to something like: `C:\Users\RNEL\AppData\Local\Programs\Python\Python39-32\python` 
  - Note the above path is specific to my computer, might need to change user name

```python
import subprocess
import sys

#https://stackoverflow.com/questions/12332975/installing-python-module-within-code
def install(package):
    subprocess.call([sys.executable, "-m", "pip", "install", package])
	
install("cffi")

import os
#This would need to be changed based on where you keep the code
os.chdir('G:/repos/python/adinstruments_sdk_python/adi')

# For 64 bit windows
exec(open("cffi_build.py").read())

# For 32 bit windows
exec(open("cffi_build_win32.py").read())
```
----

## Improvements ##

This was written extremely quickly and is missing some features. Feel free to open pull requests or to open issues.
