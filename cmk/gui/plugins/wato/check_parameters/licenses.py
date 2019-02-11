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
    Alternative,
    FixedValue,
    Integer,
    Percentage,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _vs_license():
    return Alternative(
        title=_("Levels for Number of Licenses"),
        style="dropdown",
        default_value=None,
        elements=[
            Tuple(
                title=_("Absolute levels for unused licenses"),
                elements=[
                    Integer(title=_("Warning below"), default_value=5, unit=_("unused licenses")),
                    Integer(title=_("Critical below"), default_value=0, unit=_("unused licenses")),
                ]),
            Tuple(
                title=_("Percentual levels for unused licenses"),
                elements=[
                    Percentage(title=_("Warning below"), default_value=10.0),
                    Percentage(title=_("Critical below"), default_value=0),
                ]),
            FixedValue(
                None,
                totext=_("Critical when all licenses are used"),
                title=_("Go critical if all licenses are used"),
            ),
            FixedValue(
                False,
                title=_("Always report OK"),
                totext=_("Alerting depending on the number of used licenses is disabled"),
            )
        ])


@rulespec_registry.register
class RulespecCheckgroupParametersCitrixLicenses(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "citrix_licenses"

    @property
    def title(self):
        return _("Number of used Citrix licenses")

    @property
    def parameter_valuespec(self):
        return _vs_license()

    @property
    def item_spec(self):
        return TextAscii(
            title=_("ID of the license, e.g. <tt>PVSD_STD_CCS</tt>"),
            allow_empty=False,
        )


@rulespec_registry.register
class RulespecCheckgroupParametersEsxLicenses(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "esx_licenses"

    @property
    def title(self):
        return _("Number of used VMware licenses")

    @property
    def parameter_valuespec(self):
        return _vs_license()

    @property
    def item_spec(self):
        return TextAscii(
            title=_("Name of the license"),
            help=_("For example <tt>VMware vSphere 5 Standard</tt>"),
            allow_empty=False,
        )


@rulespec_registry.register
class RulespecCheckgroupParametersIbmsvcLicenses(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "ibmsvc_licenses"

    @property
    def title(self):
        return _("Number of used IBM SVC licenses")

    @property
    def parameter_valuespec(self):
        return _vs_license()

    @property
    def item_spec(self):
        return TextAscii(
            title=_("ID of the license, e.g. <tt>virtualization</tt>"),
            allow_empty=False,
        )


@rulespec_registry.register
class RulespecCheckgroupParametersRdsLicenses(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "rds_licenses"

    @property
    def title(self):
        return _("Number of used Remote Desktop Licenses")

    @property
    def parameter_valuespec(self):
        return _vs_license()

    @property
    def item_spec(self):
        return TextAscii(
            title=_("ID of the license, e.g. <tt>Windows Server 2008 R2</tt>"),
            allow_empty=False,
        )
