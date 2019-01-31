#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    ListChoice,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersEnvironment,
    register_check_parameters,
)

bvip_link_states = [
    (0, "No Link"),
    (1, "10 MBit - HalfDuplex"),
    (2, "10 MBit - FullDuplex"),
    (3, "100 Mbit - HalfDuplex"),
    (4, "100 Mbit - FullDuplex"),
    (5, "1 Gbit - FullDuplex"),
    (7, "Wifi"),
]

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "bvip_link",
    _("Allowed Network states on Bosch IP Cameras"),
    Dictionary(
        title=_("Update State"),
        elements=[
            ("ok_states",
             ListChoice(
                 title=_("States which result in OK"),
                 choices=bvip_link_states,
                 default_value=[0, 4, 5])),
            ("warn_states",
             ListChoice(
                 title=_("States which result in Warning"),
                 choices=bvip_link_states,
                 default_value=[7])),
            ("crit_states",
             ListChoice(
                 title=_("States which result in Critical"),
                 choices=bvip_link_states,
                 default_value=[1, 2, 3])),
        ],
        optional_keys=None,
    ),
    None,
    match_type="dict",
)