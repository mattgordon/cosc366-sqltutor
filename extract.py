#!/usr/bin/env python3

from logevents import parse_event, UnknownEvent
from submission import events_to_submissions
from features import build_features, CumulativeStatisticsFeatureBase, \
    should_skip_subm, ProblemsAttemptedCumulative
from arffwriter import ArffWriter, ArffAttribute, ArffDataComment
import re
from datetime import datetime
import os
import sys

MAX_SUFFIX = "_max"
MIN_SUFFIX = "_min"
MEAN_SUFFIX = "_mean"
STDEV_SUFFIX = "_stdev"

class LogFileData():
    def __init__(self, filename, features, classifications):
        self.filename = filename
        self.classifications = classifications
        self.features = features


def timestamp_extract(line):
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

def extract_data(in_file):
    """Extract a set of log files into a set of log events"""
    events = []
    no_timestamp_lines = []
    no_timestamps = 0
    print(in_file)
    with open(in_file) as f:
        for log_line in f:
            try:
                # trying to extract the timestamp
                # the presence of a timestamp delimits a new log event
                timestamp, log_line = timestamp_extract(log_line)
                events.append(parse_event(timestamp, log_line, f))
            except ValueError:
                # we don't have a timestamp! oh no!
                no_timestamps += 1
                no_timestamp_lines.append(log_line)
    #print("Found {0} lines with no timestamp".format(no_timestamps))
    unknown_events = filter(lambda x: isinstance(x, UnknownEvent), events)
    #print("Found {0} unknown log events".format(len(list(unknown_events))))
    subms = events_to_submissions(events)
    problems = set()
    features = build_features(subms)

    problems_feature = next(f for f in features 
        if isinstance(f, ProblemsAttemptedCumulative))
    indices_to_delete = []
    for i in range(len(features[0].values)):
        if problems_feature.values[i] < 2:
            indices_to_delete.append(i)
    indices_to_delete.reverse()
    for i in indices_to_delete:
        for feature in features:
            del feature.values[i]
            if isinstance(feature, CumulativeStatisticsFeatureBase):
                del feature.max_values[i]
                del feature.min_values[i]
                del feature.mean_values[i]
                del feature.stdev_values[i]
    abandon_state = classify_problems(subms)
    return LogFileData(in_file, features, abandon_state)

def build_arff(file_data):
    attributes = []
    for feature in file_data.features:
        if isinstance(feature, CumulativeStatisticsFeatureBase):
            attributes.append(
                ArffAttribute(
                    feature.name + MAX_SUFFIX,
                    feature.type,
                    feature.max_values
                )
            )
            attributes.append(
                ArffAttribute(
                    feature.name + MIN_SUFFIX,
                    feature.type,
                    feature.min_values
                )
            )
            attributes.append(
                ArffAttribute(
                    feature.name + MEAN_SUFFIX,
                    feature.type,
                    feature.mean_values
                )
            )
            attributes.append(
                ArffAttribute(
                    feature.name + STDEV_SUFFIX,
                    feature.type,
                    feature.stdev_values
                )
            )
            if feature.use_values():
                attributes.append(
                    ArffAttribute(
                        feature.name,
                        feature.type,
                        feature.values
                    )
                )
        else:
            attributes.append(
                ArffAttribute(
                    feature.name,
                    feature.type,
                    feature.values
                )
            )
    attributes.append(
        ArffAttribute(
            "Class",
            "{abandoned, not_abandoned}",
            file_data.classifications
        )
    )
    return attributes
    
def classify_problems(subms):
    result = []
    for i in range(len(subms)):
        if should_skip_subm(subms[i]):
            continue
        outcome = None
        if subms[i].solved:
            outcome = 'not_abandoned'
        elif len(subms) <= i+1:
            outcome = 'abandoned'
        elif subms[i].problem_id == subms[i+1].problem_id:
            if should_skip_subm(subms[i+1]):
                outcome = 'abandoned'
            else:
                outcome = 'not_abandoned'
        else:
            outcome = 'abandoned'
        result.append(outcome)
    return result

def main(dir_path, out_name):
    files = filter(
        lambda f: f.is_file() and f.name.endswith('.log'), 
        os.scandir(dir_path)
    )
    file_data = []
    for file in files:
        try:
            file_data.append(extract_data(file.path))
        except UnicodeDecodeError:
            print("Couldn't decode file in utf-8: " + file.path)
    arff_attrs = []
    arff_comments = []
    instances = 0
    for file_point in file_data:
        arff_comments.append(ArffDataComment(instances, file_point.filename))
        file_attrs = build_arff(file_point)
        instances += len(file_attrs[0].values)
        if len(arff_attrs) == 0:    
            arff_attrs = file_attrs
        else:
            for arff_attr, file_attr in zip(arff_attrs, file_attrs):
                assert type(arff_attr) == type(file_attr)
                assert arff_attr.name == file_attr.name
                arff_attr.values += file_attr.values
    writer = ArffWriter(out_name + '.arff', 'features')
    writer.attributes = arff_attrs
    writer.comments = arff_comments
    writer.write()
    

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])