
import inspect
from datetime import datetime, timedelta

#This is used only for returning the loaded data
import numpy as np

#Note apparently pylint doesn't like this because it is from a dll (.pyd file)
#https://stackoverflow.com/questions/28437071/pylint-1-4-reports-e1101no-member-on-all-c-extensions
import struct

p_size = struct.calcsize("P")
if p_size == 4:
    from adi._adi_cffi2 import ffi, lib
else:
    from adi._adi_cffi import ffi, lib

r"""
    #Test Code:
    import adi
    f = adi.read_file(r'C:\Users\RNEL\Desktop\test\test_file.adicht')
    channel_id = 2
    c = f.channels[channel_id-1]
    record_id = 1
    data = f.channels[1].get_data(record_id)
    import matplotlib.pyplot as plt
    plt.plot(data)
    plt.show()
"""

def read_file(file_path):
    """
    This is the preferred entry point for working with this module.
    """
    return File(file_path)

def print_object(obj):
    """
    Goal is to eventually mimic Matlab's default display behavior for objects
    Example output from Matlab
    morphology: [1x1 seg_worm.features.morphology]
       posture: [1x1 seg_worm.features.posture]
    locomotion: [1x1 seg_worm.features.locomotion]
          path: [1x1 seg_worm.features.path]
          info: [1x1 seg_worm.info]
    #TODO: For ndarrays we should implement size displays instead of length
    #TODO: The @property hack doesn't work for @property values from parent
    classes, I would need to look at __bases__
    """

    # TODO - have some way of indicating nested function and not doing fancy
    # print for nested objects ...

    MAX_WIDTH = 70

    dict_local = obj.__dict__

    key_names = [k for k in dict_local]

    try:
        # TODO: Also include __bases__
        names_of_prop_methods = [
            name for name, value in vars(
                obj.__class__).items() if isinstance(
                value, property)]
        prop_code_ok = True
    except:
        prop_code_ok = False

    is_prop = [False] * len(key_names)
    if prop_code_ok:
        is_prop += [True] * len(names_of_prop_methods)
        key_names += names_of_prop_methods

    key_lengths = [len(x) for x in key_names]

    if len(key_lengths) == 0:
        return ""

    max_key_length = max(key_lengths)
    key_padding = [max_key_length - x for x in key_lengths]

    max_leadin_length = max_key_length + 2
    max_value_length = MAX_WIDTH - max_leadin_length

    lead_strings = [' ' * x + y + ': ' for x, y in zip(key_padding, key_names)]

    # TODO: Alphabatize the results ????
    # Could pass in as a option
    # TODO: It might be better to test for built in types
    #   Class::Bio.Entrez.Parser.DictionaryElement
    #   => show actual dictionary, not what is above

    value_strings = []
    for key, is_prop_local in zip(key_names, is_prop):
        if is_prop_local:
            temp_str = '@property method'
        else:
            run_extra_code = False
            value = dict_local[key]
            if hasattr(value, '__dict__'):
                try:  # Not sure how to test for classes :/
                    class_name = value.__class__.__name__
                    module_name = inspect.getmodule(value).__name__
                    temp_str = 'Class::' + module_name + '.' + class_name
                except:
                    run_extra_code = True
            else:
                run_extra_code = True

            if run_extra_code:
                # TODO: Change length to shape if available
                if isinstance(value, list) and len(value) > max_value_length:
                    len_value = len(value)
                    temp_str = 'Type::List, Len %d' % len_value
                else:
                    # Perhaps we want str instead?
                    # Changed from repr to str because things Python was not
                    # happy with lists of numpy arrays
                    temp_str = str(value)
                    if len(temp_str) > max_value_length:
                        #type_str = str(type(value))
                        #type_str = type_str[7:-2]
                        try:
                            len_value = len(value)
                        except:
                            len_value = 1
                        temp_str = str.format(
                            'Type::{}, Len: {}', type(value).__name__, len_value)

        value_strings.append(temp_str)

    final_str = ''
    for cur_lead_str, cur_value in zip(lead_strings, value_strings):
        final_str += (cur_lead_str + cur_value + '\n')

    return final_str

