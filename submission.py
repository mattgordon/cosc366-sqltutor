import logevents

class Submission():
    def __init__(self):
        self.database_changes = 0 #
        self.violated_constraints = [] #
        self.satisfied_constraints = [] #
        self.problem_status = None #
        self.begin_help_level = None #
        self.submit_help_level = None #
        self.begin_time = None #
        self.submit_time = None #
        self.solved = False #
        self.problem_id = None #
        self.database = None
        self.model_measure_event = None #
        self.begin_session = None
        self.end_session = None
        self.solution = None
    
    def pre_process(self, event):
        self.solution = event.solution
    
    def post_process(self, event):
        self.violated_constraints = event.violated_constraints
        self.satisfied_constraints = event.satisfied_constraints
        self.submit_time = event.timestamp
        if len(event.violated_constraints) == 0:
            self.solved = True
    
    def database_change(self, event):
        if event.database != self.database:
            self.database_changes += 1
            self.database = event.database
        if self.begin_time is None:
            self.begin_time = event.timestamp
        if hasattr(event, 'problem'):
            self.problem_id = event.problem
    
    def help_level_set(self, event):
        pass
    
    def model_measure(self, event):
        self.model_measure_event = event
    
    def client_response(self, event):
        self.problem_id = event.problem_id
        self.problem_status = event.problem_status
        self.submit_help_level = event.help_level
    
    def drawing_problem(self, event):
        # 'best quality' begin time
        self.begin_time = event.timestamp
        self.problem_id = event.problem_id
    
    def set_problem(self, event):
        self.begin_help_level = event.help_level
        self.begin_time = event.timestamp
    
    def session_begin(self, event):
        self.begin_session = event.timestamp
    
    def session_end(self, event):
        self.end_session = event.timestamp


def events_to_submissions(events):
    current_submission = Submission()
    submissions = []
    should_start_new_sub = True
    for event in events:
        if isinstance(event, logevents.LoggedInEvent):
#             if should_start_new_sub:
#                 current_submission = Submission()
#                 submissions.append(current_submission)
#                 should_start_new_sub = False
            current_submission.session_begin(event)
            
        elif isinstance(event, logevents.SetNewProblemEvent):
#             if should_start_new_sub:
#                 current_submission = Submission()
#                 submissions.append(current_submission)
#                 should_start_new_sub = False
            current_submission.set_problem(event)
            
        elif isinstance(event, logevents.DatabaseSetEvent) or \
            isinstance(event, logevents.DatabaseChangeEvent):
            current_submission.database_change(event)
            
        elif isinstance(event, logevents.DrawingProblemEvent):
#             if should_start_new_sub:
#                 current_submission = Submission()
#                 submissions.append(current_submission)
#             should_start_new_sub = True
            current_submission.drawing_problem(event)
                
        elif isinstance(event, logevents.ClientRespondingEvent):
            current_submission.client_response(event)
        
        elif isinstance(event, logevents.PreProcessEvent):
            current_submission.pre_process(event)
            
        elif isinstance(event, logevents.PostProcessEvent):
            current_submission.post_process(event)
            submissions.append(current_submission)
            current_submission = Submission()
            
        elif isinstance(event, logevents.StudentModelMeasureEvent):
            current_submission.model_measure(event)
        
        elif isinstance(event, logevents.SessionEndEvent):
            current_submission.session_end(event)
    
    return submissions
        