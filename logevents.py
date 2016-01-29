from abc import abstractmethod, ABCMeta
from datetime import datetime
import re

def parse_event(timestamp, line, file):
    for event_type in REGISTERED_EVENTS:
        if event_type.is_event(line):
            return event_type(timestamp, line, file)

class LogEvent(metaclass=ABCMeta):
    """Base class for log events."""
    def __init__(self, timestamp, line, file):
        self.timestamp = timestamp
        self.line = line
        self.file = file
    
    @staticmethod
    @abstractmethod
    def is_event(log_line):
        """Return True if this event could be created based on log_line."""
        pass


class MultilineLogEvent(LogEvent, metaclass=ABCMeta):
    def _timestamp_extract(self, line):
        """
        Return a datetime and log file line remainder.
    
        The timestamp should be in HH:MM:SS DD/MM/YYYY format, where the
        time is in 24-hour format. The timestamp should be at the
        beginning of the line. A semicolon may optionally be present at the
        end of the timestamp (in the log line) which will be stripped.
    
        If a conforming timestamp is not found, or if the log file line 
        does not have the expected structure, a ValueError will be raised.
        """
        try:
            splitted = re.split(' ', line, maxsplit=2)
            # sometimes there is a stray semicolon...
            timestampstr = (splitted[0] + ' ' + splitted[1]).strip(';')
            timestamp = datetime.strptime(timestampstr, '%H:%M:%S %d/%m/%Y')
            final_value = (timestamp, splitted[2])
        except ValueError:
            raise ValueError("Couldn't parse log file timestamp")
        except IndexError:
            raise ValueError("Log file line has unexpected structure")
        return final_value


class LoggedInEvent(LogEvent):
    """Event representing user login."""
    @staticmethod
    def is_event(log_line):
        return 'Logged in' in log_line


class NewUserEvent(LoggedInEvent):
    """Event representing user registration."""
    @staticmethod
    def is_event(log_line):
        test = False
        test |= 'Registred as a new user' in log_line
        test |= 'Registered as a new user' in log_line
        return test


class StudentModelCreatedEvent(LogEvent):
    """Event representing the creation of a student model."""
    @staticmethod
    def is_event(log_line):
        return 'Student model file created.' in log_line


class DatabaseSetEvent(LogEvent):
    """Event representing a database change in the tutor."""
    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        self._database = line.split(' ').pop().strip()

    @property
    def database(self):
        """Get the name of the new databse."""
        return self._database
    
    @staticmethod
    def is_event(log_line):
        return 'Database is set to' in log_line


class SetNewProblemEvent(LogEvent):
    """Event representing setting of new problem."""
    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        self._help_level = int(line.split(' ').pop().strip())
    
    @property
    def help_level(self):
        """Get new help level set as a consequence of setting new problem."""
        return self._help_level
    
    @staticmethod
    def is_event(log_line):
        return 'set-new-problem' in log_line


class DatabaseChangeEvent(LogEvent):
    """Represent a database change, initiated by the user."""
    DB_RE = re.compile('Changing database to ([a-z-]+)\s')
        
    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        self._database = re.match(self.DB_RE, line).group(1)
        self._problem = int(line.split(' ').pop().strip())

    @property
    def database(self):
        """Get new database name."""
        return self._database
    
    @property
    def problem(self):
        """Get new problem name."""
        return self._problem
    
    @staticmethod
    def is_event(log_line):
        return 'Changing database to ' in log_line
        

class DrawingProblemEvent(LogEvent):
    """Event representing problem selected by system."""
    RE = re.compile('drawing problem: ([0-9]+), problem status: ([A-Z]+)')
    RE_OLD = re.compile('Chosing new problem. Current problem No ([0-9]+); ' +
        'status: ([A-Z]+)')
    
    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        if 'drawing' in line:
            match = re.match(self.RE, line)
        else:
            match = re.match(self.RE_OLD, line)
        try:
            self._problem_id = int(match.group(1))
            self._problem_status = match.group(2)
        except AttributeError:
            raise ValueError("Couldn't extract to DrawingProblemEvent")
    
    @property
    def problem_id(self):
        """Get new problem ID"""
        return self._problem_id
    
    @property
    def problem_status(self):
        """Get problem status (e.g. NEW, CONSIDERED, FINISHED)"""
        return self._problem_status
    
    @staticmethod
    def is_event(log_line):
        return 'drawing problem' in log_line or 'Chosing' in log_line


