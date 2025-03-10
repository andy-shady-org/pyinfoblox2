# coding: utf-8

class IPError(Exception):
    """
    Exception class raised from IPHelpers class methods. Used as a single catch-all error for any possible
    error that is raised.
    """
    pass


class InfobloxError(Exception):
    """
    Exception class raised from Infoblox Object class methods. Used as a single catch-all error for any possible
    error that might happen during within any of the object classes used.
    """
    def __init__(self, obj_name, arg_name):
        self.obj_name = obj_name
        self.arg_name = arg_name

    def exc_message(self):
        r = '"{0}" failed.'.format(self.obj_name)
        if ' ' not in self.arg_name:
            r += ' Value "{0}" is not valid.'.format(self.arg_name)
        else:
            r += ' Error: ' + str(self.arg_name)
        return r

    def __str__(self):
        return self.exc_message()


class InfobloxDataError(Exception):
    """
    Exception class raised from Infoblox Object class methods where some form of data validation fails.
    """

    def __init__(self, obj_name, arg_name, return_status):
        self.obj_name = obj_name
        self.arg_name = arg_name
        self.status_code = return_status

    def exc_message(self):
        r = '"{0}" failed.'.format(self.obj_name)
        if ' ' not in self.arg_name:
            r += ' Value "{0}" is not valid.'.format(self.arg_name)
        else:
            r += ' Error: ' + str(self.arg_name)
        return r

    def __str__(self):
        return self.exc_message()


class InfobloxClientError(Exception):
    """
    Exception class raised from InfobloxClient class methods. Used as a single catch-all error for any possible
    error that might happen during communication with Infoblox server to simplify caller coding.
    """
    def __init__(self, obj_name, status_code, error_msg):
        self.obj_name = obj_name
        self.status_code = status_code
        self.error_msg = error_msg

    def exc_message(self):
        return 'HTTP call within object "{0}" failed. Status code is "{1}". Error message is: "{2}".'.format(
            self.obj_name, self.status_code, self.error_msg)

    def __str__(self):
        return self.exc_message()
