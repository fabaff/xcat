# I work out *how* to inject payloads into requests
import asyncio

import logging
from .injectors import IntegerInjection, StringInjection, AttributeNameInjection, \
    FunctionCallInjection, ElementNameInjection
from xcat import features

logger = logging.getLogger("xcat.detector")


class DetectionException(Exception):
    pass


class Detector(object):
    def __init__(self, checker, requestmaker):
        self.checker = checker
        self.requests = requestmaker

    def change_parameter(self, target_parameter):
        """
        :param target_parameter: A parameter name that the returned detector targets
        :return: A Detector that targets the given URI parameter
        """
        self.requests.set_target_parameter(target_parameter)

    def get_requester(self, injector, features=None):
        requester = self.requests.with_injector(injector)
        if features is not None:
            requester.add_features(features)
        return requester

    @asyncio.coroutine
    def detect_features(self, injector):

        req = self.get_requester(injector)
        x = {
            f.__class__: f
            for f in (yield from features.get_available_features(req))
        }
        return x

    @asyncio.coroutine
    def detect_injectors(self, unstable=False, use_or=False):
        """
        Work out how to send a request
        """
        # Run through all our Injection classes and test them
        injectors = []

        for cls in (IntegerInjection,
                    StringInjection,
                    AttributeNameInjection,
                    ElementNameInjection,
                    FunctionCallInjection):
            inst = cls(self, use_or=use_or)
            if (yield from inst.test(unstable)):
                injectors.append(inst)

        return injectors

    def detect_url_stable(self, data, request_count=5, expected_result=True):
        """
        See if this data is stable (requests return the same code) n times
        """
        logger.info("Testing if URL is stable with %s requests, expecting %s response", request_count, expected_result)

        gathered_results = yield from asyncio.wait([self.requests.send_request(data) for _ in range(request_count)])
        results = [r.result() == expected_result for r in gathered_results[0]]
        if all(results):
            logger.info("URL is stable")
            return True
        else:
            if any(results):
                logger.info("URL is not stable. Responses: {}", results)
            return False