class ClientRespondingEvent(MultilineLogEvent):
    """Event caused by user responding to new problem"""
    RE_1 = re.compile('responding: problem is ([0-9]+) its status is ([A-Z]+)')
    RE_2 = re.compile('responding: also set help-level to ([0-9]), ' +
        'feedback=([A-Za-z ]+)')
    
    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        self._help_level = None
        self._feedback_level = None
        self._problem_id = None
        self._problem_status = None
        match = re.match(self.RE_1, line)
        if match:
            self._problem_id = int(match.group(1))
            self._problem_status = match.group(2)
        
        # there are two lines here
        line2_timestamp, line2 = self._timestamp_extract(file.readline())
        if not (line2_timestamp - timestamp).total_seconds() <= 1:
            print("Inspect log file - slow server?")
        line2_match = re.match(self.RE_2, line2)
        if line2_match:
            self._help_level = int(line2_match.group(1))
            self._feedback_level = line2_match.group(2)
    
    @property
    def problem_id(self):
        """Get problem ID."""
        return self._problem_id
    
    @property
    def problem_status(self):
        """Get problem status (e.g. NEW, CONSIDERED, FINISHED)"""
        return self._problem_status
    
    @property
    def help_level(self):
        """Get help level (from 0 to 5)"""
        return self._help_level
    
    @property
    def feedback_level(self):
        """Get feedback level (e.g. Simple Feedback, Hint, ErrorFlag)"""
        return self._feedback_level
    
    @staticmethod
    def is_event(log_line):
        return 'responding:' in log_line


class PreProcessEvent(MultilineLogEvent):
    # this one is a stub since we don't really need it
    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        self._solution = line
        while 'Mode: ' not in line:
            line = file.readline()
            self._solution += line
    
    @property
    def solution(self): 
        return self._solution
    
    @staticmethod
    def is_event(log_line):
        return 'Pre-process:' in log_line


class AnswerCorrectEvent(LogEvent):
    """Event representing a correct submission (yay! :D)"""
    @staticmethod
    def is_event(log_line):
        return 'Answer correct' in log_line


class HelpLevelSetEvent(LogEvent):
    """Event representing help level change"""
    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        self._help_level = int(line.split(' ').pop().strip())
    
    @property
    def help_level(self):
        """Get help level (from 0 to 5)"""
        return self._help_level

    @staticmethod
    def is_event(log_line):
        return 'Now help-level is ' in log_line
        

class PostProcessEvent(MultilineLogEvent):
    """Event representing solution evaluation (post-processing)."""
    RE = re.compile(
        'Post-process:\s*' +
        'Satisfied constraints: (?:\(([0-9\s]+)\)|NIL);?\s*' + 
        'Violated constraints: (?:\(([0-9\s]+)\)|NIL);?\s*' + 
        'Feedback level: ([0-9])')
    
    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        if 'Satisfied' in line and 'Violated' in line:
            # we have everything on one line
            self._parse_one_line(line)
        else:
            # need to iterate over lines until blank line
            self._parse_multiline(line)
    
    def _parse_one_line(self, line):
        match_groups = re.match(self.RE, line)
        if not match_groups.group(1):
            self._satisfied_constraints = []
        else:
            string_constraints = match_groups.group(1).split()
            self._satisfied_constraints = [int(x) for x in string_constraints]
        if not match_groups.group(2):
            self._violated_constraints = []
        else:
            string_constraints = match_groups.group(2).split()
            self._violated_constraints = [int(x) for x in string_constraints]
        self._feedback_level = int(match_groups.group(3))
    
    def _parse_multiline(self, init_line):
        space_count = 0
        last_line = init_line
        final_result = init_line
        while space_count < 2:
            last_line = self.file.readline()
            final_result += last_line
            if last_line.isspace():
                space_count += 1
        self._parse_one_line(final_result)
    
    @property
    def satisfied_constraints(self):
        """Get a list of satisfied constraint IDs."""
        return self._satisfied_constraints
    
    @property
    def violated_constraints(self):
        """Get a list of violated constraint IDs (empty if none)."""
        return self._violated_constraints
    
    @property
    def feedback_level(self):
        """Get human readable feedback level."""
        return self._feedback_level
    
    @staticmethod
    def is_event(log_line):
        return 'Post-process:' in log_line


