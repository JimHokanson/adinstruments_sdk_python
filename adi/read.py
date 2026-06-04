from __future__ import annotations

#Standard
#------------------------
from dataclasses import dataclass
from typing import overload, Literal, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    
import inspect
from datetime import datetime, timedelta



#Third Party
#------------------------
#This is used only for returning the loaded data
import numpy as np

#Note: Pandas is also required in some cases (but not critical)


#Local
#-------------------------

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

def read_file(file_path) -> File:
    """
    This is the preferred entry point for working with this module.
    """
    return File(file_path)

def print_object(obj,keys_hide=[]):
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

    key_names = [k for k in dict_local if k not in keys_hide]

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

    class_name = obj.__class__.__name__
    final_str = class_name + '\n' + '-' * len(class_name) + '\n'
    for cur_lead_str, cur_value in zip(lead_strings, value_strings):
        final_str += (cur_lead_str + cur_value + '\n')
    return final_str

@dataclass
class CommentCollection:
    comments: list[Comment]
    record_times : list[RecordTime]

    def to_dataframe(self) -> pd.DataFrame:
        import pandas as pd

        return pd.DataFrame([
            {
                "record_id": c.record_id,
                "text": c.text,
                "id": c.id,
                "channel": c.channel,
                "time": c.time,
                "tick_position": c.tick_position,
            }
            for c in self.comments
        ])
    
    """
    def get_comment_pairs(self, start, stop, n_max=None, 
                          record_split: Literal["allow", "skip", "error"] = "skip"):
        
        #.record_id1
        #.record_id2
        #.id1
        #.id2
        #.start_time
        #.stop_time
        #.start_comment
        #.stop_comment
        #.duration
        pass
    """
    
    def get_comment_pairs(self, start, stop, n_max=None, 
                          record_split: Literal["allow", "skip", "error"] = "error",
                          unmatched: Literal["ignore", "warn", "error"] = "error"):
        """
        Find sequential pairs of comments whose text matches `start` and
        `stop` (case-insensitive partial match).

        Parameters
        ----------
        start : str
            Substring to match for the opening comment.
        stop : str
            Substring to match for the closing comment.
        n_max : int, optional
            Maximum number of pairs to return.
        record_split : {"allow", "skip", "error"}, default "error"
            How to handle pairs that span different records.
            - "skip": both comments must be in the same record; a record
              boundary orphans any open start.
            - "allow": a stop comment in a later record can close a start
              from an earlier record (duration will be None for
              cross-record pairs since times are record-relative).
            - "error": raise ValueError if any cross-record pairs are found.
        unmatched : {"ignore", "warn", "error"}, default "error"
            What to do when start or stop comments have no partner.
            - "ignore": silently discard them.
            - "warn": emit a warnings.warn with details.
            - "error": raise ValueError with details.

        Returns
        -------
        pd.DataFrame
            Columns: rid1, rid2, id1, id2, start_time,
            stop_time, start_comment, stop_comment, duration
            - rid1, rid2 - records IDs (shortened for table display)
            - duration (numeric, in seconds)
            
        """
        
        """
        Implementation details:
            - comments are merged into a single timeline and walked 
              linearly so that a second start before a stop orphans the 
              first start (rather than letting an early orphan steal a 
              later pair's stop)
        """
        
        import pandas as pd

        start_lower = start.lower()
        stop_lower = stop.lower()
        restrict_to_record = record_split == "skip"

        # Merge and tag all matching comments
        tagged = []
        for c in self.comments:
            text_lower = c.text.lower()
            is_start = start_lower in text_lower
            is_stop = stop_lower in text_lower
            if is_start or is_stop:
                tagged.append((c, is_start, is_stop))

        tagged.sort(key=lambda x: (x[0].record_id, x[0].time))

        # Linear scan: walk the timeline and pair start/stop sequentially.
        # If a new start appears before the current start is closed, the
        # current start is orphaned.
        pairs = []
        orphan_starts = []
        orphan_stops = []
        current_start = None

        for c, is_start, is_stop in tagged:
            # A record boundary orphans any open start when restricted
            if restrict_to_record and current_start is not None:
                if c.record_id != current_start.record_id:
                    orphan_starts.append(current_start)
                    current_start = None

            if is_stop and current_start is not None:
                # Close the pair
                pairs.append((current_start, c))
                current_start = None
                if n_max is not None and len(pairs) >= n_max:
                    break
            elif is_start:
                # A new start orphans any unclosed previous start
                if current_start is not None:
                    orphan_starts.append(current_start)
                current_start = c
            else:
                # is_stop with no open start
                orphan_stops.append(c)

        # Anything still open at the end is orphaned
        if current_start is not None:
            orphan_starts.append(current_start)

        # Enforce the "error" mode for cross-record pairs
        if record_split == "error":
            cross_record = [
                (c1, c2) for c1, c2 in pairs
                if c1.record_id != c2.record_id
            ]
            if cross_record:
                details = ", ".join(
                    f"comment {c1.id} (record {c1.record_id}) → "
                    f"comment {c2.id} (record {c2.record_id})"
                    for c1, c2 in cross_record
                )
                raise ValueError(
                    f"Found {len(cross_record)} cross-record pair(s): {details}")

        # Handle unmatched comments
        if unmatched != "ignore" and (orphan_starts or orphan_stops):
            parts = []
            if orphan_starts:
                details = ", ".join(
                    f"id {c.id} (record {c.record_id}, t={c.time:.3f})"
                    for c in orphan_starts)
                parts.append(f"{len(orphan_starts)} unmatched start(s): {details}")
            if orphan_stops:
                details = ", ".join(
                    f"id {c.id} (record {c.record_id}, t={c.time:.3f})"
                    for c in orphan_stops)
                parts.append(f"{len(orphan_stops)} unmatched stop(s): {details}")

            msg = "; ".join(parts)

            if unmatched == "error":
                raise ValueError(msg)
            else:
                import warnings
                warnings.warn(msg)

        # Build the output DataFrame
        rows = []
        for c1, c2 in pairs:
            same_record = c1.record_id == c2.record_id
            if same_record:
                duration = c2.time - c1.time
            else:
                r1 = self.record_times[c1.record_id-1]
                r2 = self.record_times[c2.record_id-1]
                #start2 = r2.rec_datetime
                #stop1 = r1.rec_stop_datetime
                c2_time_datetime = r2.rec_datetime + timedelta(seconds=c2.time)
                c1_time_datetime = r1.rec_datetime + timedelta(seconds=c1.time)
                duration = (c2_time_datetime - c1_time_datetime).total_seconds()
                
                #elapsed time = 
                # duration - c1.time
                #+ time between records ()
                #duration = 1
                
                
            rows.append(
                {
                    "rid1": c1.record_id,
                    "rid2": c2.record_id,
                    "id1": c1.id,
                    "id2": c2.id,
                    "start_time": c1.time,
                    "stop_time": c2.time,
                    "start_comment": c1.text,
                    "stop_comment": c2.text,
                    "duration": duration,
                }
            )

        return pd.DataFrame(rows)

    def __repr__(self):
        return print_object(self)
    
    

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
    def __init__(self,text,tick_pos,channel_id,comment_id) -> None:
        self.text = text
        self.tick_position = tick_pos
        #This is a typo (I believe) :/
        self.channel_ = channel_id
        self.channel = self.channel_
        self.id = comment_id
        
        
    def _add_info(self,record_id,tick_dt) -> None:
        self.record_id  = record_id
        self.tick_dt = tick_dt
        self.time = self.tick_position*self.tick_dt
        
        
    def __repr__(self):
        return print_object(self,keys_hide=['channel_'])


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
    
    def __init__(self,h,channel_id,records,h_file):
        self.h = h
        self.h_file = h_file
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

    @overload
    def get_data(self, record_id: int, *, return_time: Literal[False] = ..., **kw) -> np.ndarray: ...
    
    @overload
    def get_data(self, record_id: int, *, return_time: Literal[True], **kw) -> tuple[np.ndarray, np.ndarray]: ...
    
    def get_data(self, record_id: int, 
                 start_sample: int | None = None,
                 stop_sample: int | None = None,
                 sample_range: Sequence[int] | None = None,
                 start_time: float | None = None,
                 stop_time: float | None = None,
                 time_range: Sequence[float] | None = None,
                 start_comment: int | None = None,
                 stop_comment: int | None = None,
                 comment_range: Sequence[int] | None = None,
                 return_time: bool = False) -> np.ndarray | tuple[np.ndarray, np.ndarray]:
        
        """
        Calling Forms
        -------------
        data = chan.get_data(record_id, **options)
        
        time, data = chan.get_data(record_id, return_time=True, **options)
        
        
        Parameters
        ----------
        record_id : numeric
            Which record to retrieve data from. This is ignored if using
            comment IDs
        start_sample : numeric, optional
            Default 1. Ignored if start_time or start_comment is provided.
        stop_sample : numeric, optional
            Default last sample. Ignored if stop_time or stop_comment is provided.
        sample_range : [start, stop], optional
            Convenience alternative to start_sample/stop_sample. Unpacks into
            those parameters, so the same override rules apply.
        start_time : numeric, optional
            Start time in seconds. Overrides start_sample if provided.
        stop_time : numeric, optional
            Stop time in seconds. Overrides stop_sample if provided.
        time_range : [start, stop], optional
            Convenience alternative to start_time/stop_time. Unpacks into
            those parameters, so the same override rules apply.
        start_comment : numeric, optional
            Comment ID. Overrides start_time and start_sample if provided.
        stop_comment : numeric, optional
            Comment ID. Overrides stop_time and stop_sample if provided.
        comment_range : [start, stop], optional
            Convenience alternative to start_comment/stop_comment. Unpacks
            into those parameters, so the same override rules apply.
        return_time : boolean, optional
            If True, returns a tuple of (time_array, data_array).
            The default is False.
            
            
        Returns
        -------
        numpy array, or tuple of (numpy array, numpy array) if return_time=True
        
        
        Priority
        --------
        comment > time > sample. Ranges unpack into their respective 
        start/stop before the cascade runs.
        
        Improvements
        ------------
        1. Currently requesting across two different records (with comments)
        throws an error. We could eventually support multiple records
        and either:
            - place NaNs for missing data
            - interpolate
            ASSUMING: same sampling rate, gets more confusing when fs
            changes between records
        
        """
        
        dt = self.dt[record_id - 1]
    
        # Unpack ranges into individual start/stop
        #------------------------------------------
        if comment_range is not None:
            start_comment, stop_comment = comment_range
            
        if time_range is not None:
            start_time, stop_time = time_range
            
        if sample_range is not None:
            start_sample, stop_sample = sample_range
    
        # Comment → time resolution
        #------------------------------------------
        if start_comment is not None or stop_comment is not None:
            all_comments = self.h_file.get_comments()
            comments_by_id = {c.id: c for c in all_comments}
            
            if start_comment is not None:
                if start_comment not in comments_by_id:
                    raise ValueError(f"No comment found with id {start_comment}")
                c1 = comments_by_id[start_comment]
                start_time = c1.time
                start_record = c1.record_id
                
            if stop_comment is not None:
                if stop_comment not in comments_by_id:
                    raise ValueError(f"No comment found with id {stop_comment}")
                c2 = comments_by_id[stop_comment]    
                stop_time = c2.time
                stop_record = c2.record_id
                
                
            if start_comment is not None and stop_comment is not None:
                if start_record != stop_record:
                    #Eventually we could allow interpolation but 
                    #that is not yet implemented
                    raise ValueError(
                        f"start_comment (record {start_record}) and "
                        f"stop_comment (record {stop_record}) are in different records")
                record_id = start_record
            elif start_comment is not None:
                record_id = start_record
            else:
                record_id = stop_record
            
    
        # Time → sample resolution
        #------------------------------------------
        if start_time is not None:
            start_sample = int(start_time / dt) + 1  
        elif start_sample is None:
            start_sample = 1
        
        if stop_time is not None:
            stop_sample = int(stop_time / dt) + 1
        elif stop_sample is None:
            stop_sample = self.n_samples[record_id - 1]
        
        
        # Validate computed sample bounds
        #------------------------------------------
        if start_sample < 1:
            raise Exception('Computed start_sample is out of range')
        if stop_sample > self.n_samples[record_id - 1]:
            raise Exception('Computed stop_sample is out of range')
    
        data = SDK.get_channel_data(self.h, record_id, self.id, start_sample, stop_sample)
    
        if return_time:
            time = np.arange(start_sample - 1, stop_sample) * dt
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
    rec_stop_datetime : datetime
        
    
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
    
    def add_info(self,duration):
        self.rec_stop_datetime = self.rec_datetime + timedelta(seconds=duration)
    
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
        self.duration = self.tick_dt*self.n_ticks
        
        self.comments = SDK.get_all_comments(self.h,record_id)
        
        #JAH: Why did I do this as a later step?
        #
        #It looks like because everything else is needed by the SDK. Rather
        #than returning something in a more raw form, and then creating the
        #object, the SDK returns the object, which is missing some info
        for c in self.comments:
            c._add_info(self.id,self.tick_dt)
               
        self.record_time = SDK.get_record_time_info(self.h,record_id,self.tick_dt) 
        
        self.record_time.add_info(self.duration)

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
        
        self.channels = [Channel(self.h,x+1,self.records,self) for x in range(self.n_channels)]
        self.channel_names = [x.name for x in self.channels]
            
    @overload
    def get_comments(self, return_as: Literal["list"] = ...) -> list[Comment]: ...
    
    @overload
    def get_comments(self, return_as: Literal["table"]) -> pd.DataFrame: ...
    
    @overload
    def get_comments(self, return_as: Literal["object"]) -> CommentCollection: ...
    
    def get_comments(
        self,
        return_as: Literal["list", "table", "object"] = "list",
    ) -> list[Comment] | pd.DataFrame | CommentCollection:
        """
        Retrieve all comments associated with this file.

        Parameters
        ----------
        return_as : {"list", "table", "object"}, optional
            The format in which to return the comments (default is "list").

            - "list": a plain list of Comment objects.
            - "table": a pandas DataFrame with one row per comment,
              convenient for analysis or export.
            - "object": a CommentCollection wrapping the comments, with
              helper methods for filtering.

        Returns
        -------
        list of Comment or pandas.DataFrame or CommentCollection
            The comments in the requested format. The concrete type depends
            on the value of return_as:

            - list of Comment when return_as="list"
            - pandas.DataFrame when return_as="table"
            - CommentCollection when return_as="object"

        Improvements
        ------------
        1. Expand with ID filtering - return as requested
        2. Expand with word filtering
        """
        
        comments: list[Comment] = []
        record_times: list[RecordTime] = []
           
        for record in self.records:
            comments.extend(record.comments)
            record_times.append(record.record_time)
    
        if return_as == "list":
            return comments
        if return_as == "object":
            return CommentCollection(comments,record_times)
        if return_as == "table":
            return CommentCollection(comments,record_times).to_dataframe()
    
        raise ValueError(f"Unknown return_as value: {return_as!r}")
        
    def get_channel_by_name(self,chan_name,case_sensitive=False,partial_match=True) -> Channel:
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
