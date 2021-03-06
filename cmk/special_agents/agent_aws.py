#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""
Special agent for monitoring Amazon web services (AWS) with Check_MK.
"""

import abc
import argparse
import datetime
import json
import logging
import sys
import time
import errno
from typing import (  # pylint: disable=unused-import
    Union, NamedTuple, Any, List,
)
from pathlib2 import Path
import boto3  # type: ignore
import botocore  # type: ignore
from cmk.utils.paths import tmp_dir
import cmk.utils.store as store
import cmk.utils.password_store

AWSStrings = Union[bytes, unicode]

# TODO
# Rewrite API calls from low-level client to high-level resource:
# Boto3 has two distinct levels of APIs. Client (or "low-level") APIs provide
# one-to-one mappings to the underlying HTTP API operations. Resource APIs hide
# explicit network calls but instead provide resource objects and collections to
# access attributes and perform actions.

# Note that in this case you do not have to make a second API call to get the
# objects; they're available to you as a collection on the bucket. These
# collections of subresources are lazily-loaded.

# TODO limits
# - per account (S3)
# - per region (EC2, EBS, ELB, RDS)

#   .--for imports---------------------------------------------------------.
#   |         __              _                            _               |
#   |        / _| ___  _ __  (_)_ __ ___  _ __   ___  _ __| |_ ___         |
#   |       | |_ / _ \| '__| | | '_ ` _ \| '_ \ / _ \| '__| __/ __|        |
#   |       |  _| (_) | |    | | | | | | | |_) | (_) | |  | |_\__ \        |
#   |       |_|  \___/|_|    |_|_| |_| |_| .__/ \___/|_|   \__|___/        |
#   |                                    |_|                               |
#   '----------------------------------------------------------------------'

#   .--regions--------------------------------------------------------------

AWSRegions = [
    ("ap-south-1", "Asia Pacific (Mumbai)"),
    ("ap-northeast-3", "Asia Pacific (Osaka-Local)"),
    ("ap-northeast-2", "Asia Pacific (Seoul)"),
    ("ap-southeast-1", "Asia Pacific (Singapore)"),
    ("ap-southeast-2", "Asia Pacific (Sydney)"),
    ("ap-northeast-1", "Asia Pacific (Tokyo)"),
    ("ca-central-1", "Canada (Central)"),
    ("cn-north-1", "China (Beijing)"),
    ("cn-northwest-1", "China (Ningxia)"),
    ("eu-central-1", "EU (Frankfurt)"),
    ("eu-west-1", "EU (Ireland)"),
    ("eu-west-2", "EU (London)"),
    ("eu-west-3", "EU (Paris)"),
    ("eu-north-1", "EU (Stockholm)"),
    ("sa-east-1", "South America (Sao Paulo)"),
    ("us-east-2", "US East (Ohio)"),
    ("us-east-1", "US East (N. Virginia)"),
    ("us-west-1", "US West (N. California)"),
    ("us-west-2", "US West (Oregon)"),
]

#.
#   .--EC2 instance types---------------------------------------------------

AWSEC2InstGeneralTypes = [
    'a1.2xlarge',
    'a1.4xlarge',
    'a1.large',
    'a1.medium',
    'a1.xlarge',
    't2.nano',
    't2.micro',
    't2.small',
    't2.medium',
    't2.large',
    't2.xlarge',
    't2.2xlarge',
    't3.nano',
    't3.micro',
    't3.small',
    't3.medium',
    't3.large',
    't3.xlarge',
    't3.2xlarge',
    'm3.medium',
    'm3.large',
    'm3.xlarge',
    'm3.2xlarge',
    'm4.large',
    'm4.xlarge',
    'm4.2xlarge',
    'm4.4xlarge',
    'm4.10xlarge',
    'm4.16xlarge',
    'm5.12xlarge',
    'm5.24xlarge',
    'm5.2xlarge',
    'm5.4xlarge',
    'm5.large',
    'm5.xlarge',
    'm5d.12xlarge',
    'm5d.24xlarge',
    'm5d.2xlarge',
    'm5d.4xlarge',
    'm5d.large',
    'm5d.xlarge',
    'm5a.12xlarge',
    'm5a.24xlarge',
    'm5a.2xlarge',
    'm5a.4xlarge',
    'm5a.large',
    'm5a.xlarge',
]

AWSEC2InstPrevGeneralTypes = [
    't1.micro',
    'm1.small',
    'm1.medium',
    'm1.large',
    'm1.xlarge',
]

AWSEC2InstMemoryTypes = [
    'r3.2xlarge',
    'r3.4xlarge',
    'r3.8xlarge',
    'r3.large',
    'r3.xlarge',
    'r4.2xlarge',
    'r4.4xlarge',
    'r4.8xlarge',
    'r4.16xlarge',
    'r4.large',
    'r4.xlarge',
    'r5.2xlarge',
    'r5.4xlarge',
    'r5.8xlarge',
    'r5.12xlarge',
    'r5.16xlarge',
    'r5.24xlarge',
    'r5.large',
    'r5.metal',
    'r5.xlarge',
    'r5a.12xlarge',
    'r5a.24xlarge',
    'r5a.2xlarge',
    'r5a.4xlarge',
    'r5a.large',
    'r5a.xlarge',
    'r5d.2xlarge',
    'r5d.4xlarge',
    'r5d.8xlarge',
    'r5d.12xlarge',
    'r5d.16xlarge',
    'r5d.24xlarge',
    'r5d.large',
    'r5d.metal',
    'r5d.xlarge',
    'x1.16xlarge',
    'x1.32xlarge',
    'x1e.2xlarge',
    'x1e.4xlarge',
    'x1e.8xlarge',
    'x1e.16xlarge',
    'x1e.32xlarge',
    'x1e.xlarge',
    'z1d.2xlarge',
    'z1d.3xlarge',
    'z1d.6xlarge',
    'z1d.12xlarge',
    'z1d.large',
    'z1d.xlarge',
]

AWSEC2InstPrevMemoryTypes = [
    'm2.xlarge',
    'm2.2xlarge',
    'm2.4xlarge',
    'cr1.8xlarge',
]

AWSEC2InstComputeTypes = [
    'c3.large',
    'c3.xlarge',
    'c3.2xlarge',
    'c3.4xlarge',
    'c3.8xlarge',
    'c4.large',
    'c4.xlarge',
    'c4.2xlarge',
    'c4.4xlarge',
    'c4.8xlarge',
    'c5.18xlarge',
    'c5.2xlarge',
    'c5.4xlarge',
    'c5.9xlarge',
    'c5.large',
    'c5.xlarge',
    'c5d.18xlarge',
    'c5d.2xlarge',
    'c5d.4xlarge',
    'c5d.9xlarge',
    'c5d.large',
    'c5d.xlarge',
    'c5n.18xlarge',
    'c5n.2xlarge',
    'c5n.4xlarge',
    'c5n.9xlarge',
    'c5n.large',
    'c5n.xlarge',
]

AWSEC2InstPrevComputeTypes = [
    'c1.medium',
    'c1.xlarge',
    'cc2.8xlarge',
    'cc1.4xlarge',
]

AWSEC2InstAcceleratedComputeTypes = [
    'f1.4xlarge',
    'p2.xlarge',
    'p2.8xlarge',
    'p2.16xlarge',
    'p3.16xlarge',
    'p3.2xlarge',
    'p3.8xlarge',
    'p3dn.24xlarge',
]

AWSEC2InstStorageTypes = [
    'i2.xlarge',
    'i2.2xlarge',
    'i2.4xlarge',
    'i2.8xlarge',
    'i3.large',
    'i3.xlarge',
    'i3.2xlarge',
    'i3.4xlarge',
    'i3.8xlarge',
    'i3.16xlarge',
    'i3.metal',
    'h1.16xlarge',
    'h1.2xlarge',
    'h1.4xlarge',
    'h1.8xlarge',
]

# 'hi1.4xlarge' is no longer in the instance type listings,
# but some accounts might still have a limit for it
AWSEC2InstPrevStorageTypes = [
    'hi1.4xlarge',
    'hs1.8xlarge',
]

AWSEC2InstDenseStorageTypes = [
    'd2.xlarge',
    'd2.2xlarge',
    'd2.4xlarge',
    'd2.8xlarge',
]

AWSEC2InstGPUTypes = [
    'g2.2xlarge',
    'g2.8xlarge',
    'g3.16xlarge',
    'g3.4xlarge',
    'g3.8xlarge',
    'g3s.xlarge',
]

AWSEC2InstPrevGPUTypes = [
    'cg1.4xlarge',
]

# note, as of 2016-12-17, these are still in Developer Preview;
# there isn't a published instance limit yet, so we'll assume
# it's the default...
AWSEC2InstFPGATypes = [
    'f1.2xlarge',
    'f1.16xlarge',
]

AWSEC2InstTypes = (
    AWSEC2InstGeneralTypes + AWSEC2InstPrevGeneralTypes + AWSEC2InstMemoryTypes +
    AWSEC2InstPrevMemoryTypes + AWSEC2InstComputeTypes + AWSEC2InstPrevComputeTypes +
    AWSEC2InstAcceleratedComputeTypes + AWSEC2InstStorageTypes + AWSEC2InstPrevStorageTypes +
    AWSEC2InstDenseStorageTypes + AWSEC2InstGPUTypes + AWSEC2InstPrevGPUTypes + AWSEC2InstFPGATypes)

# (On-Demand, Reserved, Spot)

AWSEC2LimitsDefault = (20, 20, 5)

AWSEC2LimitsSpecial = {
    'c4.4xlarge': (10, 20, 5),
    'c4.8xlarge': (5, 20, 5),
    'c5.4xlarge': (10, 20, 5),
    'c5.9xlarge': (5, 20, 5),
    'c5.18xlarge': (5, 20, 5),
    'cg1.4xlarge': (2, 20, 5),
    'cr1.8xlarge': (2, 20, 5),
    'd2.4xlarge': (10, 20, 5),
    'd2.8xlarge': (5, 20, 5),
    'g2.2xlarge': (5, 20, 5),
    'g2.8xlarge': (2, 20, 5),
    'g3.4xlarge': (1, 20, 5),
    'g3.8xlarge': (1, 20, 5),
    'g3.16xlarge': (1, 20, 5),
    'h1.8xlarge': (10, 20, 5),
    'h1.16xlarge': (5, 20, 5),
    'hi1.4xlarge': (2, 20, 5),
    'hs1.8xlarge': (2, 20, 0),
    'i2.2xlarge': (8, 20, 0),
    'i2.4xlarge': (4, 20, 0),
    'i2.8xlarge': (2, 20, 0),
    'i2.xlarge': (8, 20, 0),
    'i3.2xlarge': (2, 20, 0),
    'i3.4xlarge': (2, 20, 0),
    'i3.8xlarge': (2, 20, 0),
    'i3.16xlarge': (2, 20, 0),
    'i3.large': (2, 20, 0),
    'i3.xlarge': (2, 20, 0),
    'm4.4xlarge': (10, 20, 5),
    'm4.10xlarge': (5, 20, 5),
    'm4.16xlarge': (5, 20, 5),
    'm5.4xlarge': (10, 20, 5),
    'm5.12xlarge': (5, 20, 5),
    'm5.24xlarge': (5, 20, 5),
    'p2.8xlarge': (1, 20, 5),
    'p2.16xlarge': (1, 20, 5),
    'p2.xlarge': (1, 20, 5),
    'p3.2xlarge': (1, 20, 5),
    'p3.8xlarge': (1, 20, 5),
    'p3.16xlarge': (1, 20, 5),
    'p3dn.24xlarge': (1, 20, 5),
    'r3.4xlarge': (10, 20, 5),
    'r3.8xlarge': (5, 20, 5),
    'r4.4xlarge': (10, 20, 5),
    'r4.8xlarge': (5, 20, 5),
    'r4.16xlarge': (1, 20, 5),
}

#.

#.
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


def _datetime_converter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()


def _chunks(list_, length=100):
    return [list_[i:i + length] for i in xrange(0, len(list_), length)]


def _get_ec2_instance_id(inst, region):
    # PrivateIpAddress and InstanceId is available although the instance is stopped
    return u"%s-%s-%s" % (inst['PrivateIpAddress'], region, inst['InstanceId'])


#.
#   .--section API---------------------------------------------------------.
#   |                       _   _                  _    ____ ___           |
#   |         ___  ___  ___| |_(_) ___  _ __      / \  |  _ \_ _|          |
#   |        / __|/ _ \/ __| __| |/ _ \| '_ \    / _ \ | |_) | |           |
#   |        \__ \  __/ (__| |_| | (_) | | | |  / ___ \|  __/| |           |
#   |        |___/\___|\___|\__|_|\___/|_| |_| /_/   \_\_|  |___|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#   ---result distributor---------------------------------------------------


class ResultDistributor(object):
    """
    Mediator which distributes results from sections
    in order to reduce queries to AWS account.
    """

    def __init__(self):
        self._colleagues = []

    def add(self, colleague):
        self._colleagues.append(colleague)

    def distribute(self, sender, result):
        for colleague in self._colleagues:
            if colleague.name != sender.name:
                colleague.receive(sender, result)


#   ---sections/colleagues--------------------------------------------------

AWSSectionResults = NamedTuple("AWSSectionResults", [
    ("results", List),
    ("cache_timestamp", float),
])

AWSSectionResult = NamedTuple("AWSSectionResult", [
    ("piggyback_hostname", AWSStrings),
    ("content", Any),
])

AWSLimit = NamedTuple("AWSLimit", [
    ("key", AWSStrings),
    ("title", AWSStrings),
    ("limit", int),
    ("amount", int),
])

AWSColleagueContents = NamedTuple("AWSColleagueContents", [
    ("content", Any),
    ("cache_timestamp", float),
])

AWSRawContent = NamedTuple("AWSRawContent", [
    ("content", Any),
    ("cache_timestamp", float),
])

AWSComputedContent = NamedTuple("AWSComputedContent", [
    ("content", Any),
    ("cache_timestamp", float),
])

AWSCacheFilePath = Path(tmp_dir) / "agents" / "agent_aws"


class AWSSection(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, client, region, config, distributor=None):
        self._client = client
        self._region = region
        self._config = config
        self._distributor = ResultDistributor() if distributor is None else distributor
        self._received_results = {}
        self._cache_file_dir = AWSCacheFilePath / self._region / self._config.hostname
        self._cache_file = AWSCacheFilePath / self._region / self._config.hostname / self.name

    @abc.abstractproperty
    def name(self):
        pass

    @abc.abstractproperty
    def interval(self):
        """
        In general the default resolution of AWS metrics is 5 min (300 sec)
        The default resolution of AWS S3 metrics is 1 day (86400 sec)
        We use interval property for cached section.
        """
        pass

    @property
    def period(self):
        return 2 * self.interval

    def _send(self, content):
        self._distributor.distribute(self, content)

    def receive(self, sender, content):
        self._received_results.setdefault(sender.name, content)

    def run(self, use_cache=False):
        colleague_contents = self._get_colleague_contents()
        assert isinstance(
            colleague_contents, AWSColleagueContents
        ), "%s: Colleague contents must be of type 'AWSColleagueContents'" % self.name
        assert isinstance(
            colleague_contents.cache_timestamp,
            float), "%s: Cache timestamp of colleague contents must be of type 'float'" % self.name

        raw_content = self._get_raw_content(colleague_contents, use_cache=use_cache)
        assert isinstance(
            raw_content,
            AWSRawContent), "%s: Raw content must be of type 'AWSRawContent'" % self.name
        assert isinstance(
            raw_content.cache_timestamp,
            float), "%s: Cache timestamp of raw content must be of type 'float'" % self.name

        computed_content = self._compute_content(raw_content, colleague_contents)
        assert isinstance(computed_content, AWSComputedContent
                         ), "%s: Computed content must be of type 'AWSComputedContent'" % self.name
        assert isinstance(
            computed_content.cache_timestamp,
            float), "%s: Cache timestamp of computed content must be of type 'float'" % self.name

        self._send(computed_content)
        created_results = self._create_results(computed_content)
        assert isinstance(created_results,
                          list), "%s: Created results must be fo type 'list'" % self.name

        final_results = []
        for result in created_results:
            assert isinstance(
                result,
                AWSSectionResult), "%s: Result must be of type 'AWSSectionResult'" % self.name

            if not result.content:
                logging.info("%s: Result is empty or None", self.name)
                continue

            assert isinstance(
                result.piggyback_hostname, (unicode, str)
            ), "%s: Piggyback hostname of created result must be of type 'unicode' or 'str'" % self.name
            # In the related check plugin aws.include we parse these results and
            # extend list of json-loaded results.
            assert isinstance(result.content,
                              list), "%s: Result content must be of type 'list'" % self.name

            final_results.append(result)
        return AWSSectionResults(final_results, computed_content.cache_timestamp)

    def _get_raw_content(self, colleague_contents, use_cache=False):
        # Cache is only used if the age is lower than section interval AND
        # the collected data from colleagues are not newer
        self._cache_file_dir.mkdir(parents=True, exist_ok=True)
        if use_cache and self._cache_is_recent_enough(colleague_contents):
            raw_content, cache_timestamp = self._read_from_cache()
        else:
            raw_content = self._fetch_raw_content(colleague_contents)
            # TODO: Write cache only when _compute_section_content succeeded?
            if use_cache:
                self._write_to_cache(raw_content)
            cache_timestamp = time.time()
        return AWSRawContent(raw_content, cache_timestamp)

    def _cache_is_recent_enough(self, colleague_contents):
        if not self._cache_file.exists():
            logging.info("New cache file %s", self._cache_file)
            return False

        now = time.time()
        try:
            age = now - self._cache_file.stat().st_mtime
        except OSError as e:
            if e.errno == 2:
                logging.info("No such file or directory %s (calculate age)", self._cache_file)
                return False
            else:
                logging.info("Cannot calculate cache file age: %s", e)
                raise

        if age >= self.interval:
            logging.info("Cache file %s is outdated", self._cache_file)
            return False

        if colleague_contents.cache_timestamp > now:
            logging.info("Colleague data is newer than cache file %s", self._cache_file)
            return False
        return True

    def _read_from_cache(self):
        try:
            with self._cache_file.open(encoding="utf-8") as f:
                raw_content = f.read().strip()
        except IOError as e:
            if e.errno == errno.ENOENT:
                logging.info("No such file or directory %s (read from cache)", self._cache_file)
                return None, 0.0
            else:
                logging.info("Cannot read from cache file: %s", e)
                raise
        try:
            content = json.loads(raw_content)
        except ValueError as e:
            logging.info("Cannot load raw content: %s", e)
            content = None
        return content, self._cache_file.stat().st_mtime

    def _write_to_cache(self, raw_content):
        json_dump = json.dumps(raw_content, default=_datetime_converter)
        store.save_file(str(self._cache_file), json_dump)

    @abc.abstractmethod
    def _get_colleague_contents(self):
        # type: (Any) -> AWSColleagueContents
        """
        Receive section contents from colleagues. The results are stored in
        self._receive_results: {<KEY>: AWSComputedContent}.
        The relation between two sections must be declared in the related
        distributor in advance to make this work.
        Use max. cache_timestamp of all received results for
        AWSColleagueContents.cache_timestamp
        """
        pass

    @abc.abstractmethod
    def _fetch_raw_content(self, colleague_contents):
        """
        Call API methods, eg. 'response = ec2_client.describe_instances()' and
        extract content from raw content.  Raw contents basically consist of
        two sub results:
        - 'ResponseMetadata'
        - '<KEY>'
        Return raw_result['<KEY>'].
        """
        pass

    @abc.abstractmethod
    def _compute_content(self, raw_content, colleague_contents):
        # type: (AWSRawContent, Any) -> AWSComputedContent
        """
        Compute the final content of this section based on the raw content of
        this section and the content received from the optional colleague
        sections.
        """
        pass

    @abc.abstractmethod
    def _create_results(self, computed_content):
        # type: (Any) -> List[AWSSectionResult]
        pass

    def _get_response_content(self, response, key, dflt=None):
        if dflt is None:
            dflt = []
        try:
            return response[key]
        except KeyError:
            logging.info("%s: KeyError; Available keys are %s", self.name, response.keys())
            return dflt

    def _prepare_tags_for_api_response(self, tags):
        """
        We need to change the format, in order to filter out instances with specific
        tags if and only if we already fetched instances, eg. by limits section.
        The format:
        [{'Key': KEY, 'Value': VALUE}, ...]
        """
        if not tags:
            return
        return [{'Key': e['Name'].strip("tag:"), 'Value': v} for e in tags for v in e['Values']]


class AWSSectionLimits(AWSSection):
    __metaclass__ = abc.ABCMeta

    def __init__(self, client, region, config, distributor=None):
        super(AWSSectionLimits, self).__init__(client, region, config, distributor=distributor)
        self._limits = {}

    def _add_limit(self, piggyback_hostname, limit):
        assert isinstance(limit, AWSLimit), "%s: Limit must be of type 'AWSLimit'" % self.name
        self._limits.setdefault(piggyback_hostname, []).append(limit)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, limits)
            for piggyback_hostname, limits in self._limits.iteritems()
        ]


class AWSSectionGeneric(AWSSection):
    __metaclass__ = abc.ABCMeta


class AWSSectionCloudwatch(AWSSection):
    __metaclass__ = abc.ABCMeta

    def _fetch_raw_content(self, colleague_contents):
        end_time = time.time()
        start_time = end_time - self.period
        metrics = self._get_metrics(colleague_contents)
        if not metrics:
            return []

        # A single GetMetricData call can include up to 100 MetricDataQuery structures
        # There's no pagination for this operation:
        # self._client.can_paginate('get_metric_data') = False
        raw_content = []
        for chunk in _chunks(metrics):
            if not chunk:
                continue
            response = self._client.get_metric_data(
                MetricDataQueries=chunk,
                StartTime=start_time,
                EndTime=end_time,
            )

            metrics = self._get_response_content(response, 'MetricDataResults')
            if not metrics:
                continue
            raw_content.extend(metrics)
        return raw_content

    @abc.abstractmethod
    def _get_metrics(self, colleague_contents):
        pass

    def _create_id_for_metric_data_query(self, index, metric_name, *args):
        """
        ID field must be unique in a single call.
        The valid characters are letters, numbers, and underscore.
        The first character must be a lowercase letter.
        Regex: ^[a-z][a-zA-Z0-9_]*$
        """
        return "_".join(["id", str(index)] + list(args) + [metric_name])


#.
#   .--costs/usage---------------------------------------------------------.
#   |                      _          __                                   |
#   |         ___ ___  ___| |_ ___   / /   _ ___  __ _  __ _  ___          |
#   |        / __/ _ \/ __| __/ __| / / | | / __|/ _` |/ _` |/ _ \         |
#   |       | (_| (_) \__ \ |_\__ \/ /| |_| \__ \ (_| | (_| |  __/         |
#   |        \___\___/|___/\__|___/_/  \__,_|___/\__,_|\__, |\___|         |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'

# Interval between 'Start' and 'End' must be a DateInterval. 'End' is exclusive.
# Example:
# 2017-01-01 - 2017-05-01; cost and usage data is retrieved from 2017-01-01 up
# to and including 2017-04-30 but not including 2017-05-01.
# The GetCostAndUsageRequest operation supports only DAILY and MONTHLY granularities.


class CostsAndUsage(AWSSectionGeneric):
    @property
    def name(self):
        return "costs_and_usage"

    @property
    def interval(self):
        return 86400

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def _fetch_raw_content(self, colleague_contents):
        fmt = "%Y-%m-%d"
        now = time.time()
        response = self._client.get_cost_and_usage(
            TimePeriod={
                'Start': time.strftime(fmt, time.gmtime(now - self.interval)),
                'End': time.strftime(fmt, time.gmtime(now)),
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[{
                'Type': 'DIMENSION',
                'Key': 'LINKED_ACCOUNT'
            }, {
                'Type': 'DIMENSION',
                'Key': 'SERVICE'
            }],
        )
        return self._get_response_content(response, 'ResultsByTime')

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


#.
#   .--EC2-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____/ ___|___ \                            |
#   |                         |  _|| |     __) |                           |
#   |                         | |__| |___ / __/                            |
#   |                         |_____\____|_____|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class EC2Limits(AWSSectionLimits):
    @property
    def name(self):
        return "ec2_limits"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def _fetch_raw_content(self, colleague_contents):
        response = self._client.describe_instances()
        reservations = self._get_response_content(response, 'Reservations')

        response = self._client.describe_reserved_instances()
        reserved_instances = self._get_response_content(response, 'ReservedInstances')

        response = self._client.describe_addresses()
        addresses = self._get_response_content(response, 'Addresses')

        response = self._client.describe_security_groups()
        security_groups = self._get_response_content(response, 'SecurityGroups')

        response = self._client.describe_network_interfaces()
        interfaces = self._get_response_content(response, 'NetworkInterfaces')

        response = self._client.describe_spot_instance_requests()
        spot_inst_requests = self._get_response_content(response, 'SpotInstanceRequests')

        response = self._client.describe_spot_fleet_requests()
        spot_fleet_requests = self._get_response_content(response, 'SpotFleetRequestConfigs')

        return reservations, reserved_instances, addresses, security_groups, interfaces, spot_inst_requests, spot_fleet_requests

    def _compute_content(self, raw_content, colleague_contents):
        reservations, reserved_instances, addresses, security_groups, interfaces, spot_inst_requests, spot_fleet_requests = raw_content.content
        instances = {inst['InstanceId']: inst for res in reservations for inst in res['Instances']}
        res_instances = {inst['ReservedInstanceId']: inst for inst in reserved_instances}

        self._add_instance_limits(instances, res_instances, spot_inst_requests)
        self._add_addresses_limits(addresses)
        self._add_security_group_limits(instances, security_groups)
        self._add_interface_limits(instances, interfaces)
        self._add_spot_inst_limits(spot_inst_requests)
        self._add_spot_fleet_limits(spot_fleet_requests)
        return AWSComputedContent(reservations, raw_content.cache_timestamp)

    def _add_instance_limits(self, instances, res_instances, spot_inst_requests):
        inst_limits = self._get_inst_limits(instances, spot_inst_requests)
        res_limits = self._get_res_inst_limits(res_instances)

        total_ris = 0
        running_ris = 0
        ondemand_limits = {}
        # subtract reservations from instance usage
        for inst_az, inst_types in inst_limits.iteritems():
            if inst_az not in res_limits:
                for inst_type, count in inst_types.iteritems():
                    ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + count
                continue

            # else we have reservations for this AZ
            for inst_type, count in inst_types.iteritems():
                if inst_type not in res_limits[inst_az]:
                    # no reservations for this type
                    ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + count
                    continue

                amount_res_inst_type = res_limits[inst_az][inst_type]
                ondemand = count - amount_res_inst_type
                total_ris += amount_res_inst_type
                if count < amount_res_inst_type:
                    running_ris += count
                else:
                    running_ris += amount_res_inst_type
                if ondemand < 0:
                    # we have unused reservations
                    continue
                ondemand_limits[inst_type] = ondemand_limits.get(inst_type, 0) + ondemand

        dflt_ondemand_limit, _reserved_limit, _spot_limit = AWSEC2LimitsDefault
        total_instances = 0
        for inst_type, count in ondemand_limits.iteritems():
            total_instances += count
            ondemand_limit, _reserved_limit, _spot_limit = AWSEC2LimitsSpecial.get(
                inst_type, AWSEC2LimitsDefault)
            self._add_limit(
                "",
                AWSLimit("running_ondemand_instances_%s" % inst_type,
                         "Running On-Demand %s Instances" % inst_type, ondemand_limit, count))
        self._add_limit(
            "",
            AWSLimit("running_ondemand_instances_total", "Total Running On-Demand Instances",
                     dflt_ondemand_limit, total_instances))

    def _get_inst_limits(self, instances, spot_inst_requests):
        spot_instance_ids = [inst['InstanceId'] for inst in spot_inst_requests]
        inst_limits = {}
        for inst_id, inst in instances.iteritems():
            if inst_id in spot_instance_ids:
                continue
            if inst['State']['Name'] in ['stopped', 'terminated']:
                continue
            inst_type = inst['InstanceType']
            inst_az = inst['Placement']['AvailabilityZone']
            inst_limits.setdefault(
                inst_az, {})[inst_type] = inst_limits.get(inst_az, {}).get(inst_type, 0) + 1
        return inst_limits

    def _get_res_inst_limits(self, res_instances):
        res_limits = {}
        for res_inst in res_instances.itervalues():
            if res_inst['State'] != 'active':
                continue
            inst_type = res_inst['InstanceType']
            if inst_type not in AWSEC2InstTypes:
                logging.info("%s: Unknown instance type '%s'", self.name, inst_type)
                continue

            inst_az = res_inst['AvailabilityZone']
            res_limits.setdefault(inst_az, {})[inst_type] = res_limits.get(inst_az, {}).get(
                inst_type, 0) + res_inst['InstanceCount']
        return res_limits

    def _add_addresses_limits(self, addresses):
        # Global limits
        vpc_addresses = 0
        std_addresses = 0
        for address in addresses:
            domain = address['Domain']
            if domain == "vpc":
                vpc_addresses += 1
            elif domain == "standard":
                std_addresses += 1
        self._add_limit(
            "", AWSLimit("vpc_elastic_ip_addresses", "VPC Elastic IP Addresses", 5, vpc_addresses))
        self._add_limit("",
                        AWSLimit("elastic_ip_addresses", "Elastic IP Addresses", 5, std_addresses))

    def _add_security_group_limits(self, instances, security_groups):
        # Security groups for EC2-Classic per instance
        # Rules per security group for EC2-Classic
        sgs_per_vpc = {}
        for sec_group in security_groups:
            vpc_id = sec_group['VpcId']
            if not vpc_id:
                continue
            inst = self._get_inst_assignment(instances, 'VpcId', vpc_id)
            if inst is None:
                continue
            inst_id = _get_ec2_instance_id(inst, self._region)
            key = (inst_id, vpc_id)
            sgs_per_vpc[key] = sgs_per_vpc.get(key, 0) + 1
            self._add_limit(
                inst_id,
                AWSLimit("vpc_sec_group_rules",
                         "Rules of VPC security group %s" % sec_group['GroupName'], 50,
                         len(sec_group['IpPermissions'])))

        for (inst_id, vpc_id), count in sgs_per_vpc.iteritems():
            self._add_limit(
                inst_id, AWSLimit("vpc_sec_groups", "Security Groups of VPC %s" % vpc_id, 500,
                                  count))

    def _get_inst_assignment(self, instances, key, assignment):
        for inst in instances.itervalues():
            if inst.get(key) == assignment:
                return inst

    def _add_interface_limits(self, instances, interfaces):
        # These limits are per security groups and
        # security groups are per instance
        for iface in interfaces:
            inst = self._get_inst_assignment(instances, 'VpcId', iface.get('VpcId'))
            if inst is None:
                continue
            self._add_limit(
                _get_ec2_instance_id(inst, self._region),
                AWSLimit(
                    "if_vpc_sec_group", "VPC security groups of elastic network interface %s" %
                    iface['NetworkInterfaceId'], 5, len(iface['Groups'])))

    def _add_spot_inst_limits(self, spot_inst_requests):
        count_spot_inst_reqs = 0
        for spot_inst_req in spot_inst_requests:
            if spot_inst_req['State'] in ['open', 'active']:
                count_spot_inst_reqs += 1
        self._add_limit(
            "", AWSLimit('spot_inst_requests', 'Spot Instance Requests', 20, count_spot_inst_reqs))

    def _add_spot_fleet_limits(self, spot_fleet_requests):
        active_spot_fleet_requests = 0
        total_target_cap = 0
        for spot_fleet_req in spot_fleet_requests:
            if spot_fleet_req['State'] != 'active':
                continue

            active_spot_fleet_requests += 1
            total_target_cap += spot_fleet_req['SpotFleetRequestConfig']['TargetCapacity']

        self._add_limit(
            "",
            AWSLimit('active_spot_fleet_requests', 'Active Spot Fleet Requests', 1000,
                     active_spot_fleet_requests))
        self._add_limit(
            "",
            AWSLimit('spot_fleet_total_target_capacity',
                     'Spot Fleet Requests Total Target Capacity', 5000, total_target_cap))


class EC2Summary(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(EC2Summary, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['ec2_names']
        self._tags = self._config.service_config['ec2_tags']

    @property
    def name(self):
        return "ec2_summary"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ec2_limits')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def _fetch_raw_content(self, colleague_contents):
        if self._tags is None and self._names is not None:
            return self._fetch_instances_filtered_by_names(colleague_contents.content)
        if self._tags is not None:
            return self._fetch_instances_filtered_by_tags(colleague_contents.content)
        return self._fetch_instances_without_filter()

    def _fetch_instances_filtered_by_names(self, col_reservations):
        if col_reservations:
            instances = [
                inst for res in col_reservations for inst in res['Instances']
                if inst['InstanceId'] in self._names
            ]
        else:
            response = self._client.describe_instances(InstanceIds=self._names)
            instances = [
                inst for res in self._get_response_content(response, 'Reservations')
                for inst in res['Instances']
            ]
        return instances

    def _fetch_instances_filtered_by_tags(self, col_reservations):
        if col_reservations:
            tags = self._prepare_tags_for_api_response(self._tags)
            instances = [
                inst for res in col_reservations
                for inst in res['Instances'] for tag in inst['Tags'] if tag in tags
            ]
        else:
            response = self._client.describe_instances(Filters=self._tags)
            instances = [
                inst for res in self._get_response_content(response, 'Reservations')
                for inst in res['Instances']
            ]
        return instances

    def _fetch_instances_without_filter(self):
        response = self._client.describe_instances()
        return [
            inst for res in self._get_response_content(response, 'Reservations')
            for inst in res['Instances']
        ]

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(
            self._format_instances(raw_content.content), raw_content.cache_timestamp)

    def _format_instances(self, instances):
        # PrivateIpAddress and InstanceId is available although the instance is stopped
        return {_get_ec2_instance_id(inst, self._region): inst for inst in instances}

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content.values())]


class EC2SecurityGroups(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(EC2SecurityGroups, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['ec2_names']
        self._tags = self._config.service_config['ec2_tags']

    @property
    def name(self):
        return "ec2_security_groups"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ec2_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _fetch_raw_content(self, colleague_contents):
        response = self._describe_security_groups()
        return {
            group['GroupId']: group
            for group in self._get_response_content(response, 'SecurityGroups')
        }

    def _describe_security_groups(self):
        if self._names is not None:
            return self._client.describe_security_groups(InstanceIds=self._names)
        elif self._tags is not None:
            return self._client.describe_security_groups(Filters=self._tags)
        return self._client.describe_security_groups()

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for instance_name, instance in colleague_contents.content.iteritems():
            for security_group_from_instance in instance.get('SecurityGroups', []):
                security_group = raw_content.content.get(security_group_from_instance['GroupId'])
                if security_group is None:
                    continue
                content_by_piggyback_hosts.setdefault(instance_name, []).append(security_group)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


class EC2(AWSSectionCloudwatch):
    @property
    def name(self):
        return "ec2"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ec2_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, (instance_name, instance) in enumerate(colleague_contents.content.iteritems()):
            instance_id = instance['InstanceId']
            for metric_name, unit in [
                ("CPUCreditUsage", "Count"),
                ("CPUCreditBalance", "Count"),
                ("CPUUtilization", "Percent"),
                ("DiskReadOps", "Count"),
                ("DiskWriteOps", "Count"),
                ("DiskReadBytes", "Bytes"),
                ("DiskWriteBytes", "Bytes"),
                ("NetworkIn", "Bytes"),
                ("NetworkOut", "Bytes"),
                ("StatusCheckFailed_Instance", "Count"),
                ("StatusCheckFailed_System", "Count"),
            ]:
                metrics.append({
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': instance_name,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EC2',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "InstanceId",
                                'Value': instance_id,
                            }]
                        },
                        'Period': self.period,
                        'Stat': 'Average',
                        'Unit': unit,
                    },
                })
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row['Label'], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


#.
#   .--S3------------------------------------------------------------------.
#   |                             ____ _____                               |
#   |                            / ___|___ /                               |
#   |                            \___ \ |_ \                               |
#   |                             ___) |__) |                              |
#   |                            |____/____/                               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class S3Limits(AWSSectionLimits):
    @property
    def name(self):
        return "s3_limits"

    @property
    def interval(self):
        return 86400

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def _fetch_raw_content(self, colleague_contents):
        """
        There's no API method for getting account limits thus we have to
        fetch all buckets.
        """
        response = self._client.list_buckets()
        return self._get_response_content(response, 'Buckets')

    def _compute_content(self, raw_content, colleague_contents):
        self._add_limit("", AWSLimit('buckets', 'Buckets', 100, len(raw_content.content)))
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class S3Summary(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(S3Summary, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['s3_names']
        self._tags = self._prepare_tags_for_api_response(self._config.service_config['s3_tags'])

    @property
    def name(self):
        return "s3_summary"

    @property
    def interval(self):
        return 86400

    def _get_colleague_contents(self):
        colleague = self._received_results.get('s3_limits')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def _fetch_raw_content(self, colleague_contents):
        found_buckets = []
        for bucket in self._list_buckets(colleague_contents):
            bucket_name = bucket['Name']

            # We can request buckets globally but if a bucket is located in
            # another region we do not get any results
            response = self._client.get_bucket_location(Bucket=bucket_name)
            location = self._get_response_content(response, 'LocationConstraint', dflt="")
            if location != self._region:
                continue
            bucket['LocationConstraint'] = location

            #TODO
            # Why do we get the following error while calling these methods:
            #_response = self._client.get_public_access_block(Bucket=bucket_name)
            #_response = self._client.get_bucket_policy_status(Bucket=bucket_name)
            # 'S3' object has no attribute 'get_bucket_policy_status'
            try:
                response = self._client.get_bucket_tagging(Bucket=bucket_name)
            except botocore.exceptions.ClientError as e:
                # If there are no tags attached to a bucket we receive a 'ClientError'
                logging.info("%s/%s: No tags set, %s", self.name, bucket_name, e)
                response = {}

            tagging = self._get_response_content(response, 'TagSet')
            if self._matches_tag_conditions(tagging):
                bucket['Tagging'] = tagging
                found_buckets.append(bucket)
        return found_buckets

    def _list_buckets(self, colleague_contents):
        if self._tags is None and self._names is not None:
            if colleague_contents.content:
                return [
                    bucket for bucket in colleague_contents.content if bucket['Name'] in self._names
                ]
            return [{'Name': n} for n in self._names]

        response = self._client.list_buckets()
        return self._get_response_content(response, 'Buckets')

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent({bucket['Name']: bucket for bucket in raw_content.content},
                                  raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", None)]


class S3(AWSSectionCloudwatch):
    @property
    def name(self):
        return "s3"

    @property
    def interval(self):
        # BucketSizeBytes and NumberOfObjects are available per day
        # and must include 00:00h
        return 86400

    def _get_colleague_contents(self):
        colleague = self._received_results.get('s3_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, bucket_name in enumerate(colleague_contents.content.iterkeys()):
            for metric_name, unit, storage_classes in [
                ("BucketSizeBytes", "Bytes", [
                    "StandardStorage",
                    "StandardIAStorage",
                    "ReducedRedundancyStorage",
                ]),
                ("NumberOfObjects", "Count", ["AllStorageTypes"]),
            ]:
                for storage_class in storage_classes:
                    metrics.append({
                        'Id': self._create_id_for_metric_data_query(idx, metric_name,
                                                                    storage_class),
                        'Label': bucket_name,
                        'MetricStat': {
                            'Metric': {
                                'Namespace': 'AWS/S3',
                                'MetricName': metric_name,
                                'Dimensions': [{
                                    'Name': "BucketName",
                                    'Value': bucket_name,
                                }, {
                                    'Name': 'StorageType',
                                    'Value': storage_class,
                                }]
                            },
                            'Period': self.period,
                            'Stat': 'Average',
                            'Unit': unit,
                        },
                    })
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        for row in raw_content.content:
            bucket = colleague_contents.content.get(row['Label'])
            if bucket:
                row.update(bucket)
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


class S3Requests(AWSSectionCloudwatch):
    @property
    def name(self):
        return "s3_requests"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('s3_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, bucket_name in enumerate(colleague_contents.content.iterkeys()):
            for metric_name, unit in [
                ("AllRequests", "Count"),
                ("GetRequests", "Count"),
                ("PutRequests", "Count"),
                ("DeleteRequests", "Count"),
                ("HeadRequests", "Count"),
                ("PostRequests", "Count"),
                ("SelectRequests", "Count"),
                ("SelectScannedBytes", "Bytes"),
                ("SelectReturnedBytes", "Bytes"),
                ("ListRequests", "Count"),
                ("BytesDownloaded", "Bytes"),
                ("BytesUploaded", "Bytes"),
                ("4xxErrors", "Count"),
                ("5xxErrors", "Count"),
                ("FirstByteLatency", "Milliseconds"),
                ("TotalRequestLatency", "Milliseconds"),
            ]:
                metrics.append({
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': bucket_name,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/S3',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "BucketName",
                                'Value': bucket_name,
                            }]
                        },
                        'Period': self.period,
                        'Stat': 'Sum',  #reports per period
                        'Unit': unit,
                    },
                })
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        for row in raw_content.content:
            bucket = colleague_contents.content.get(row['Label'])
            if bucket:
                row.update(bucket)
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


#.
#   .--ELB-----------------------------------------------------------------.
#   |                          _____ _     ____                            |
#   |                         | ____| |   | __ )                           |
#   |                         |  _| | |   |  _ \                           |
#   |                         | |___| |___| |_) |                          |
#   |                         |_____|_____|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ELBLimits(AWSSectionLimits):
    @property
    def name(self):
        return "elb_limits"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def _fetch_raw_content(self, colleague_contents):
        """
        The AWS/ELB API method 'describe_account_limits' provides limit values
        but no values about the usage per limit thus we have to gather the usage
        values from 'describe_load_balancers'.
        """
        response = self._client.describe_load_balancers()
        load_balancers = self._get_response_content(response, 'LoadBalancerDescriptions')

        response = self._client.describe_account_limits()
        limits = self._get_response_content(response, 'Limits')
        return load_balancers, limits

    def _compute_content(self, raw_content, colleague_contents):
        load_balancers, limits = raw_content.content
        limits = {r["Name"]: int(r['Max']) for r in limits}

        self._add_limit(
            "",
            AWSLimit("load_balancers", "Load balancers", limits['classic-load-balancers'],
                     len(load_balancers)))

        for load_balancer in load_balancers:
            dns_name = load_balancer['DNSName']
            self._add_limit(
                dns_name,
                AWSLimit("load_balancer_listeners", "Listeners", limits['classic-listeners'],
                         len(load_balancer['ListenerDescriptions'])))
            self._add_limit(
                dns_name,
                AWSLimit("load_balancer_registered_instances", "Registered instances",
                         limits['classic-registered-instances'], len(load_balancer['Instances'])))
        return AWSComputedContent(load_balancers, raw_content.cache_timestamp)


class ELBSummary(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(ELBSummary, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['elb_names']
        self._tags = self._prepare_tags_for_api_response(self._config.service_config['elb_tags'])

    @property
    def name(self):
        return "elb_summary"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def _fetch_raw_content(self, colleague_contents):
        found_load_balancers = []
        for load_balancer in self._describe_load_balancers(colleague_contents):
            load_balancer_name = load_balancer['LoadBalancerName']
            try:
                response = self._client.describe_tags(LoadBalancerNames=[load_balancer_name])
            except botocore.exceptions.ClientError as e:
                # If there are no tags attached to a bucket we receive a 'ClientError'
                logging.info("%s/%s: No tags set, %s", self.name, load_balancer_name, e)
                response = {}

            tagging = [
                tag for tag_descr in self._get_response_content(response, 'TagDescriptions')
                for tag in tag_descr['Tags']
            ]
            if self._matches_tag_conditions(tagging):
                load_balancer['TagDescriptions'] = tagging
                found_load_balancers.append(load_balancer)
        return found_load_balancers

    def _describe_load_balancers(self, colleague_contents):
        if self._tags is None and self._names is not None:
            if colleague_contents.content:
                return [
                    load_balancer for load_balancer in colleague_contents.content
                    if load_balancer['LoadBalancerName'] in self._names
                ]
            response = self._client.describe_load_balancers(LoadBalancerNames=self._names)
        else:
            response = self._client.describe_load_balancers()
        return self._get_response_content(response, 'LoadBalancerDescriptions')

    def _matches_tag_conditions(self, tagging):
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        for tag in tagging:
            if tag in self._tags:
                return True
        return False

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for load_balancer in raw_content.content:
            content_by_piggyback_hosts.setdefault(load_balancer['DNSName'], load_balancer)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content.values())]


class ELBHealth(AWSSectionGeneric):
    @property
    def name(self):
        return "elb_health"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('elb_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _fetch_raw_content(self, colleague_contents):
        load_balancers = {}
        for load_balancer_dns_name, load_balancer in colleague_contents.content.iteritems():
            load_balancer_name = load_balancer['LoadBalancerName']
            response = self._client.describe_instance_health(LoadBalancerName=load_balancer_name)
            states = self._get_response_content(response, 'InstanceStates')
            if states:
                load_balancers.setdefault(load_balancer_dns_name, states)
        return load_balancers

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, content)
            for piggyback_hostname, content in computed_content.content.iteritems()
        ]


class ELB(AWSSectionCloudwatch):
    @property
    def name(self):
        return "elb"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('elb_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, (load_balancer_dns_name,
                  load_balancer) in enumerate(colleague_contents.content.iteritems()):
            load_balancer_name = load_balancer['LoadBalancerName']
            for metric_name, stat in [
                ("RequestCount", "Sum"),
                ("SurgeQueueLength", "Maximum"),
                ("SpilloverCount", "Sum"),
                ("Latency", "Average"),
                ("HTTPCode_ELB_4XX", "Sum"),
                ("HTTPCode_ELB_5XX", "Sum"),
                ("HTTPCode_Backend_2XX", "Sum"),
                ("HTTPCode_Backend_3XX", "Sum"),
                ("HTTPCode_Backend_4XX", "Sum"),
                ("HTTPCode_Backend_5XX", "Sum"),
                ("HealthyHostCount", "Average"),
                ("UnHealthyHostCount", "Average"),
                ("BackendConnectionErrors", "Sum"),
            ]:
                metrics.append({
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': load_balancer_dns_name,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/ELB',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "LoadBalancerName",
                                'Value': load_balancer_name,
                            }]
                        },
                        'Period': self.period,
                        'Stat': stat,
                    },
                })
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row['Label'], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


#.
#   .--EBS-----------------------------------------------------------------.
#   |                          _____ ____ ____                             |
#   |                         | ____| __ ) ___|                            |
#   |                         |  _| |  _ \___ \                            |
#   |                         | |___| |_) |__) |                           |
#   |                         |_____|____/____/                            |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# EBS are attached to EC2 instances. Thus we put the content to related EC2
# instance as piggyback host.


class EBSLimits(AWSSectionLimits):
    @property
    def name(self):
        return "ebs_limits"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def _fetch_raw_content(self, colleague_contents):
        response = self._client.describe_volumes()
        volumes = self._get_response_content(response, 'Volumes')

        response = self._client.describe_snapshots()
        snapshots = self._get_response_content(response, 'Snapshots')
        return volumes, snapshots

    def _compute_content(self, raw_content, colleague_contents):
        volumes, snapshots = raw_content.content

        vol_storage_standard = 0
        vol_storage_io1 = 0
        vol_storage_gp2 = 0
        vol_storage_sc1 = 0
        vol_storage_st1 = 0
        vol_iops_io1 = 0
        for volume in volumes:
            vol_type = volume['VolumeType']
            vol_size = volume['Size']
            if vol_type == 'standard':
                vol_storage_standard += vol_size
            elif vol_type == 'io1':
                vol_storage_io1 += vol_size
                vol_iops_io1 += volume['Iops']
            elif vol_type == 'gp2':
                vol_storage_gp2 += vol_size
            elif vol_type == 'sc1':
                vol_storage_sc1 += vol_size
            elif vol_type == 'st1':
                vol_storage_st1 += vol_size
            else:
                logging.info("%s: Unhandled volume type: '%s'", self.name, vol_type)

        # These are total limits and not instance specific
        # Space values are in TiB.
        self._add_limit(
            "", AWSLimit('block_store_snapshots', 'Block store snapshots', 100000, len(snapshots)))
        self._add_limit(
            "",
            AWSLimit('block_store_space_standard', 'Magnetic volumes space', 300,
                     vol_storage_standard))
        self._add_limit(
            "", AWSLimit('block_store_space_io1', 'Provisioned IOPS SSD space', 300,
                         vol_storage_io1))
        self._add_limit(
            "",
            AWSLimit('block_store_iops_io1', 'Provisioned IOPS SSD IO operations per second',
                     300000, vol_storage_io1))
        self._add_limit(
            "", AWSLimit('block_store_space_gp2', 'General Purpose SSD space', 300,
                         vol_storage_gp2))
        self._add_limit("", AWSLimit('block_store_space_sc1', 'Cold HDD space', 300,
                                     vol_storage_sc1))
        self._add_limit(
            "",
            AWSLimit('block_store_space_st1', 'Throughput Optimized HDD space', 300,
                     vol_storage_st1))
        return AWSComputedContent(volumes, raw_content.cache_timestamp)


class EBSSummary(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(EBSSummary, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['ebs_names']
        self._tags = self._config.service_config['ebs_tags']

    @property
    def name(self):
        return "ebs_summary"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ebs_limits')
        volumes = []
        max_cache_timestamp = 0.0
        if colleague and colleague.content:
            max_cache_timestamp = max(max_cache_timestamp, colleague.cache_timestamp)
            volumes = colleague.content

        colleague = self._received_results.get('ec2_summary')
        instances = []
        if colleague and colleague.content:
            max_cache_timestamp = max(max_cache_timestamp, colleague.cache_timestamp)
            instances = colleague.content

        return AWSColleagueContents((volumes, instances), max_cache_timestamp)

    def _fetch_raw_content(self, colleague_contents):
        col_volumes, _col_instances = colleague_contents.content
        if self._tags is None and self._names is not None:
            return self._fetch_volumes_filtered_by_names(col_volumes)
        if self._tags is not None:
            return self._fetch_volumes_filtered_by_tags(col_volumes)
        return self._fetch_volumes_without_filter()

    def _fetch_volumes_filtered_by_names(self, col_volumes):
        if col_volumes:
            volumes = {
                vol['VolumeId']: vol for vol in col_volumes if vol['VolumeId'] in self._names
            }
        else:
            volumes = self._format_volumes(self._client.describe_volumes(VolumeIds=self._names))
        return (volumes,
                self._format_volume_states(
                    self._client.describe_volume_status(VolumeIds=self._names)))

    def _fetch_volumes_filtered_by_tags(self, col_volumes):
        if col_volumes:
            tags = self._prepare_tags_for_api_response(self._tags)
            volumes = {
                vol['VolumeId']: vol for vol in col_volumes for tag in vol['Tags'] if tag in tags
            }
        else:
            volumes = self._format_volumes(self._client.describe_volumes(Filters=self._tags))
        return (volumes,
                self._format_volume_states(self._client.describe_volume_status(Filters=self._tags)))

    def _fetch_volumes_without_filter(self):
        return (self._format_volumes(self._client.describe_volumes()),
                self._format_volume_states(self._client.describe_volume_status()))

    def _format_volumes(self, response):
        return {r['VolumeId']: r for r in self._get_response_content(response, 'Volumes')}

    def _format_volume_states(self, response):
        return {r['VolumeId']: r for r in self._get_response_content(response, 'VolumeStatuses')}

    def _compute_content(self, raw_content, colleague_contents):
        _col_volumes, col_instances = colleague_contents.content
        instance_name_mapping = {v['InstanceId']: k for k, v in col_instances.iteritems()}

        volumes, volume_states = raw_content.content
        content = []
        for volume_id in set(volumes.keys()).union(set(volume_states.keys())):
            volume = volumes.get(volume_id, {})
            volume.update(volume_states.get(volume_id, {}))
            content.append(volume)

        content_by_piggyback_hosts = {}
        for row in content:
            for attachment in row['Attachments']:
                attachment_id = attachment['InstanceId']
                instance_name = instance_name_mapping.get(attachment_id)
                if instance_name is None:
                    instance_name = ""
                content_by_piggyback_hosts.setdefault(instance_name, []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


class EBS(AWSSectionCloudwatch):
    @property
    def name(self):
        return "ebs"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('ebs_summary')
        if colleague and colleague.content:
            return AWSColleagueContents([(instance_name, row['VolumeId'], row['VolumeType'])
                                         for instance_name, rows in colleague.content.iteritems()
                                         for row in rows], colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, (instance_name, volume_name, volume_type) in enumerate(colleague_contents.content):
            for metric_name, unit, volume_types in [
                ("VolumeReadOps", "Count", []),
                ("VolumeWriteOps", "Count", []),
                ("VolumeReadBytes", "Bytes", []),
                ("VolumeWriteBytes", "Bytes", []),
                ("VolumeQueueLength", "Count", []),
                ("BurstBalance", "Percent", ["gp2", "st1", "sc1"]),
                    #("VolumeThroughputPercentage", "Percent", ["io1"]),
                    #("VolumeConsumedReadWriteOps", "Count", ["io1"]),
                    #("VolumeTotalReadTime", "Seconds", []),
                    #("VolumeTotalWriteTime", "Seconds", []),
                    #("VolumeIdleTime", "Seconds", []),
                    #("VolumeStatus", None, []),
                    #("IOPerformance", None, ["io1"]),
            ]:
                if volume_types and volume_type not in volume_types:
                    continue
                metric = {
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': instance_name,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EBS',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "VolumeID",
                                'Value': volume_name,
                            }]
                        },
                        'Period': self.period,
                        'Stat': 'Average',
                    },
                }
                if unit:
                    metric['MetricStat']['Unit'] = unit
                metrics.append(metric)
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        content_by_piggyback_hosts = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row['Label'], []).append(row)
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.iteritems()
        ]


#.
#   .--RDS-----------------------------------------------------------------.
#   |                          ____  ____  ____                            |
#   |                         |  _ \|  _ \/ ___|                           |
#   |                         | |_) | | | \___ \                           |
#   |                         |  _ <| |_| |___) |                          |
#   |                         |_| \_\____/|____/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'

AWSRDSLimitNameMap = {
    "DBClusters": ("db_clusters", "DB clusters"),
    "DBClusterParameterGroups": ("db_cluster_parameter_groups", "DB cluster parameter groups"),
    "DBInstances": ("db_instances", "DB instances"),
    "EventSubscriptions": ("event_subscriptions", "Event subscriptions"),
    "ManualSnapshots": ("manual_snapshots", "Manual snapshots"),
    "OptionGroups": ("option_groups", "Option groups"),
    "DBParameterGroups": ("db_parameter_groups", "DB parameter groups"),
    "ReadReplicasPerMaster": ("read_replica_per_master", "Read replica per master"),
    "ReservedDBInstances": ("reserved_db_instances", "Reserved DB instances"),
    "DBSecurityGroups": ("db_security_groups", "DB security groups"),
    "DBSubnetGroups": ("db_subnet_groups", "DB subnet groups"),
    "SubnetsPerDBSubnetGroup": ("subnet_per_db_subnet_groups", "Subnet per DB subnet groups"),
    "AllocatedStorage": ("allocated_storage", "Allocated storage"),
    "AuthorizationsPerDBSecurityGroup": ("auths_per_db_security_groups",
                                         "Authorizations per DB security group"),
    "DBClusterRoles": ("db_cluster_roles", "DB cluster roles"),
}


class RDSLimits(AWSSectionLimits):
    @property
    def name(self):
        return "rds_limits"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def _fetch_raw_content(self, colleague_contents):
        """
        AWS/RDS API method 'describe_account_attributes' already sends
        limit and usage values.
        """
        response = self._client.describe_account_attributes()
        return self._get_response_content(response, 'AccountQuotas')

    def _compute_content(self, raw_content, colleague_contents):
        for limit in raw_content.content:
            quota_name = limit['AccountQuotaName']
            key, title = AWSRDSLimitNameMap.get(quota_name, (None, None))
            if key is None or title is None:
                logging.info("%s: Unhandled account quota name: '%s'", self.name, quota_name)
                continue
            self._add_limit("", AWSLimit(key, title, int(limit['Max']), int(limit['Used'])))
        return AWSComputedContent(None, 0.0)


class RDSSummary(AWSSectionGeneric):
    def __init__(self, client, region, config, distributor=None):
        super(RDSSummary, self).__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config['rds_names']
        self._tags = self._config.service_config['rds_tags']

    @property
    def name(self):
        return "rds_summary"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        return AWSColleagueContents(None, 0.0)

    def _fetch_raw_content(self, colleague_contents):
        response = self._describe_db_instances()
        return self._get_response_content(response, 'DBInstances')

    def _describe_db_instances(self):
        if self._names is not None:
            return [
                self._client.describe_db_instances(DBInstanceIdentifier=name)
                for name in self._names
            ]
        elif self._tags is not None:
            return [self._client.describe_db_instances(Filters=self._tags) for name in self._names]
        return self._client.describe_db_instances()

    def _compute_content(self, raw_content, colleague_contents):
        return AWSComputedContent(
            {instance['DBInstanceIdentifier']: instance for instance in raw_content.content},
            raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content.values())]


class RDS(AWSSectionCloudwatch):
    @property
    def name(self):
        return "rds"

    @property
    def interval(self):
        return 300

    def _get_colleague_contents(self):
        colleague = self._received_results.get('rds_summary')
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _get_metrics(self, colleague_contents):
        metrics = []
        for idx, instance_id in enumerate(colleague_contents.content.iterkeys()):
            for metric_name, unit in [
                ("BinLogDiskUsage", "Bytes"),
                ("BurstBalance", "Percent"),
                ("CPUUtilization", "Percent"),
                ("CPUCreditUsage", "Count"),
                ("CPUCreditBalance", "Count"),
                ("DatabaseConnections", "Count"),
                ("DiskQueueDepth", "Count"),
                ("FailedSQLServerAgentJobsCount", "Count/Second"),
                ("NetworkReceiveThroughput", "Bytes/Second"),
                ("NetworkTransmitThroughput", "Bytes/Second"),
                ("OldestReplicationSlotLag", "Megabytes"),
                ("ReadIOPS", "Count/Second"),
                ("ReadLatency", "Seconds"),
                ("ReadThroughput", "Bytes/Second"),
                ("ReplicaLag", "Seconds"),
                ("ReplicationSlotDiskUsage", "Megabytes"),
                ("TransactionLogsDiskUsage", "Megabytes"),
                ("TransactionLogsGeneration", "Megabytes/Second"),
                ("WriteIOPS", "Count/Second"),
                ("WriteLatency", "Seconds"),
                ("WriteThroughput", "Bytes/Second"),
                    #("FreeableMemory", "Bytes"),
                    #("SwapUsage", "Bytes"),
                    #("FreeStorageSpace", "Bytes"),
                    #("MaximumUsedTransactionIDs", "Count"),
            ]:
                metric = {
                    'Id': self._create_id_for_metric_data_query(idx, metric_name),
                    'Label': instance_id,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/RDS',
                            'MetricName': metric_name,
                            'Dimensions': [{
                                'Name': "DBInstanceIdentifier",
                                'Value': instance_id,
                            }]
                        },
                        'Period': self.period,
                        'Stat': 'Average',
                    },
                }
                if unit:
                    metric['MetricStat']['Unit'] = unit
                metrics.append(metric)
        return metrics

    def _compute_content(self, raw_content, colleague_contents):
        for row in raw_content.content:
            row.update(colleague_contents.content.get(row['Label'], {}))
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    def _create_results(self, computed_content):
        return [AWSSectionResult("", computed_content.content)]


#.
#   .--sections------------------------------------------------------------.
#   |                               _   _                                  |
#   |                 ___  ___  ___| |_(_) ___  _ __  ___                  |
#   |                / __|/ _ \/ __| __| |/ _ \| '_ \/ __|                 |
#   |                \__ \  __/ (__| |_| | (_) | | | \__ \                 |
#   |                |___/\___|\___|\__|_|\___/|_| |_|___/                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class AWSSections(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, hostname, session, debug=False):
        self._hostname = hostname
        self._session = session
        self._debug = debug
        self._sections = []

    @abc.abstractmethod
    def init_sections(self, services, region, config):
        pass

    def _init_client(self, client_key):
        try:
            return self._session.client(client_key)
        except (ValueError, botocore.exceptions.ClientError,
                botocore.exceptions.UnknownServiceError) as e:
            # If region name is not valid we get a ValueError
            # but not in all cases, eg.:
            # 1. 'eu-central-' raises a ValueError
            # 2. 'foobar' does not raise a ValueError
            # In the second case we get an exception raised by botocore
            # during we execute an operation, eg. cloudwatch.get_metrics(**kwargs):
            # - botocore.exceptions.EndpointConnectionError
            logging.info("Invalid region name or client key %s: %s", client_key, e)
            raise

    def run(self, use_cache=True):
        exceptions = []
        results = {}
        for section in self._sections:
            try:
                section_result = section.run(use_cache=use_cache)
            except AssertionError as e:
                logging.info(e)
                if self._debug:
                    raise
            except Exception as e:
                logging.info(e)
                if self._debug:
                    raise
                exceptions.append(e)
            else:
                results.setdefault((section.name, section_result.cache_timestamp, section.interval),
                                   section_result.results)

        self._write_exceptions(exceptions)
        self._write_section_results(results)

    def _write_exceptions(self, exceptions):
        sys.stdout.write("<<<aws_exceptions>>>\n")
        if exceptions:
            out = "\n".join([e.message for e in exceptions])
        else:
            out = "No exceptions"
        sys.stdout.write("%s: %s\n" % (self.__class__.__name__, out))

    def _write_section_results(self, results):
        if not results:
            logging.info("%s: No results or cached data", self.__class__.__name__)
            return

        for (section_name, cache_timestamp, section_interval), result in results.iteritems():
            if not result:
                logging.info("%s: No results", section_name)
                continue

            if not isinstance(result, list):
                logging.info(
                    "%s: Section result must be of type 'list' containing 'AWSSectionResults'",
                    section_name)
                continue

            cached_suffix = ""
            if section_interval > 60:
                cached_suffix = ":cached(%s,%s)" % (int(cache_timestamp), section_interval + 60)

            if any([r.content for r in result]):
                self._write_section_result(section_name, cached_suffix, result)

    def _write_section_result(self, section_name, cached_suffix, result):
        section_header = "<<<aws_%s%s>>>\n" % (section_name, cached_suffix)
        for row in result:
            write_piggyback_header = row.piggyback_hostname\
                                     and row.piggyback_hostname != self._hostname
            if write_piggyback_header:
                sys.stdout.write("<<<<%s>>>>\n" % row.piggyback_hostname)
            sys.stdout.write(section_header)
            sys.stdout.write("%s\n" % json.dumps(row.content, default=_datetime_converter))
            if write_piggyback_header:
                sys.stdout.write("<<<<>>>>\n")


class AWSSectionsUSEast(AWSSections):
    """
    Some clients like CostExplorer only work with US East region:
    https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-api.html
    """

    def init_sections(self, services, region, config):
        #---clients---------------------------------------------------------
        ce_client = self._init_client('ce')

        #---distributors----------------------------------------------------

        #---sections with distributors--------------------------------------

        #---sections--------------------------------------------------------
        ce = CostsAndUsage(ce_client, region, config)

        #---register sections to distributors-------------------------------

        #---register sections for execution---------------------------------
        if 'ce' in services:
            self._sections.append(ce)


class AWSSectionsGeneric(AWSSections):
    def init_sections(self, services, region, config):
        #---clients---------------------------------------------------------
        ec2_client = self._init_client('ec2')
        elb_client = self._init_client('elb')
        s3_client = self._init_client('s3')
        rds_client = self._init_client('rds')
        cloudwatch_client = self._init_client('cloudwatch')

        #---distributors----------------------------------------------------
        ec2_limits_distributor = ResultDistributor()
        ec2_summary_distributor = ResultDistributor()

        elb_limits_distributor = ResultDistributor()
        elb_summary_distributor = ResultDistributor()

        ebs_limits_distributor = ResultDistributor()
        ebs_summary_distributor = ResultDistributor()

        s3_limits_distributor = ResultDistributor()
        s3_summary_distributor = ResultDistributor()

        rds_summary_distributor = ResultDistributor()

        #---sections with distributors--------------------------------------
        ec2_limits = EC2Limits(ec2_client, region, config, ec2_limits_distributor)
        ec2_summary = EC2Summary(ec2_client, region, config, ec2_summary_distributor)

        ebs_limits = EBSLimits(ec2_client, region, config, ebs_limits_distributor)
        ebs_summary = EBSSummary(ec2_client, region, config, ebs_summary_distributor)

        elb_limits = ELBLimits(elb_client, region, config, elb_limits_distributor)
        elb_summary = ELBSummary(elb_client, region, config, elb_summary_distributor)

        s3_limits = S3Limits(s3_client, region, config, s3_limits_distributor)
        s3_summary = S3Summary(s3_client, region, config, s3_summary_distributor)

        rds_summary = RDSSummary(rds_client, region, config, rds_summary_distributor)

        #---sections--------------------------------------------------------
        elb_health = ELBHealth(elb_client, region, config)
        ec2_security_groups = EC2SecurityGroups(ec2_client, region, config)
        ec2 = EC2(cloudwatch_client, region, config)

        ebs = EBS(cloudwatch_client, region, config)
        elb = ELB(cloudwatch_client, region, config)

        s3 = S3(cloudwatch_client, region, config)
        s3_requests = S3Requests(cloudwatch_client, region, config)

        rds_limits = RDSLimits(rds_client, region, config)
        rds = RDS(cloudwatch_client, region, config)

        #---register sections to distributors-------------------------------
        ec2_limits_distributor.add(ec2_summary)
        ec2_summary_distributor.add(ec2_security_groups)
        ec2_summary_distributor.add(ec2)
        ec2_summary_distributor.add(ebs_summary)
        ec2_summary_distributor.add(ebs)

        ebs_limits_distributor.add(ebs_summary)
        ebs_summary_distributor.add(ebs)

        elb_limits_distributor.add(elb_summary)
        elb_summary_distributor.add(elb_health)
        elb_summary_distributor.add(elb)

        s3_limits_distributor.add(s3_summary)
        s3_summary_distributor.add(s3)
        s3_summary_distributor.add(s3_requests)

        rds_summary_distributor.add(rds)

        #---register sections for execution---------------------------------
        if 'ec2' in services:
            if config.service_config.get('ec2_limits'):
                self._sections.append(ec2_limits)
            self._sections.append(ec2_summary)
            self._sections.append(ec2_security_groups)
            self._sections.append(ec2)

        if 'ebs' in services:
            if config.service_config.get('ebs_limits'):
                self._sections.append(ebs_limits)
            self._sections.append(ebs_summary)
            self._sections.append(ebs)

        if 'elb' in services:
            if config.service_config.get('elb_limits'):
                self._sections.append(elb_limits)
            self._sections.append(elb_summary)
            self._sections.append(elb_health)
            self._sections.append(elb)

        if 's3' in services:
            if config.service_config.get('s3_limits'):
                self._sections.append(s3_limits)
            self._sections.append(s3_summary)
            self._sections.append(s3)
            if config.service_config['s3_requests']:
                self._sections.append(s3_requests)

        if 'rds' in services:
            if config.service_config.get('rds_limits'):
                self._sections.append(rds_limits)
            self._sections.append(rds_summary)
            self._sections.append(rds)


#.
#   .--main----------------------------------------------------------------.
#   |                                       _                              |
#   |                       _ __ ___   __ _(_)_ __                         |
#   |                      | '_ ` _ \ / _` | | '_ \                        |
#   |                      | | | | | | (_| | | | | |                       |
#   |                      |_| |_| |_|\__,_|_|_| |_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

AWSServiceAttributes = NamedTuple("AWSServiceAttributes", [
    ("key", str),
    ("title", str),
    ("global_service", bool),
    ("filter_by_names_or_tags", bool),
    ("limits", bool),
])

AWSServices = [
    AWSServiceAttributes(
        key="ce",
        title="Costs and usage",
        global_service=True,
        filter_by_names_or_tags=False,
        limits=False),
    AWSServiceAttributes(
        key="ec2",
        title="Elastic Compute Cloud (EC2)",
        global_service=False,
        filter_by_names_or_tags=True,
        limits=True),
    AWSServiceAttributes(
        key="ebs",
        title="Elastic Block Storage (EBS)",
        global_service=False,
        filter_by_names_or_tags=True,
        limits=True),
    AWSServiceAttributes(
        key="s3",
        title="Simple Storage Service (S3)",
        global_service=False,
        filter_by_names_or_tags=True,
        limits=True),
    AWSServiceAttributes(
        key="elb",
        title="Elastic Load Balancing (ELB)",
        global_service=False,
        filter_by_names_or_tags=True,
        limits=True),
    AWSServiceAttributes(
        key="rds",
        title="Relational Database Service (RDS)",
        global_service=False,
        filter_by_names_or_tags=True,
        limits=True),
]


def parse_arguments(argv):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--debug", action="store_true", help="Raise Python exceptions.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log messages from AWS library 'boto3' and 'botocore'.")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Execute all sections, do not rely on cached data. Cached data will not be overwritten."
    )

    parser.add_argument(
        "--access-key-id", required=True, help="The access key for your AWS account.")
    parser.add_argument(
        "--secret-access-key", required=True, help="The secret key for your AWS account.")
    parser.add_argument(
        "--regions",
        nargs='+',
        help="Regions to use:\n%s" % "\n".join(["%-15s %s" % e for e in AWSRegions]))

    parser.add_argument(
        "--global-services",
        nargs='+',
        help="Global services to monitor:\n%s" % "\n".join(
            ["%-15s %s" % (e.key, e.title) for e in AWSServices if e.global_service]))

    parser.add_argument(
        "--services",
        nargs='+',
        help="Services per region to monitor:\n%s" % "\n".join(
            ["%-15s %s" % (e.key, e.title) for e in AWSServices if not e.global_service]))

    for service in AWSServices:
        if service.filter_by_names_or_tags:
            parser.add_argument(
                '--%s-names' % service.key, nargs='+', help="Names for %s" % service.title)
            parser.add_argument(
                '--%s-tag-key' % service.key,
                nargs=1,
                action='append',
                help="Tag key for %s" % service.title)
            parser.add_argument(
                '--%s-tag-values' % service.key,
                nargs='+',
                action='append',
                help="Tag values for %s" % service.title)
        if service.limits:
            parser.add_argument(
                '--%s-limits' % service.key,
                action="store_true",
                help="Monitor limits for %s" % service.title)

    parser.add_argument(
        "--s3-requests",
        action="store_true",
        help="You have to enable requests metrics in AWS/S3 console. This is a paid feature.")

    parser.add_argument('--overall-tag-key', nargs=1, action='append', help="Overall tag key")
    parser.add_argument(
        '--overall-tag-values', nargs='+', action='append', help="Overall tag values")

    parser.add_argument("--hostname", required=True)
    return parser.parse_args(argv)


def setup_logging(opt_debug, opt_verbose):
    logger = logging.getLogger()
    logger.disabled = True
    fmt = '%(levelname)s: %(name)s: %(filename)s: %(lineno)s: %(message)s'
    lvl = logging.INFO
    if opt_verbose:
        logger.disabled = False
        lvl = logging.DEBUG
    elif opt_debug:
        logger.disabled = False
    logging.basicConfig(level=lvl, format=fmt)


def create_session(access_key_id, secret_access_key, region):
    return boto3.session.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region)


class AWSConfig(object):
    def __init__(self, hostname, overall_tags):
        self.hostname = hostname
        self._overall_tags = self._prepare_tags(overall_tags)
        self.service_config = {}

    def add_service_tags(self, tags_key, tags):
        self.service_config.setdefault(tags_key, None)
        if tags != (None, None):
            self.service_config[tags_key] = self._prepare_tags(tags)
        elif self._overall_tags:
            self.service_config[tags_key] = self._overall_tags

    def _prepare_tags(self, tags):
        """
        Prepare tags format as needed in API methods:
        Filters=[{'Name': 'tag:KEY', 'Values': [VAL,...]}, ...]
        Keys AND values must be set for filtering.
        """
        keys, values = tags
        if keys and values:
            return [{
                'Name': 'tag:%s' % k,
                'Values': v
            } for k, v in zip([k[0] for k in keys], values)]
        return

    def add_single_service_config(self, key, value):
        self.service_config.setdefault(key, value)


def main(args=None):
    if args is None:
        cmk.utils.password_store.replace_passwords()
        args = sys.argv[1:]

    args = parse_arguments(args)
    setup_logging(args.debug, args.verbose)
    hostname = args.hostname

    aws_config = AWSConfig(hostname, (args.overall_tag_key, args.overall_tag_values))
    for service_key, service_names, service_tags, service_limits in [
        ("ec2", args.ec2_names, (args.ec2_tag_key, args.ec2_tag_values), args.ec2_limits),
        ("ebs", args.ebs_names, (args.ebs_tag_key, args.ebs_tag_values), args.ebs_limits),
        ("s3", args.s3_names, (args.s3_tag_key, args.s3_tag_values), args.s3_limits),
        ("elb", args.elb_names, (args.elb_tag_key, args.elb_tag_values), args.elb_limits),
        ("rds", args.rds_names, (args.rds_tag_key, args.rds_tag_values), args.rds_limits),
    ]:
        aws_config.add_single_service_config("%s_names" % service_key, service_names)
        aws_config.add_service_tags("%s_tags" % service_key, service_tags)
        aws_config.add_single_service_config("%s_limits" % service_key, service_limits)

    aws_config.add_single_service_config("s3_requests", args.s3_requests)

    has_exceptions = False
    for aws_services, aws_regions, aws_sections in [
        (args.global_services, ["us-east-1"], AWSSectionsUSEast),
        (args.services, args.regions, AWSSectionsGeneric),
    ]:
        if not aws_services or not aws_regions:
            continue
        for region in aws_regions:
            try:
                session = create_session(args.access_key_id, args.secret_access_key, region)
                sections = aws_sections(hostname, session, debug=args.debug)
                sections.init_sections(aws_services, region, aws_config)
                sections.run(use_cache=not args.no_cache)
            except AssertionError:
                if args.debug:
                    return 1
            except Exception as e:
                logging.info(e)
                has_exceptions = True
                if args.debug:
                    return 1
    if has_exceptions:
        return 1
    return 0