class IncorrectFeedbackEvent(LogEvent):
    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        self._feedback = line
    
    @property
    def feedback(self):
        return self.feedback
    
    @staticmethod
    def is_event(log_line):
        return ' feedback ' in log_line


class StudentModelMeasureEvent(LogEvent):
    RE = re.compile('select-meas:([0-9]+)/?([0-9]*) ' + 
        'from-meas:([0-9]+)/?([0-9]*) where-meas:([0-9]+)/?([0-9]*) ' + 
        'group-meas:([0-9]+)/?([0-9]*) having-meas:([0-9]+)/?([0-9]*) ' +
        'order-meas:([0-9]+)/?([0-9]*)')

    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        match_groups = re.match(self.RE, line)
        self._select_meas_correct = int(match_groups.group(1))
        self._select_meas_total = self._zero_if_empty(match_groups.group(2))
        self._from_meas_correct = int(match_groups.group(3))
        self._from_meas_total = self._zero_if_empty(match_groups.group(4))
        self._where_meas_correct = int(match_groups.group(5))
        self._where_meas_total = self._zero_if_empty(match_groups.group(6))
        self._group_meas_correct = int(match_groups.group(7))
        self._group_meas_total = self._zero_if_empty(match_groups.group(8))
        self._having_meas_correct = int(match_groups.group(9))
        self._having_meas_total = self._zero_if_empty(match_groups.group(10))
        self._order_meas_correct = int(match_groups.group(11))
        self._order_meas_total = self._zero_if_empty(match_groups.group(12))
    
    @property
    def from_meas_correct(self):
        return self._from_meas_correct
    
    @property
    def from_meas_total(self):
        return self._from_meas_total
    
    @property
    def where_meas_correct(self):
        return self._where_meas_correct
    
    @property
    def where_meas_total(self): 
        return self._where_meas_total
    
    @property
    def group_meas_correct(self):
        return self._group_meas_correct
    
    @property
    def group_meas_total(self):
        return self._group_meas_total
    
    @property
    def having_meas_correct(self):
        return self._having_meas_correct
    
    @property
    def having_meas_total(self):
        return self._having_meas_total
    
    @property
    def order_meas_correct(self):
        return self._order_meas_correct
    
    @property
    def order_meas_total(self):
        return self._order_meas_total
    
    @property
    def select_meas_percentage(self):
        if self._select_meas_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._select_meas_correct / self._select_meas_total
    
    @property
    def from_meas_percentage(self):
        if self._from_meas_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._from_meas_correct / self._from_meas_total
    
    @property
    def where_meas_percentage(self):
        if self._where_meas_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._where_meas_correct / self._where_meas_total
    
    @property
    def group_meas_percentage(self):
        if self._group_meas_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._group_meas_correct / self._group_meas_total
    
    @property
    def having_meas_percentage(self):
        if self._having_meas_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._having_meas_correct / self._having_meas_total
    
    @property
    def order_meas_percentage(self):
        if self._order_meas_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._order_meas_correct / self._order_meas_total
    
    def _zero_if_empty(self, string):
        if len(string) == 0:
            return 0
        else:
            return int(string)
    
    @staticmethod
    def is_event(log_line):
        return 'from-meas:' in log_line