class Comment():
    
    """
    This is currently created in the Record constructor.
    
    A comment consists primarily of a string and the time that it applies to.
    
    Attributes
    ----------
    text : string
        The comment string
    tick_position :
    channel : numeric
        - a value of -1 indicates all channels
    id : 
        This starts at 1 and increments but may have gaps if comments are deleted.
        Also, I don't think these are returned in order (time order instead of id order?)
    tick_dt :
    time : 
        Seconds since start of recording (based on tick position)
    
    """
    def __init__(self,text,tick_pos,channel_id,comment_id):
        self.text = text
        self.tick_position = tick_pos
        self.channel_ = channel_id
        self.id = comment_id
        
        
    def _add_info(self,tick_dt):
        self.tick_dt = tick_dt
        self.time = self.tick_position*self.tick_dt
        
        
    def __repr__(self):
        return print_object(self)


class Channel():
    
    """
    Attributes
    ----------
    h : 
        Handle to the SDK for making calls.
    id : numeric
        Channel ID, starts at 1
    n_records : numeric
    tick_dt : list, length: n_records
        Highest sampling rate of any channel for that record. Not really
        critical for this object (use dt/fs instead)
    records : [Record]
        Provides acccess to the relevant record
    name :
        This is fixed across all records
    units : list, length: n_records
    n_samples : list, length: n_records
    dt : list, length: n_records
        Time between samples
    fs : list, length: n_records
        Sampling rate
    max_time : 
        Last time point where data was collected.
        
    Notes
    ------
    1. Data for a channel may not exist for a given record.    
        
    Methods
    -------
    get_data : retrieves data
    
    """
    
    def __init__(self,h,channel_id,records):
        self.h = h
        self.id = channel_id #1 based
        self.n_records = len(records)
        self.tick_dt = [x.tick_dt for x in records]
        self.records = records
        
        self.name = SDK.get_channel_name(self.h,self.id)
        
        self.units = [SDK.get_units_name(self.h,x+1,self.id) for x in range(self.n_records)]
        self.n_samples = [SDK.get_n_samples_in_record(self.h,x+1,self.id) for x in range(self.n_records)]
        self.dt = [SDK.get_sample_period(self.h,x+1,self.id) for x in range(self.n_records)]
        self.fs = [1/x for x in self.dt]
        self.max_time = [(self.n_samples[x]-1)*self.dt[x] if self.n_samples[x] > 0 else None for x in range(self.n_records)]
        
    def get_data(self, record_id, start_sample=None, stop_sample=None,
                 start_time=None, stop_time=None, return_time=False):
        """
        Calling Forms
        -------------
        data = chan.get_data(record_id,**options)
        
        time,data = chan.get_data(record_id,return_time=True,**options)
        
        
        Parameters
        ----------
        record_id : numeric
            Which record to retrieve data from.
        start_sample : numeric, optional
            Default 1. Ignored if start_time is provided.
        stop_sample : numeric, optional
            Default last sample. Ignored if stop_time is provided.
        start_time : numeric, optional
            Start time in seconds. Overrides start_sample if provided.
        stop_time : numeric, optional
            Stop time in seconds. Overrides stop_sample if provided.
        return_time : boolean, optional
            If True, returns a tuple of (time_array, data_array).
            The default is False.
            
            
        Returns
        -------
        numpy array, or tuple of (numpy array, numpy array) if return_time=True   
        
        Improvements
        ------------
        1. Consider adding sample_range = [start,stop] and time_range = [start,stop]
        
        """
        
        dt = self.dt[record_id - 1]
    
        #Start sample determination
        #------------------------------------------
        if start_time is not None:
            # Convert to 1-based sample index
            start_sample = int(start_time / dt) + 1  
        elif start_sample is None:
            start_sample = 1
        
        #Stop sample determination
        #------------------------------------------
        if stop_time is not None:
            stop_sample = int(stop_time / dt) + 1
        elif stop_sample is None:
            stop_sample = self.n_samples[record_id - 1]
        
        
        # Validate computed sample bounds
        #------------------------------------------
        if start_sample < 1:
            raise Exception('Computed start_sample from start_time is out of range')
        if stop_sample > self.n_samples[record_id - 1]:
            raise Exception('Computed stop_sample from stop_time is out of range')
    
        data = SDK.get_channel_data(self.h, record_id, self.id, start_sample, stop_sample)
    
        if return_time:
            time = np.arange(start_sample - 1, stop_sample) * dt  # 0-based time in seconds
            return time, data
        else:    
            return data
        

    def __repr__(self):
        return print_object(self)         


