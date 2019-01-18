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
    Float,
    Integer,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "mysql_innodb_io",
    _("MySQL InnoDB Throughput"),
    Dictionary(
        elements=[("read",
                   Tuple(
                       title=_("Read throughput"),
                       elements=[
                           Float(title=_("warning at"), unit=_("MB/s")),
                           Float(title=_("critical at"), unit=_("MB/s"))
                       ])),
                  ("write",
                   Tuple(
                       title=_("Write throughput"),
                       elements=[
                           Float(title=_("warning at"), unit=_("MB/s")),
                           Float(title=_("critical at"), unit=_("MB/s"))
                       ])),
                  ("average",
                   Integer(
                       title=_("Average"),
                       help=_("When averaging is set, a floating average value "
                              "of the disk throughput is computed and the levels for read "
                              "and write will be applied to the average instead of the current "
                              "value."),
                       minvalue=1,
                       default_value=5,
                       unit=_("minutes")))]),
    TextAscii(
        title=_("Instance"),
        help=_("Only needed if you have multiple MySQL Instances on one server"),
    ),
    "dict",
)