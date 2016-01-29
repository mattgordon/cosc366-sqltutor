import logevents
from abc import abstractmethod, ABCMeta
from statistics import mean, stdev

class FeatureBase(metaclass=ABCMeta):
    """Base class for features."""
    def __init__(self):
        self._last_submission = None
        self._submission = None
        self._values = []
    
    @property
    @abstractmethod
    def name(self):
        return None
    
    @property
    @abstractmethod
    def type(self):
        return None
    
    def new_submission(self, submission):
        self._last_submission = self._submission
        self._submission = submission
        self._values.append(self._submission_value())
    
    @abstractmethod
    def _submission_value(self):
        pass
    
    @property
    def values(self):
        return self._values
    
    def clear_submissions(self):
        self._last_submission = None
        self._submission = None
        self._after_clear()
    
    def _after_clear(self):
        pass


class CumulativeStatisticsFeatureBase(FeatureBase, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()
        self._mean_values = []
        self._mean_values_src = []
        self._stdev_values = []
        self._stdev_values_src = []
        self._max_values = []
        self._max_values_src = []
        self._min_values = []
        self._min_values_src = []
    
    def new_submission(self, submission):
        super().new_submission(submission)
        if self.clear_src_values_for_session():
            self._mean_values_src = []
            self._stdev_values_src = []
            self._max_values_src = []
            self._min_values_src = []
        if self.should_add_mean():
            self._mean_values_src.append(self._values[-1])
        if len(self._mean_values_src) > 0:
            self._mean_values.append(mean(self._mean_values_src))
        else:
            self._mean_values.append(None)
        if self.should_add_stdev():
            self._stdev_values_src.append(self._values[-1])
        if len(self._stdev_values_src) > 1:
            self._stdev_values.append(stdev(self._stdev_values_src))
        else:
            self._stdev_values.append(None)
        self._max_values.append(
            max(
                filter(
                    lambda v: v is not None, self._values),
                default=None))
        self._min_values.append(
            min(
                filter(
                    lambda v: v is not None, self._values),
                default=None))
    
    def clear_src_values_for_session(self):
        return False
        
    def use_values(self):
        return False
    
    @property
    def type(self):
        return "numeric"
    
    @property
    def mean_values(self):
        return self._mean_values
    
    @property
    def stdev_values(self):
        return self._stdev_values
    
    @property
    def max_values(self):
        return self._max_values
    
    @property
    def min_values(self):
        return self._min_values
    
    @abstractmethod
    def should_add_stdev(self):
        pass
    
    @abstractmethod
    def should_add_mean(self):
        pass


class TimeUntilFirstSubmission(CumulativeStatisticsFeatureBase):
    @property
    def name(self):
        return "time_until_first_sub"

    def __init__(self):
        super().__init__()
        self._current_prob_id = None
        self._current_prob_first_submission = None

    def _submission_value(self):
        if self._current_prob_id != self._submission.problem_id and \
            self._submission.problem_id is not None:
            self._current_prob_id = self._submission.problem_id
            self._current_prob_first_submission = self._submission
        if self._current_prob_first_submission is not None and \
            self._current_prob_first_submission.begin_time is not None:
            return (self._current_prob_first_submission.submit_time -
                     self._current_prob_first_submission.begin_time) \
                    .total_seconds()
        else:
            return None
    
    def should_add_mean(self):
        return self._current_prob_id is not None and \
            self._current_prob_first_submission is not None and \
            self._current_prob_first_submission.begin_time is not None
    
    def should_add_stdev(self):
        return self.should_add_mean()
        

class PreviousProblemFeatureBase(FeatureBase, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()
        self._prev_prob_submissions = []
        self._current_prob_submissions = []
        self._current_prob_id = None
    
    def new_submission(self, submission):
        self._last_submission = self._submission
        self._submission = submission
        if self._current_prob_id is None:
            self._current_prob_id = submission.problem_id
        if self._current_prob_id == submission.problem_id:
            self._current_prob_submissions.append(submission)
        else:
            self._prev_prob_submissions = self._current_prob_submissions
            self._current_prob_id = submission.problem_id
            self._current_prob_submissions = []
            self._current_prob_submissions.append(submission)
        if len(self._prev_prob_submissions) == 0:
            self._values.append(None)
        else:
            self._values.append(self._submission_value())
    
    @property
    def values(self):
        return self._values


class ViolatedConstraints(CumulativeStatisticsFeatureBase):
    @property
    def name(self):
        return "violated_constraints"
    
    def _submission_value(self):
        if self._submission.solution is not None:
            return len(self._submission.violated_constraints)
        else:
            return None
    
    def use_values(self):
        return True
    
    def should_add_mean(self):
        return self._submission.solution is not None
    
    def should_add_stdev(self):
        return self._submission.solution is not None


class SatisfiedConstraints(FeatureBase):
    @property
    def name(self):
        return "satisfied_constraints"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        if self._submission.solution is not None:
            return len(self._submission.satisfied_constraints)
        else:
            return None
    
    def use_values(self):
        return True
    
    def should_add_mean(self):
        return self._submission.solution is not None
    
    def should_add_stdev(self):
        return self._submission.solution is not None


class HelpLevel(FeatureBase):
    @property
    def name(self):
        return "help_level"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        return self._submission.submit_help_level


class DecreasedViolatedConstraints(FeatureBase):
    @property
    def name(self):
        return "violated_constraints_decreased"
    
    @property
    def type(self):
        return "{True, False}"
    
    def _submission_value(self):
        if self._last_submission is None:
            return None
        else:
            return len(self._submission.violated_constraints) < \
                len(self._last_submission.violated_constraints)
                

class TimeSincePreviousSubmission(FeatureBase):
    @property
    def name(self):
        return "time_since_previous_submission"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        if self._last_submission is None:
            return None
        elif self._submission.begin_session is not None:
            return None
        else:
            try:
                return (self._submission.submit_time - 
                    self._last_submission.submit_time).total_seconds()
            except TypeError:
                return None


class ProblemTimeFromStart(FeatureBase):
    @property
    def name(self):
        return "problem_time_from_start"
    
    @property
    def type(self):
        return "numeric"
    
    def __init__(self):
        super().__init__()
        self._current_problem_id = None
        self._problem_start_time = None
    
    def _submission_value(self):
        try:
            if self._current_problem_id == self._submission.problem_id:
                return (self._submission.submit_time 
                    - self._problem_start_time).total_seconds()
            else:
                self._current_problem_id = self._submission.problem_id
                self._problem_start_time = self._submission.begin_time
                return (self._submission.submit_time - 
                    self._submission.begin_time).total_seconds()
        except TypeError:
            return None
                
                
class SubmissionNumber(FeatureBase):
    @property
    def name(self):
        return "submission_number"
    
    @property
    def type(self):
        return "numeric"
    
    def __init__(self):
        super().__init__()
        self._submission_count = 1
    
    def _submission_value(self):
        if self._last_submission is None:
            self._submission_count = 1
        elif self._last_submission.problem_id != self._submission.problem_id:
            self._submission_count = 1
        else:
            self._submission_count += 1
        return self._submission_count
        

class SessionTimeFromStart(FeatureBase):
    @property
    def name(self):
        return "session_time_from_start"
    
    @property
    def type(self):
        return "numeric"
    
    def __init__(self):
        super().__init__()
        self._session_start = None
    
    def _submission_value(self):
        try:
            if self._submission.begin_session is not None:
                self._session_start = self._submission.begin_session
            time = (self._submission.submit_time - 
                self._session_start).total_seconds()
            assert time >= 0
            return time
        except TypeError:
            return None


class SubmissionTimeDifference(FeatureBase):
    @property
    def name(self):
        return "submission_time_diff_sq"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        if self._last_submission is None:
            return None
        else:
            try:
                return (self._submission.submit_time - 
                    self._last_submission.submit_time).total_seconds() ** 2
            except TypeError:
                return None


class FirstSubmitTimePrev(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_first_submit_time"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        first_sub = self._prev_prob_submissions[0]
        try:
            return (first_sub.submit_time - 
                first_sub.begin_time).total_seconds()
        except TypeError:
            return None


class TimeTakenPrev(PreviousProblemFeatureBase):
    @property
    def name(self): 
        return "prev_time_taken"
    
    @property
    def type(self):
        return "numeric"
        
    def _submission_value(self):
        first_sub = self._prev_prob_submissions[0]
        last_sub = self._prev_prob_submissions[-1]
        try:
            time = (last_sub.submit_time - 
                first_sub.begin_time).total_seconds()
            if time > 1000000:
                print(last_sub.submit_time)
                print(first_sub.begin_time)
        except TypeError:
            return None


class CompletedPrev(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_completed"
    
    @property
    def type(self):
        return "{True, False}"
    
    def _submission_value(self):
        return any([s.solved for s in self._prev_prob_submissions])


class SubmissionCountPrev(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_submission_count"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        return len(self._prev_prob_submissions)


class MaxViolatedConstraints(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_max_violated_constraints"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        return max([len(s.violated_constraints) 
            for s in self._prev_prob_submissions])


class NumberWrongSubmissions(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_count_wrong_submissions"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        return len(list(
            filter(lambda s: not s.solved, self._prev_prob_submissions)))


class AverageSubmissionTime(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_avg_submission_time"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        data = [(s.submit_time - s.begin_time).total_seconds() 
            for s in self._prev_prob_submissions
            if s.submit_time is not None and s.begin_time is not None]
        if len(data) == 0:
            return None
        else:
            return mean(data)


class LatestSubmissionTime(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_latest_submission_time"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        last_sub = self._prev_prob_submissions[-1]
        if last_sub.submit_time is not None and \
            last_sub.begin_time is not None:
            assert last_sub.submit_time >= last_sub.begin_time
            return (last_sub.submit_time - last_sub.begin_time).total_seconds()
        else:
            return None


class StdevSubmissionTime(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_stdev_submission_time"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        data = [(s.submit_time - s.begin_time).total_seconds()
                for s in self._prev_prob_submissions
                if s.submit_time is not None and s.begin_time is not None]
        if len(data) < 2:
            return None
        else:
            return stdev(data)


class MaxSubmissionTime(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_max_submission_time"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        data = [(s.submit_time - s.begin_time).total_seconds()
            for s in self._prev_prob_submissions
            if s.submit_time is not None and s.begin_time is not None]
        if len(data) == 0:
            return None
        else:
            return max(data)


class MinSubmissionTime(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_min_submission_time"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        data = [(s.submit_time - s.begin_time).total_seconds()
            for s in self._prev_prob_submissions
            if s.submit_time is not None and s.begin_time is not None]
        if len(data) == 0:
            return None
        else:
            return min(data)


class SameDatabasePrev(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_problem_same_db"
    
    @property
    def type(self):
        return "{True, False}"
    
    def _submission_value(self):
        return self._current_prob_submissions[0].database is not None


class DifferentFeedbackOptionsPrev(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_diff_feedback_options"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        return len(set(
            [s.submit_help_level for s in self._prev_prob_submissions]))


class TimeSinceSessionStartPrev(PreviousProblemFeatureBase):
    @property
    def name(self):
        return "prev_time_since_session_start"
    
    @property
    def type(self):
        return "numeric"
    
    def __init__(self):
        super().__init__()
        self._session_start = None
    
    def _submission_value(self):
        if self._prev_prob_submissions[0].begin_time is None:
            print("Inspect log file!")
            return None
        for sub in self._prev_prob_submissions:
            if sub.begin_session is not None and (self._session_start is None
                or (self._prev_prob_submissions[0].begin_time 
                    - sub.begin_session).total_seconds() >= 0):
                self._session_start = sub.begin_session
        time = (self._prev_prob_submissions[0].begin_time -
            self._session_start).total_seconds()
        if time > 100000:
            print(self._submission.submit_time)
            print('huh?' + str(time))
        assert time >= 0
        return time


class ProblemsAttemptedCumulative(FeatureBase):
    @property
    def name(self):
        return "session_problems_attempted"
    
    @property
    def type(self):
        return "numeric"
    
    def __init__(self):
        super().__init__()
        self._attempted_problems = set()
    
    def _submission_value(self):
        if self._submission.begin_session is not None:
            self._attempted_problems = set()
        self._attempted_problems.add(self._submission.problem_id)
        return len(self._attempted_problems)


class ProblemsCompletedCumulative(FeatureBase):
    @property
    def name(self):
        return "session_problems_completed"
    
    @property
    def type(self):
        return "numeric"
    
    def __init__(self):
        super().__init__()
        self._completed_problems = set()
    
    def _submission_value(self):
        if self._submission.begin_session is not None:
            self._completed_problems = set()
        if self._submission.solved:
            self._completed_problems.add(self._submission.problem_id)
        return len(self._completed_problems)


class DatabaseChangesCumulative(FeatureBase):
    @property
    def name(self):
        return "session_database_changes"
    
    @property
    def type(self):
        return "numeric"
    
    def __init__(self):
        super().__init__()
        self._databases = 0
    
    def _submission_value(self):
        self._databases += self._submission.database_changes
        return self._databases


class TimeSpentOnProblem(CumulativeStatisticsFeatureBase):
    @property
    def name(self):
        return "session_problem_completion_time"
    
    def __init__(self):
        super().__init__()
        self._current_problem_id = None
        self._current_problem_start = None
        self._last_problem_duration = None
        self._problem_changed = False
    
    def _submission_value(self):
        if self._current_problem_id != self._submission.problem_id:
            if self._current_problem_start is not None and \
                self._last_submission.submit_time is not None:
                self._last_problem_duration = (
                    self._last_submission.submit_time -
                    self._current_problem_start).total_seconds()
                self._problem_changed = True
            self._current_problem_id = self._submission.problem_id
            self._current_problem_start = self._submission.begin_time
        else:
            self._problem_changed = False
        return self._last_problem_duration
    
    def should_add_mean(self):
        return self._problem_changed
    
    def should_add_stdev(self):
        return self._problem_changed


class TimeBetweenSubmissions(CumulativeStatisticsFeatureBase):
    @property
    def name(self):
        return "session_time_between_submissions"
    
    def _submission_value(self):
        if self._submission.begin_session is not None:
            self._last_submission = None
            return None
        elif self._last_submission is not None and \
            self._submission.submit_time is not None and \
            self._last_submission.submit_time is not None:
            return (self._submission.submit_time - 
                self._last_submission.submit_time).total_seconds()
        else:
            return None
            
    def should_add_mean(self):  
        return self._last_submission is not None and \
            self._submission.submit_time is not None and \
            self._last_submission.submit_time is not None
    
    def should_add_stdev(self):
        return self._last_submission is not None and \
            self._submission.submit_time is not None and \
            self._last_submission.submit_time is not None


class NumberOfSubmissions(CumulativeStatisticsFeatureBase):
    @property
    def name(self):
        return "num_submissions_per_problem"
    
    def __init__(self):
        super().__init__()
        self._current_problem_id = None
        self._prev_prob_submissions = None
        self._current_problem_submissions = None
        self._problem_changed = False
    
    def _submission_value(self):
        if self._current_problem_id is None and \
            self._submission.problem_id is None:
            self._problem_changed = False
        elif self._current_problem_id != self._submission.problem_id:
            self._prev_prob_submissions = self._current_problem_submissions
            self._current_problem_id = self._submission.problem_id
            self._current_problem_submissions = 1
            if self._prev_prob_submissions is not None:
                self._problem_changed = True
        else:
            self._current_problem_submissions += 1
            self._problem_changed = False
        return self._prev_prob_submissions
    
    def should_add_mean(self):
        return self._problem_changed
    
    def should_add_stdev(self):
        return self._problem_changed


class ProblemComplexityPrev(PreviousProblemFeatureBase):
    FILE = open('complexity-data.txt')
    LOOKUP = {}
    
    @property
    def name(self):
        return "prev_problem_complexity"
    
    @property
    def type(self):
        return "numeric"
    
    def __init__(self):
        super().__init__()
        if len(self.LOOKUP) == 0:
            for line in self.FILE:
                line_split = line.split()
                self.LOOKUP[int(line_split[0])] = int(line_split[1])
    
    def _submission_value(self):
        try:
            return self.LOOKUP[self._prev_prob_submissions[0].problem_id]
        except KeyError:
            print('Dirty log!')


class ProblemComplexity(CumulativeStatisticsFeatureBase):
    FILE = open('complexity-data.txt')
    LOOKUP = {}
    
    @property
    def name(self):
        return "current_problem_complexity"
    
    def __init__(self):
        super().__init__()
        if len(self.LOOKUP) == 0:
            for line in self.FILE:
                line_split = line.split()
                self.LOOKUP[int(line_split[0])] = int(line_split[1])
        self._current_prob_id = None
        self._problem_changed = False
    
    def use_values(self):
        return True
    
    def _submission_value(self):
        if self._current_prob_id != self._submission.problem_id:
            self._problem_changed = True
            self._current_prob_id = self._submission.problem_id
        else:
            self._problem_changed = False
        if self._submission.problem_id is None:
            self._problem_changed = False
            return None
        else:
            try:
                return self.LOOKUP[self._submission.problem_id]
            except KeyError:
                self._problem_changed = None
                print('Dirty log!')
    
    def should_add_mean(self):
        return self._problem_changed
            
    def should_add_stdev(self):
        return self._problem_changed


class StudentLevel(FeatureBase):
    FILE = open('complexity-data.txt')
    LOOKUP = {}
    
    def __init__(self):
        super().__init__()
        self._level = 0
        self._current_prob_id = None
        self._current_prob_attempts = 0
        self._current_prob_solved = False
        self._current_prob_level = 0
        self._prev_prob_level = 0
        self._prev_prob_solved = False
        self._prev_prob_attempts = 0
        if len(self.LOOKUP) == 0:
            for line in self.FILE:
                line_split = line.split()
                self.LOOKUP[int(line_split[0])] = int(line_split[1])
    
    @property
    def name(self):
        return "student_level"
    
    @property
    def type(self):
        return "numeric"
    
    def _submission_value(self):
        # update problems
        if self._current_prob_id != self._submission.problem_id \
            and self._submission.problem_id in self.LOOKUP:
            # check if decrease necessary
            if not self._prev_prob_solved and not self._current_prob_solved \
                and self._current_prob_attempts >= 5  \
                and self._prev_prob_attempts >= 5  \
                and self._prev_prob_level <= self._level \
                and self._current_prob_level <= self._level \
                and self._level > 0:
                self._level -= 1
            self._prev_prob_level = self._current_prob_level
            self._prev_prob_solved = self._current_prob_solved
            self._prev_prob_attempts = self._current_prob_attempts
            self._current_prob_id = self._submission.problem_id
            self._current_prob_level = self.LOOKUP[self._current_prob_id]
            self._current_prob_attempts = 1
        else:
            self._current_prob_attempts += 1
        self._current_prob_solved = self._submission.solved
        # check if increase necessary
        if self._prev_prob_attempts <= 3 and self._current_prob_attempts <= 3 \
            and self._prev_prob_solved and self._current_prob_solved and \
            self._prev_prob_level >= self._level and \
            self._current_prob_level >= self._level:
            self._level += 1
        return self._level


class StudentLevelComplexityDifference(StudentLevel):
    @property
    def name(self):
        return "student_level_complexity_difference"
    
    def _submission_value(self):
        level = super()._submission_value()
        return self._current_prob_level - level


class IdenticalSubmission(StudentLevel):
    @property
    def name(self):
        return "submission_same_as_previous"
    
    @property
    def type(self):
        return "{True, False}"
    
    def _submission_value(self):
        if self._submission is not None and self._last_submission is not None:
            return self._submission.solution == self._last_submission.solution
        else:
            return False

def build_features(submissions):
    submission_features = [feature() for feature in FEATURES]
    for submission in submissions:
        if should_skip_subm(submission):
            continue
        for feature in submission_features:
            feature.new_submission(submission)
    return submission_features

def should_skip_subm(submission):
    skip = submission.solution is None and submission.begin_session is None
    if skip:
        print(submission.__dict__)
    return skip

FEATURES = [
    ViolatedConstraints,
    SatisfiedConstraints,
    HelpLevel,
    DecreasedViolatedConstraints,
    TimeSincePreviousSubmission,
    ProblemTimeFromStart,
    SubmissionNumber,
    SessionTimeFromStart,
    SubmissionTimeDifference,
    FirstSubmitTimePrev,
    TimeTakenPrev,
    CompletedPrev,
    SubmissionCountPrev,
    MaxViolatedConstraints,
    NumberWrongSubmissions,
    AverageSubmissionTime,
    LatestSubmissionTime,
    StdevSubmissionTime,
    MaxSubmissionTime,
    MinSubmissionTime,
    SameDatabasePrev,
    DifferentFeedbackOptionsPrev,
    TimeSinceSessionStartPrev,
    ProblemsAttemptedCumulative,
    ProblemsCompletedCumulative,
    DatabaseChangesCumulative,
    TimeSpentOnProblem,
    TimeBetweenSubmissions,
    NumberOfSubmissions,
    ProblemComplexity,
    ProblemComplexityPrev,
    StudentLevel,
    StudentLevelComplexityDifference,
    IdenticalSubmission,
    TimeUntilFirstSubmission
]