class RecordTime():
    
    """
    Describes when a record started (in real/wall time). There is also some
    triggering information which I don't completely understand ...
    
    Attributes
    ----------
    trig_datetime : datetime
    trig_start_delta : numeric
        Difference between trigger and data collection start, in ticks. If 
        positive then data started later. If negative, data collection starts
        before the trigger (presumably using a buffer approach to allow going
        back in time to get data before the trigger occurs)
    trig_datestr : string
    rec_datetime : datetime
        I believe this is the actual time when the first sample was collected
    rec_datestr : string
        
    
    It is possible to trigger data collection before or after the trigger signal.
    
    
    """
    def __init__(self,tick_dt,trig_time,frac_secs,trig_minus_start_ticks):
        
        self.trig_datetime = datetime.utcfromtimestamp(trig_time) + timedelta(seconds = frac_secs)
        self.trig_start_delta = trig_minus_start_ticks
        self.trig_datestr = self.trig_datetime.strftime("%Y-%m-%d %H:%M:%S.%f").rstrip('0')
    
        delta = timedelta(seconds = abs(trig_minus_start_ticks*tick_dt))
        
        if trig_minus_start_ticks > 0:
            self.rec_datetime = self.trig_datetime + delta
        else:
            self.rec_datetime = self.trig_datetime - delta;
        
        self.rec_datestr = self.rec_datetime.strftime("%Y-%m-%d %H:%M:%S.%f").rstrip('0')
                
        #+ve - trigger before block
        #-ve - trigger after block
    
    def __repr__(self):
        return print_object(self)   

class Record():
    
    """
    Holder of comments and record timing information.
    
    Attributes
    ----------
    h : handle to the SDK
    id : numeric
        Record indicator, starts at 1
    n_ticks : numeric
        # of samples in the record for the channel sampled at the highest rate
    tick_dt : numeric
        Time between "ticks"
    tick_fs : numeric
        Sampling rate of ticks
    comments : [Comment]
    record_time : RecordTime
        
    
    """
    def __init__(self,h,record_id):
        
        """
        Parameters
        ----------
        h : 
            Handle to the underlying file pointer
        record_id : numeric
            1 based record
        """
        self.h = h
        self.id = record_id
        
        
        self.n_ticks = SDK.get_n_ticks_in_record(self.h,record_id)
        
        #Not actually channel specific, channel is ignored (according to ADI)
        #Hard coded in "first channel" => 1
        self.tick_dt = SDK.get_tick_period(self.h,record_id,1)
        self.tick_fs = 1.0/self.tick_dt
        
        self.comments = SDK.get_all_comments(self.h,record_id)
        
        #JAH: Why did I do this as a later step?
        for c in self.comments:
            c._add_info(self.tick_dt)
            
            
        self.record_time = SDK.get_record_time_info(self.h,record_id,self.tick_dt) 

    def __repr__(self):
        return print_object(self)            

        

class File():
    
    """
    Attributes
    ----------
    file_loaded
    h
    n_records
    n_channels
    records
    channels
    channel_names
    
    Methods
    -------
    get_channel_by_name - returns a specific channel
    
    
    Missing methods from MATLAB version (i.e., potential improvements)
    ------------------------------------------------------------------
    - isChannelInRecord - flag on whether channel is in specified record
    - channelsInRecord - list of channels in record
    - getAllComments - return all comments
    
    
    """
    def __init__(self,file_path):
        self.file_loaded = False
        self.h = SDK.open_read_file(file_path)
        self.file_loaded = True

        self.n_records = SDK.get_n_records(self.h)
        
        self.n_channels = SDK.get_n_channels(self.h)
        
        self.records = [Record(self.h,x+1) for x in range(self.n_records)]
        
        self.channels = [Channel(self.h,x+1,self.records) for x in range(self.n_channels)]
        self.channel_names = [x.name for x in self.channels]
        
    def get_channel_by_name(self,chan_name,case_sensitive=False,partial_match=True):
        """

        Parameters
        ----------
        chan_name : string
            Name of the channel to match
        case_sensitive : boolean, optional
            Whether to require case matching. The default is False.
        partial_match : boolean, optional
            Whether to allow partial matching. For example 'pres' could
            be used to match 'Bladder Pressure'. The default is True.

        Returns
        -------
        channel object

        """
        # Normalize the search term if case-insensitive
        search_name = chan_name if case_sensitive else chan_name.lower()
    
        matched_names = []
        matched_channels = []
    
        for name, channel in zip(self.channel_names, self.channels):
            candidate = name if case_sensitive else name.lower()
    
            if partial_match:
                is_match = search_name in candidate
            else:
                is_match = search_name == candidate
    
            if is_match:
                matched_names.append(name)
                matched_channels.append(channel)
    
        if len(matched_channels) == 0:
            raise ValueError(
                f"No channel found matching '{chan_name}'. "
                f"Available channels: {self.channel_names}"
            )
        elif len(matched_channels) > 1:
            raise ValueError(
                f"Multiple channels found matching '{chan_name}': {matched_names}. "
                f"Please provide a more specific name."
            )

        return matched_channels[0]
    
    def __del__(self):
        #print("object deleted")
        if self.file_loaded:
            SDK.close_file(self.h)

    def __repr__(self):
        return print_object(self)
    
    