class StudentModelCoverageEvent(LogEvent):
    RE = re.compile('select-cov:([0-9]+)/?([0-9]*) ' + 
        'from-cov:([0-9]+)/?([0-9]*) where-cov:([0-9]+)/?([0-9]*) ' + 
        'group-cov:([0-9]+)/?([0-9]*) having-cov:([0-9]+)/?([0-9]*) ' +
        'order-cov:([0-9]+)/?([0-9]*)')

    def __init__(self, timestamp, line, file):
        super().__init__(timestamp, line, file)
        match_groups = re.match(self.RE, line)
        self._select_cov_correct = int(match_groups.group(1))
        self._select_cov_total = self._zero_if_empty(match_groups.group(2))
        self._from_cov_correct = int(match_groups.group(3))
        self._from_cov_total = self._zero_if_empty(match_groups.group(4))
        self._where_cov_correct = int(match_groups.group(5))
        self._where_cov_total = self._zero_if_empty(match_groups.group(6))
        self._group_cov_correct = int(match_groups.group(7))
        self._group_cov_total = self._zero_if_empty(match_groups.group(8))
        self._having_cov_correct = int(match_groups.group(9))
        self._having_cov_total = self._zero_if_empty(match_groups.group(10))
        self._order_cov_correct = int(match_groups.group(11))
        self._order_cov_total = self._zero_if_empty(match_groups.group(12))
    
    @property
    def from_cov_correct(self):
        return self._from_cov_correct
    
    @property
    def from_cov_total(self):
        return self._from_cov_total
    
    @property
    def where_cov_correct(self):
        return self._where_cov_correct
    
    @property
    def where_cov_total(self): 
        return self._where_cov_total
    
    @property
    def group_cov_correct(self):
        return self._group_cov_correct
    
    @property
    def group_cov_total(self):
        return self._group_cov_total
    
    @property
    def having_cov_correct(self):
        return self._having_cov_correct
    
    @property
    def having_cov_total(self):
        return self._having_cov_total
    
    @property
    def order_cov_correct(self):
        return self._order_cov_correct
    
    @property
    def order_cov_total(self):
        return self._order_cov_total
    
    @property
    def select_cov_percentage(self):
        if self._select_cov_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._select_cov_correct / self._select_cov_total
    
    @property
    def from_cov_percentage(self):
        if self._from_cov_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._from_cov_correct / self._from_cov_total
    
    @property
    def where_cov_percentage(self):
        if self._where_cov_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._where_cov_correct / self._where_cov_total
    
    @property
    def group_cov_percentage(self):
        if self._group_cov_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._group_cov_correct / self._group_cov_total
    
    @property
    def having_cov_percentage(self):
        if self._having_cov_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._having_cov_correct / self._having_cov_total
    
    @property
    def order_cov_percentage(self):
        if self._order_cov_total == 0:
            # return None instead of divide by zero
            return None
        else:
            return self._order_cov_correct / self._order_cov_total
    
    def _zero_if_empty(self, string):
        if len(string) == 0:
            return 0
        else:
            return int(string)
    
    @staticmethod
    def is_event(log_line):
        return 'from-cov:' in log_line


class DisplayingStudentModelEvent(LogEvent):
    @staticmethod
    def is_event(log_line):
        return 'displaying student model' in log_line

class SessionEndEvent(LogEvent):   
    @staticmethod
    def is_event(log_line):
        return re.search("[L|l]ogged out", log_line)


class UnknownEvent(LogEvent):
    """A catch-all event if no other event caught a log line."""
    @staticmethod
    def is_event(log_line):
        return True
        

# this has to be after the event class definitions or Python won't see 
# the classes and will get confused... :(
REGISTERED_EVENTS = [
    NewUserEvent,
    StudentModelCreatedEvent,
    DatabaseSetEvent,
    SetNewProblemEvent,
    DatabaseChangeEvent,
    DrawingProblemEvent,
    ClientRespondingEvent,
    PreProcessEvent,
    AnswerCorrectEvent,
    HelpLevelSetEvent,
    PostProcessEvent,
    IncorrectFeedbackEvent,
    StudentModelMeasureEvent,
    StudentModelCoverageEvent,
    DisplayingStudentModelEvent,
    SessionEndEvent,
    LoggedInEvent,
    # NB: make sure UnknownEvent is last or it will eat all others!
    # Especially take care if you are planning on appending to this 
    UnknownEvent
]