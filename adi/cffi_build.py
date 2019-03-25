# -*- coding: utf-8 -*-
"""
Created on Wed Mar 13 09:31:53 2019

@author: RNEL
"""

from cffi import FFI
ffibuilder = FFI()

# cdef() expects a single string declaring the C types, functions and
# globals needed to use the shared object. It must be in valid C syntax.
ffibuilder.cdef("""
      typedef enum ADIResultCode
      {
      //Win32 error codes (HRESULTs)
      kResultSuccess = 0,                             // operation succeeded
      kResultErrorFlagBit        = 0x80000000,       // high bit set if operation failed
      kResultInvalidArg          = 0x80070057,       // invalid argument. One (or more) of the arguments is invalid
      kResultFail                = 0x80004005,       // Unspecified error
      kResultFileNotFound        = 0x80030002,       // failure to find the specified file (check the path)


      //Start of error codes specific to this API      
      kResultADICAPIMsgBase        = 0xA0049000,

      kResultFileIOError  = 0xA0049000,    // file IO error - could not read/write file
      kResultFileOpenFail,                            // file failed to open
      kResultInvalidFileHandle,                       // file handle is invalid
      kResultInvalidPosition,                         // pos specified is outside the bounds of the record or file
      kResultInvalidCommentNum,                       // invalid commentNum. Comment could not be found
      kResultNoData,                                  // the data requested was not present (e.g. no more comments in the record).
      kResultBufferTooSmall                          // the buffer passed to a function to receive data (e.g. comment text) was not big enough to receive all the data.
      
                                                      // new result codes must be added at the end
      } ADIResultCode;
      
      typedef enum ADICDataFlags
      {
      kADICDataAtSampleRate = 0,                 // specifies that the function uses samples
      kADICDataAtTickRate = 0x80000000          // specifies that the function uses ticks
      } ADICDataFlags;
      
      
      typedef enum ADIFileOpenMode
      {
      kOpenFileForReadOnly = 0,  // opens the file as read-only, so data cannot be written
      kOpenFileForReadAndWrite  // opens the file as read/write
      } ADIFileOpenMode;
      
    struct ADI_FileHandle__ { int unused; }; typedef struct ADI_FileHandle__ *ADI_FileHandle;
    struct ADI_CommentsHandle__ { int unused; }; typedef struct ADI_CommentsHandle__ *ADI_CommentsHandle;
    
    ADIResultCode ADI_OpenFile(const wchar_t* path, ADI_FileHandle* fileH, ADIFileOpenMode mode);
    
    //Skipped CreateFile
    
    //NYI    
    ADIResultCode ADI_GetErrorMessage(ADIResultCode code, wchar_t* messageOut, long maxChars, long *textLen);
    
    //Skipped ADI_TickToSamplePos
    //Skipped ADI_SamplePosToTick
    
    ADIResultCode ADI_GetNumberOfRecords(ADI_FileHandle fileH, long* nRecords);
    
    ADIResultCode ADI_GetNumberOfChannels(ADI_FileHandle fileH, long* nChannels);
    
    ADIResultCode ADI_GetNumTicksInRecord(ADI_FileHandle fileH, long record, long* nTicks);
    
    ADIResultCode ADI_GetRecordTickPeriod(ADI_FileHandle fileH, long channel, long record, double* secsPerTick);
    
    ADIResultCode ADI_GetNumSamplesInRecord(ADI_FileHandle fileH, long channel, long record, long* nSamples);
    
    ADIResultCode ADI_GetRecordSamplePeriod(ADI_FileHandle fileH, long channel, long record, double* secsPerSample);
    
    //Hack :/
    //https://stackoverflow.com/questions/19352932/declare-struct-containing-time-t-field-in-python-cffi
    typedef long time_t;
    
    ADIResultCode ADI_GetRecordTime(ADI_FileHandle fileH, long record, time_t *triggerTime, double *fracSecs, long *triggerMinusStartTicks);
    
    ADIResultCode ADI_CreateCommentsAccessor(ADI_FileHandle fileH, long record, ADI_CommentsHandle* commentsH);
    
    ADIResultCode ADI_CloseCommentsAccessor(ADI_CommentsHandle *commentsH);
    
    ADIResultCode ADI_GetCommentInfo(ADI_CommentsHandle commentsH, long *tickPos, long *channel, long *commentNum, wchar_t* text, long maxChars, long *textLen);
    
    ADIResultCode ADI_NextComment(ADI_CommentsHandle commentsH);
    
    ADIResultCode ADI_GetSamples(ADI_FileHandle fileH, long channel, long record, long startPos, ADICDataFlags dataType, long nLength, float* data, long* returned);

    ADIResultCode ADI_GetUnitsName(ADI_FileHandle fileH, long channel, long record, wchar_t* units, long maxChars, long *textLen);
    
    ADIResultCode ADI_GetChannelName(ADI_FileHandle fileH, long channel, wchar_t* name, long maxChars, long *textLen);

    //Skipped a bunch in the header at this point ...
    
    ADIResultCode ADI_CloseFile(ADI_FileHandle* fileH);
""")

# set_source() gives the name of the python extension module to
# produce, and some C source code as a string.  This C code needs
# to make the declarated functions, types and globals available,
# so it is often just the "#include".
ffibuilder.set_source("_adi_cffi",
"""
     #include "ADIDatCAPI_mex.h"   // the C header of the library
""",
     libraries=['ADIDatIOWin64'])   # library name, for the linker

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)