class SDK():
    
    @staticmethod
    def open_read_file(file_path):
        h = ffi.new("ADI_FileHandle *")
        result = lib.ADI_OpenFile(file_path,h,lib.kOpenFileForReadOnly)
        
        if result == 0:
            return h
        else:
            #TODO: Add more 
            raise Exception('Error opening file for reading')
    
    """
    ============================   Record    ============================
    """   
    
    @staticmethod
    def get_record_time_info(h,record_id,tick_dt):
        trig_time = ffi.new("time_t *")
        frac_secs = ffi.new("double *")
        trigger_minus_rec_start = ffi.new("long *")
        result = lib.ADI_GetRecordTime(h[0],record_id-1,trig_time,frac_secs,trigger_minus_rec_start)
        if result == 0:
            return RecordTime(tick_dt,trig_time[0],frac_secs[0],trigger_minus_rec_start[0])
        else:
            #TODO: Improve message
            raise Exception('Error getting # of ticks in record')
    
    
    @staticmethod
    def get_n_ticks_in_record(h,record_id):
        n_ticks = ffi.new("long *")
        result = lib.ADI_GetNumTicksInRecord(h[0],record_id-1,n_ticks)
        if result == 0:
            return n_ticks[0]
        else:
            #TODO: Improve message
            raise Exception('Error getting # of ticks in record')

    """
    ============================   Channel    ============================
    """     
    #TODO: Would be better to include channel in names ... 
    @staticmethod
    def get_tick_period(h,record_id,channel_id):
        tick_period = ffi.new("double *")
        result = lib.ADI_GetRecordTickPeriod(h[0],channel_id-1,record_id-1,tick_period)
        if result == 0:
            return tick_period[0]
        else:
            raise Exception('Error getting tick period')
       
    @staticmethod       
    def get_n_samples_in_record(h,record_id,channel_id):
         n_samples = ffi.new("long *")      
         result = lib.ADI_GetNumSamplesInRecord(h[0],channel_id-1,record_id-1,n_samples)
         
         if result == 0 or result == 1:
             return n_samples[0]
         else:
             raise Exception('Error getting # of samples in record')
    

    @staticmethod
    def get_sample_period(h,record_id,channel_id):
        sample_period = ffi.new("double *")
        result = lib.ADI_GetRecordSamplePeriod(h[0],channel_id-1,record_id-1,sample_period)
        if result == 0 or result == 1:
            return sample_period[0]
        else:
            raise Exception('Error getting sample period')
       

    
    @staticmethod
    def get_units_name(h,record_id,channel_id):
        #TODO: Make length a variable
        
        #Different interfae ...
        #    N = 10
        #ptr = ffi.new( "float[]", N )
        
        text = ffi.new("wchar_t[1000]")
        max_chars = 999 #needs null termination???
        text_length = ffi.new("long *")
        result = lib.ADI_GetUnitsName(h[0],channel_id-1,record_id-1,text,max_chars,text_length)
        
        if not(result == 0 or result == 1):
            print(result)
            raise Exception('Error retrieving units')
        
        #I think the length includes null terminaton so we substract 1
        final_text = ffi.unpack(text,text_length[0]-1)
        return final_text        
    
    @staticmethod       
    def get_channel_name(h,channel_id):  
        
        
        #TODO: Make length a variable
        text = ffi.new("wchar_t[1000]")
        max_chars = 999 #needs null termination???
        text_length = ffi.new("long *")
        result = lib.ADI_GetChannelName(h[0],channel_id-1,text,max_chars,text_length)
        
        if not(result == 0 or result == 1):
            print(result)
            raise Exception('Error retrieving channel name')
        
        #I think the length includes null terminaton so we substract 1
        final_text = ffi.unpack(text,text_length[0]-1)
        return final_text

    
    
    @staticmethod       
    def get_channel_data(h,record_id,channel_id,start_sample,stop_sample):

        n_elements = stop_sample-start_sample+1
        
        if n_elements <= 0:
            raise ValueError("# of samples requested is less than 1")
        
        np_arr = np.zeros(n_elements, dtype=np.float32)
        
        #Note, we might just be able to case to numpy after running
        #=> numpy.frombuffer => 0 copy?
        
        #https://ammous88.wordpress.com/2014/12/30/numpy-array-with-cffi-c-function/
        cffi_arr = ffi.cast('float*', np_arr.ctypes.data)
        
        returned = ffi.new("long *")
        result = lib.ADI_GetSamples(h[0],channel_id-1,record_id-1,start_sample-1,lib.kADICDataAtSampleRate,n_elements,cffi_arr,returned)
        
        if result == 0:
            return np_arr
        else:
            raise Exception('Unable to retrieve requested data')
    
    
    """
    ============================   Comments    ============================
    """                         
    @staticmethod
    def get_comment_accessor(h,record_id):
        """
        0 indicates no comments
        """
        h2 = ffi.new("ADI_CommentsHandle *")                       
        result = lib.ADI_CreateCommentsAccessor(h[0],record_id-1,h2)
        
        #No comments - not sure why we don't have a flag for this ...
        if result == -1610313723:
            return 0
        elif result == 0:
            return h2
        else:
            raise Exception('Error opening comments accessor')
            
    
    @staticmethod
    def advance_comment_ptr(h2):
        """
        returns True if comment is available
        """
        result = lib.ADI_NextComment(h2[0])
        
        if result == 0:
            return True
        elif result == lib.kResultNoData:
            return False
        else:
            raise Exception('Unhandled case for advancing comment pointer')
    
    @staticmethod
    def get_all_comments(h,record_id):
        
        h2 = SDK.get_comment_accessor(h,record_id)
        if h2 == 0:
            return []
        else:
            output = []
            c = SDK.get_comment(h2)
            output.append(c)
            while SDK.advance_comment_ptr(h2):
                c = SDK.get_comment(h2)
                output.append(c)
                
                
            SDK.close_comment_accessor(h2)    
            return output    
        
        
    @staticmethod
    def get_comment(h2):
        tick_pos = ffi.new("long *")
        channel = ffi.new("long *")
        comment_id = ffi.new("long *")
        #TODO: Make length a variable
        text = ffi.new("wchar_t[1000]")
        max_chars = 999 #needs null termination????
        text_length = ffi.new("long *")
        result = lib.ADI_GetCommentInfo(h2[0],tick_pos,channel,comment_id,text,max_chars,text_length)
        
        if result != 0:
            raise Exception('Error retrieving comment')
        
        #I think the length includes null terminaton so we substract 1
        final_text = ffi.unpack(text,text_length[0]-1)
        return Comment(final_text,tick_pos[0],channel[0],comment_id[0])
        
        #ADI_GetCommentInfo
        #ADIResultCode ADI_GetCommentInfo(ADI_CommentsHandle commentsH, long *tickPos, long *channel, long *commentNum, wchar_t* text, long maxChars, long *textLen);
    
    @staticmethod
    def close_comment_accessor(h2):
        result = lib.ADI_CloseCommentsAccessor(h2)
        if result == 0:
            pass
        else:
            raise Exception('Error closing comments handle')
     
    @staticmethod
    def get_n_records(h):
        n_records = ffi.new("long *")
        result = lib.ADI_GetNumberOfRecords(h[0],n_records)
        if result == 0:
            return n_records[0]
        else:
            raise Exception('Error getting # of records')
        
        
    @staticmethod
    def get_n_channels(h):
        n_channels = ffi.new("long *")
        result = lib.ADI_GetNumberOfChannels(h[0],n_channels)
        if result == 0:
            return n_channels[0]
        else:
            raise Exception('Error getting # of channels')
        
    @staticmethod    
    def close_file(h):
        result = lib.ADI_CloseFile(h)
        if result == 0:
            pass
        else:
            raise Exception('Error closing file handle')
