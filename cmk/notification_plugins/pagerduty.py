# -*- coding: utf-8 -*-
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
r"""
Send notification messages to PagerDuty
=======================================

"""
from __future__ import unicode_literals

from typing import Dict  # pylint: disable=unused-import

from cmk.notification_plugins.utils import cmk_links, retrieve_from_passwordstore


def pagerduty_event_type(event):
    return {
        "PROBLEM": "trigger",
        "ACKNOWLEDGEMENT": "acknowledge",
        "RECOVERY": "resolve",
    }[event]


def pagerduty_severity(state):
    return {
        "CRITICAL": "critical",
        "DOWN": "critical",
        "WARNING": "warning",
        "OK": "info",
        "UP": "info",
        "UNKNOWN": "error",
        "UNREACHABLE": "error",
    }[state]


def perf_values(data):
    entry = ['Value', 'warn_level', 'crit_level', 'min', 'max']
    return ",".join([e + '=' + v for e, v in zip(entry, data.split(";")) if v])


def construct_perfdata(data):
    data = (item.split("=") for item in data.split())
    data = {k: perf_values(v) for k, v in data}
    return data


def pagerduty_msg(context):
    # type: (Dict) -> Dict
    """Build the PagerDuty incident payload"""

    host_url, service_url = cmk_links(context)

    if context.get('WHAT', None) == "SERVICE":
        state = context["SERVICESTATE"]
        incident_key = '{SERVICEDESC}/{HOSTNAME}:{HOSTADDRESS}'.format(**context).replace(" ", "")
        incident = "{SERVICESTATE}: {SERVICEDESC} on {HOSTNAME}".format(**context)
        output = context["SERVICEOUTPUT"]
        perfdata = construct_perfdata(context["SERVICEPERFDATA"])
        incident_url = service_url
    else:
        state = context["HOSTSTATE"]
        incident_key = '{HOSTNAME}:{HOSTADDRESS}'.format(**context).replace(" ", "")
        incident = '{HOSTNAME} is {HOSTSTATE}'.format(**context)
        perfdata = construct_perfdata(context["HOSTPERFDATA"])
        output = context["HOSTOUTPUT"]
        incident_url = host_url

    msg_payload = {
        "routing_key": retrieve_from_passwordstore(context.get('PARAMETER_ROUTING_KEY')),
        "event_action": pagerduty_event_type(context.get('NOTIFICATIONTYPE')),
        "dedup_key": incident_key,
        "payload": {
            "summary": incident,
            "source": context.get('HOSTADDRESS'),
            "severity": pagerduty_severity(state),
            "custom_details": {
                "info": output,
                "host": context.get('HOSTNAME'),
                "host_address": context.get('HOSTADDRESS'),
                "perfdata": perfdata,
            }
        }
    }
    if incident_url:
        msg_payload.update({"client": "Check_MK", "client_url": incident_url})

    return msg_payload
