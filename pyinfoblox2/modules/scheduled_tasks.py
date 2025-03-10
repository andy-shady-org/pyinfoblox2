# coding: utf-8

import datetime
import logging
from typing import List

from .base import IPHelpers, BaseList
from ..errors import InfobloxClientError, InfobloxError, InfobloxDataError


class ScheduledTask(IPHelpers):
    """
    Abstraction class that simplifies and unifies all access to Infoblox ScheduledTask objects.
    """
    FIELDS = 'task_id,task_type,approval_status,execution_status,changed_objects,scheduled_time,submit_time,submitter'
    RECORD_TYPE = 'scheduledtask'

    def __init__(self, client, task_id=None, **kwargs):
        super(ScheduledTask, self).__init__(client)
        self.task_id = task_id
        self.task_type = None
        self.data = kwargs
        self.approval_status = None
        self.exec_status = None
        self.changed_objects = dict()
        self.scheduled_time = None
        self.submit_time = None
        self.submitter = None
        self.object_name = None
        self.logger.debug('ScheduledTask Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def to_json(self, original_format=False):
        """
        Returns class items as dict structure

        :param original_format: keep original formal
        :type original_format: bool
        :return: class as dict structure
        :rtype: dict
        """
        if original_format:
            return dict(task_id=self.task_id, task_type=self.task_type, approval_status=self.approval_status, execution_status=self.exec_status,
                        changed_objects=self.changed_objects, scheduled_time=datetime.datetime.fromtimestamp(self.scheduled_time).strftime('%Y-%m-%d %H:%M:%S'),
                        submit_time=datetime.datetime.fromtimestamp(self.submit_time).strftime('%Y-%m-%d %H:%M:%S'), submitter=self.submitter)
        return dict(task_id=self.task_id, task_type=self.task_type, approval_status=self.approval_status, exec_status=self.exec_status,
                    changed_objects=self.changed_objects, scheduled_time=datetime.datetime.fromtimestamp(self.scheduled_time).strftime('%Y-%m-%d %H:%M:%S'),
                    submit_time=datetime.datetime.fromtimestamp(self.submit_time).strftime('%Y-%m-%d %H:%M:%S'), submitter=self.submitter)

    @classmethod
    def load(cls, client, value, callout=True):
        """
        Static method to load a given ScheduledTask either by value of using an existing object

        :param client: pyinfoblox client class
        :param value: a valid task id or ScheduledTask class, or a valid dict of params
        :param callout: Call out to WAPI to retrieve data, default=True
        :return: ScheduledTask class, fully populated or False if task does not exist
        """
        if value and isinstance(value, int):
            return cls.load_by_id(client, value)
        return super(cls, cls).load(client, value, callout)

    @classmethod
    def load_by_id(cls, client, task_id):
        """
        Static method to load a given task as a ScheduledTask object and return it for use

        :param client: pyinfoblox client class
        :param task_id: Infoblox ID for the scheduled task
        :return: ScheduledTask class, fully populated
        """
        c = cls(client, task_id)
        try:
            c.get()
        except (InfobloxError, InfobloxClientError):
            return False
        return c

    def from_json(self, json_data):
        """
        Load direct from JSON data

        :param json_data: dict of parameters
        :return:
        :raises: Exception on error
        :raise: InfobloxError
        """
        if not self.ref:
            if 'ref' in json_data and json_data['ref']:
                try:
                    h = self.load_by_ref(self.client, json_data['ref'])
                    if isinstance(h, ScheduledTask):
                        self.ref = h.ref
                        self.task_type = h.task_type
                        self.approval_status = h.approval_status
                        self.exec_status = h.exec_status
                        self.changed_objects = h.changed_objects
                        self.scheduled_time = h.scheduled_time
                        self.submit_time = h.submit_time
                        self.submitter = h.submitter
                        self.loaded = True
                except InfobloxError:
                    raise
            elif 'task_id' in json_data and json_data.get('task_id', 0):
                try:
                    self.task_id = int(json_data.get('task_id', 0))
                except (ValueError, TypeError):
                    raise InfobloxDataError(self.__class__.__name__, 'ScheduledTask "task_id" is invalid type', 400)
                try:
                    self.get()
                except InfobloxError:
                    return False
            else:
                if not self.ref:
                    raise InfobloxDataError(self.__class__.__name__, 'ScheduledTask "task_id" attribute missing in data structure', 400)

    def get(self):
        """
        Checks Infoblox for the ScheduledTask record

        :return: Infoblox ScheduledTask record in dict if exists else False
        :rtype: dict|bool
        :raises: Exception on error
        :raise: InfobloxError
        """

        if self.task_id and self.task_id is not None:
            fields = f'?_return_fields={self.FIELDS}&_return_as_object=1&task_id={self.task_id}'
        elif self.object_name and self.object_name is not None:
            fields = f'?_return_fields={self.FIELDS}&_return_as_object=1&changed_objects.name={self.object_name}'
        else:
            raise InfobloxDataError(self.__class__.__name__, 'task_id/object_name', 400)

        self.response = self.client.get(f'{self.RECORD_TYPE}{fields}')
        self.parse_reply()

    def parse_reply(self):
        result = self.parse_response(self.response)
        if isinstance(result, dict):
            if '_ref' in result:
                self.logger.debug('Record found, now setting details...')
                self.task_type = result.get('task_type', '')
                self.approval_status = result.get('approval_status', '')
                self.exec_status = result.get('execution_status', '')
                self.changed_objects = result.get('changed_objects', '')
                self.scheduled_time = result.get('scheduled_time', '')
                self.submit_time = result.get('submit_time', '')
                self.submitter = result.get('submitter', '')
                self.ref = result.get('_ref')
            else:
                self.logger.error('reference not returned by item addition or update: %s' % self.response)
                raise InfobloxError(self.__class__.__name__, 'reference not returned by item addition or update: %s' % self.response)
        elif isinstance(result, str):
            self.ref = result
        else:
            self.logger.error('invalid data type, not dict or string: %s' % self.response)
            raise InfobloxError(self.__class__.__name__, 'invalid data type, not dict or string: %s' % self.response)
        self.loaded = True

    def execute_now(self):
        if not self.ref:
            raise InfobloxDataError(self.__class__.__name__, 'ScheduledTask "ref" attribute is not set, please get the task first', 400)
        payload = {"execute_now": True}
        self.response = self.client.put(self.ref, payload=payload)
        self.ref = self.parse_response(self.response)

    def match(self, task_id):
        return task_id == self.task_id

    def __str__(self):
        return str(self.task_id)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.task_id == other.task_id:
            return True
        return False


class ScheduledTasks(BaseList):
    """
    Abstraction class that should be used when dealing with lists of Infoblox ScheduledTasks objects.
    """
    CHILD = ScheduledTask
    RECORD_TYPE = 'scheduledtask'

    def __init__(self, client, **kwargs):
        super(ScheduledTasks, self).__init__(client, **kwargs)
        self.items = list()  # type: List[ScheduledTask]
        self.logger.debug('ScheduledTasks Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    @classmethod
    def search_by_id(cls, client, value, limit=100, paging=0):
        return cls.search(client, 'task_id', value, limit=limit, paging=paging)

    @classmethod
    def search_by_name(cls, client, value, limit=100, paging=0):
        return cls.search(client, 'changed_objects.name', value, limit=limit, paging=paging)

    @classmethod
    def search_by_type(cls, client, value, limit=100, paging=0):
        """
        Search scheduled tasks by object type, e.g. record:cname
        """
        return cls.search(client, 'changed_objects.object_type', value, limit=limit, paging=paging)

    def __getitem__(self, item):
        super().__getitem__(item)

        for x in self.items:
            if isinstance(item, self.CHILD):
                if x.match(item.task_id):
                    return x
            elif isinstance(item, str):
                if x.match(item):
                    return x
            elif isinstance(item, int):
                return self.items[item]
        raise IndexError(f'{self.CHILD.__name__} Not found')

    def __contains__(self, item):
        result = [x.task_id for x in self.items]
        return result.__contains__(item)
