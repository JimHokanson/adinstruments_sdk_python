# adinstruments_sdk_python
SDK for ADIstruments files in Python

A slightly more flushed out Matlab version can be found here
https://github.com/JimHokanson/adinstruments_sdk_matlab

Use this code to read .adicht (Labchart) files into Python.

Currently only works for Windows.

Interfacing with the ADIstruments DLL is done via cffi:
https://cffi.readthedocs.io/en/latest/

# Setup #

Running the code might require compiling the cffi code. This requires running cffi_build.py in the adi package. This might require installing cffi as well as some version of Visual Studio. The currently released code was compiled for Python 3.6 on Visual Studio 2015 or 2017 (not sure which)


# Test code #

```python
    import adi
    f = adi.read_file(r'C:\Users\RNEL\Desktop\test\test_file.adicht')
    channel_id = 2
    c = f.channels[channel_id-1]
    record_id = 1
    data = f.channels[1].get_data(record_id)
    import matplotlib.pyplot as plt
    plt.plot(data)
    plt.show()
```

# Improvements #

This was written extremely quickly and is missing some features. Feel free to open pull requests or to open issues.