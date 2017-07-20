"""Filler."""

from __future__ import absolute_import, division, print_function

import sys
import datetime
import progressbar
import dateutil.parser as dparser

from abc import ABCMeta, abstractmethod

from scripts.parser_library.utils import pretty_json


class Viewer:
    """The frontend to a tracker object."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def receive(self, tracker, broadcast_type):
        """Incremental updates of tracking info.

        Args:
            tracker (scripts.parser_library.tracker.Tracker): Instance of tracker.
            broadcast_type (str): Broadcast type emitted by tracker.
        """

    @abstractmethod
    def report(self, tracker):
        """Report all tracked info.

        Args:
            tracker (scripts.parser_library.tracker.Tracker): Instance of tracker.
        """


class ProgressBar(Viewer):
    """Command line progress bar viewer for parsers."""

    TERMINAL_WIDTH_SWITCH_SIZE = 100

    def __init__(self, school, formatter=(lambda x: x)):
        self.statuses = StatView()

        # Set progress bar to long or short dependent on terminal width
        terminal_width = ProgressBar._get_terminal_size()
        if terminal_width < ProgressBar.TERMINAL_WIDTH_SWITCH_SIZE:
            self.bar = progressbar.ProgressBar(
                redirect_stdout=True,
                max_value=progressbar.UnknownLength,
                widgets=[
                    ' (', school, ') ',
                    progressbar.FormatLabel('%(value)s')
                ])
        else:
            self.bar = progressbar.ProgressBar(
                redirect_stdout=True,
                max_value=progressbar.UnknownLength,
                widgets=[
                    ' (', school, ')',
                    ' [', progressbar.Timer(), '] ',
                    progressbar.FormatLabel('%(value)s')
                ])
        self.formatter = formatter

    @staticmethod
    def _get_terminal_size():
        return progressbar.utils.get_terminal_size()[0]

    def receive(self, tracker, broadcast_type):
        self.statuses.receive(tracker, broadcast_type)
        counters = self.statuses.stats
        mode = '=={}=='.format(tracker.mode.upper())
        count_string = ' | '.join(('{}: {}'.format(k[:3].title(), self.formatter(counters[k])) for k in counters if counters[k]['total'] > 0))
        formatted_string = mode
        if ProgressBar._get_terminal_size() > ProgressBar.TERMINAL_WIDTH_SWITCH_SIZE:
            attrs = ['year', 'term', 'department']
            for attr in attrs:
                if not hasattr(tracker, attr):
                    continue
                if attr == 'department':
                    if 'code' in tracker.department:
                        formatted_string += ' | {}'.format(tracker.department['code'])
                    formatted_string += ' | {}'.format(tracker.department['name'])
                    continue
                formatted_string += ' | {}'.format(getattr(tracker, attr))
        formatted_string += ' | {}'.format(count_string)
        self.bar.update(formatted_string)

    def report(self, tracker):
        """Do nothing."""


class LogFormatted(Viewer):
    def __init__(self, logpath):
        self.logpath = logpath
        self.statuses = StatView()

    def receive(self, tracker, broadcast_type):
        self.statuses.receive(tracker, broadcast_type)

    # TODO - report in valid json format
    def report(self, tracker):
        with open(self.logpath, 'a') as log:
            print('=' * 40, file=log)
            print('{}'.format(tracker.school.upper()), file=log)
            print('=={}=='.format(tracker.mode.upper()), file=log)
            if tracker.saw_error:
                print('FAILED:\n\n{}'.format(tracker.error), file=log)
            print('TIMESTAMP (UTC): {}'.format(tracker.timestamp), file=log)
            print('ELAPSED: {}'.format(str(datetime.timedelta(seconds=int(tracker.end_time - tracker.start_time)))), file=log)
            if hasattr(tracker, 'cmd_options'):
                print('COMMAND OPTIONS:\n{}'.format(pretty_json(tracker.cmd_options)), file=log)
            statistics = {
                subject: {
                    stat: value for stat, value in stats.items() if value != 0
                } for subject, stats in self.statuses.stats.items() if len(stats) > 0
            }
            print('STATS:\n{}'.format(pretty_json(statistics)), file=log)
            if hasattr(tracker, 'granularity'):
                print('calculated granularity: {}'.format(tracker.granularity), file=log)


class StatView(Viewer):
    # TODO - move to central location w/Validator/schema kinds
    KINDS = [
        'course',
        'section',
        'meeting',
        'textbook',
        'evaluation',
        'offering',
        'textbook_link',
        'eval',
    ]

    STATUSES = ['valid', 'created', 'new', 'updated', 'total']

    report = None

    def __init__(self):
        self.stats = {
            subject: {
                stat: 0 for stat in StatView.STATUSES
            } for subject in StatView.KINDS
        }

    def __iter__(self):
        return iter(self.stats)

    def __getitem__(self, key):
        return self.stats[key]

    def receive(self, tracker, broadcast_type):
        if broadcast_type != 'STATUS':
            return
        self.increment(tracker.status['kind'], tracker.status['status'])

    def increment(self, kind, status):
        self.stats[kind][status] += 1

    def clear(self):
        for subject in self.counts:
            for stat in subject:
                subject[stat] = 0


class TimeDistributionView(Viewer):

    def __init__(self):
        self.distribution = {
            12: 0,
            24: 0
        }

        self.granularity = 60

    def receive(self, tracker, broadcast_type):
        if broadcast_type != 'TIME':
            return

        time = getattr(tracker, broadcast_type.lower())
        dparser.parse(time)

        # TODO - analyze distribution and track granularity

        # if hour > 12:
        #     self.time_distribution['_24'] += 1
        # else:
        #     self.time_distribution['_12'] += 1

        # grains = [60, 30, 20, 15, 10, 5, 3, 2, 1]
        # for grain in grains:
        #     if minute % grain == 0:
        #         if grain < self.granularity:
        #             self.granularity = grain
        #         break

    def report(self, tracker):
        """Do nothing."""
