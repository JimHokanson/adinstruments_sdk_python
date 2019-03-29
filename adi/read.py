
import inspect
from datetime import datetime, timedelta

#This is used only for returning the loaded data
import numpy as np

#Note apparently pylint doesn't like this because it is from a dll (.pyd file)
#https://stackoverflow.com/questions/28437071/pylint-1-4-reports-e1101no-member-on-all-c-extensions
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
    Currently created in get_all_comments
    
    TODO: In record add dt info so that time is valid as well (needs dt)
    
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
        
        """
 https://github.com/JimHokanson/adinstruments_sdk_matlab/blob/master/%2Badi/%40channel/channel.m       
        obj.tick_dt        = [record_handles.tick_dt];
            obj.data_starts    = [record_handles.data_start];
            obj.record_starts  = [record_handles.record_start];
            obj.record_handles = record_handles;
        """
        #self.tick_dt = [x.tick_dt for x in records]
        #self.tick_dt = [x.tick_dt for x in records]
        #self.tick_dt = [x.tick_dt for x in records]


    def get_data(self,record_id,start_sample=None,stop_sample=None):
        
        if start_sample is None:
            start_sample = 1
            
        if stop_sample is None:
            stop_sample = self.n_samples[record_id-1]
        elif stop_sample > self.n_samples[record_id-1]:   
            raise Exception('Out of range data requested')
        
        return SDK.get_channel_data(self.h,record_id,self.id,start_sample,stop_sample)

    def __repr__(self):
        return print_object(self)         


class RecordTime():
    
    """
    Apparently it is possible to trigger data collection before or after a trigger signal.
    
    Datetimes for both the trigger and data start are properties of this class.
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
    Attributes
    ----------
    n_ticks :
        # of samples in the record for the channel sampled at the highest rate
    tick_dt :
        Time between "ticks"
    comments : Comment
    
    """
    def __init__(self,h,record_id):
        
        """
        h : 
            Handle to the underlying file pointer
        sdk : SDK
        record_id : int?
            1 based record
        """
        self.h = h
        self.id = record_id
        
        
        self.n_ticks = SDK.get_n_ticks_in_record(self.h,record_id)
        
        #Not actually channel specific, channel is ignored (according to ADI)
        #Hard coded in "first channel" => 1
        self.tick_dt = SDK.get_tick_period(self.h,record_id,1)
        
        self.comments = SDK.get_all_comments(self.h,record_id)
        
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
    
    
    """
    def __init__(self,file_path):
        self.file_loaded = False
        self.h = SDK.open_read_file(file_path)
        self.file_loaded = True

        self.n_records = SDK.get_n_records(self.h)
        
        self.n_channels = SDK.get_n_channels(self.h)
        
        self.records = [Record(self.h,x+1) for x in range(self.n_records)]
        
        self.channels = [Channel(self.h,x+1,self.records) for x in range(self.n_channels)]
        
    
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
        np_arr = np.empty(n_elements, dtype=np.float32)
        
        
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