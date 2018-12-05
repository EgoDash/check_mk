#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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
"""Code for processing Check_MK werks. This is needed by several components,
so it's best place is in the central library."""

import itertools
import json

from pathlib2 import Path

import cmk.paths

from cmk.exceptions import MKGeneralException
from cmk.i18n import _


def werk_classes():
    return {
        "feature": _("New feature"),
        "fix": _("Bug fix"),
        "security": _("Security fix"),
    }


def werk_components():
    return {
        # CRE
        "core": _("Core & setup"),
        "checks": _("Checks & agents"),
        "multisite": _("User interface"),
        "wato": _("WATO"),
        "notifications": _("Notifications"),
        "bi": _("BI"),
        "reporting": _("Reporting & availability"),
        "ec": _("Event console"),
        "livestatus": _("Livestatus"),
        "liveproxy": _("Livestatus proxy"),
        "inv": _("HW/SW inventory"),

        # CEE
        "cmc": _("The Check_MK Micro Core"),
        "setup": _("Setup, site management"),
        "config": _("Configuration generation"),
        "inline-snmp": _("Inline SNMP"),
        "agents": _("Agent bakery"),
        "metrics": _("Metrics system"),
        "alerts": _("Alert handlers"),

        # CMK-OMD
        "omd": _("Site management"),
        "rpm": _("RPM packaging"),
        "deb": _("DEB packaging"),
        "nagvis": _("NagVis"),
        "packages": _("Other components"),
        "distros": _("Linux distributions"),
    }


def werk_levels():
    return {
        1: _("Trivial change"),
        2: _("Prominent change"),
        3: _("Major change"),
    }


def werk_compatibilities():
    return {
        "compat": _("Compatible"),
        "incomp_ack": _("Incompatible"),
        "incomp_unack": _("Incompatible - TODO"),
    }


def _compiled_werks_dir():
    return Path(cmk.paths.share_dir) / "werks"


def load():
    werks = {}
    # The suppressions are needed because of https://github.com/PyCQA/pylint/issues/1660
    for file_name in itertools.chain(
            _compiled_werks_dir().glob("werks"),  # pylint: disable=no-member
            _compiled_werks_dir().glob("werks-*")):  # pylint: disable=no-member
        werks.update(load_precompiled_werks_file(file_name))
    return werks


def load_precompiled_werks_file(path):
    with path.open() as fp:
        return {int(werk_id): werk for werk_id, werk in json.load(fp).iteritems()}


def load_raw_files(werks_dir):
    if werks_dir is None:
        werks_dir = Path(cmk.paths.share_dir) / "werks"
    werks = {}
    for file_name in werks_dir.glob("[0-9]*"):
        werk_id = int(file_name.name)
        try:
            werk = _load_werk(file_name)
            werk["id"] = werk_id
            werks[werk_id] = werk
        except Exception as e:
            raise MKGeneralException(_("Failed to load werk \"%s\": %s") % (werk_id, e))
    return werks


def _load_werk(path):
    werk = {
        "body": [],
    }
    in_header = True
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if in_header and not line:
                in_header = False
            elif in_header:
                key, text = line.split(":", 1)
                try:
                    value = int(text.strip())
                except ValueError:
                    value = text.strip()
                werk[key.lower()] = value
            else:
                werk["body"].append(line)

    werk.setdefault("compatible", "compat")
    werk.setdefault("edition", "cre")

    return werk


def write_precompiled_werks(path, werks):
    with path.open("wb") as fp:
        json.dump(werks, fp, check_circular=False)


# Writhe the given werks to a file object. This is used for creating a textual
# change log for the released versions and the announcement mails
def write_as_text(werks, f, write_version=True):
    version, component = None, None
    for werk in sort_by_version_and_component(werks.values()):
        if version != werk["version"]:
            if version is not None:
                f.write("\n\n")

            version, component = werk["version"], None

            if write_version:
                f.write("%s:\n" % werk["version"])

        if component != werk["component"]:
            if component is not None:
                f.write("\n")

            component = werk["component"]

            f.write("    %s:\n" % \
                werk_components().get(component, component).encode("utf-8"))

        write_werk_as_text(f, werk)


def write_werk_as_text(f, werk):
    prefix = ""
    if werk["class"] == "fix":
        prefix = " FIX:"
    elif werk["class"] == "security":
        prefix = " SEC:"

    if werk.get("description") and len(werk["description"]) > 3:
        omit = "..."
    else:
        omit = ""

    f.write("    * %04d%s %s%s\n" % (werk["id"], prefix, werk["title"].encode("utf-8"), omit))

    if werk["compatible"] == "incomp":
        f.write("            NOTE: Please refer to the migration notes!\n")


# sort by version and within one version by component
def sort_by_version_and_component(werks):
    return sorted(werks,
                  key=lambda w: (parse_check_mk_version(w["version"]),
                                 werk_components().get(w["component"], w["component"]),
                                 w["class"] != "fix",
                                 w["class"] != "sec",
                                 w["title"]),
                  reverse=True)


def sort_by_date(werks):
    return sorted(werks, key=lambda w: w["date"], reverse=True)


# Parses versions of Check_MK and converts them into comparable integers.
# This does not handle daily build numbers, only official release numbers.
# 1.2.4p1   -> 01020450001
# 1.2.4     -> 01020450000
# 1.2.4b1   -> 01020420100
# 1.2.3i1p1 -> 01020310101
# 1.2.3i1   -> 01020310100
# TODO: Copied from check_mk_base.py - find location for common code.
def parse_check_mk_version(v):
    def extract_number(s):
        number = ''
        for i, c in enumerate(s):
            try:
                int(c)
                number += c
            except ValueError:
                s = s[i:]
                return number and int(number) or 0, s
        return number and int(number) or 0, ''

    parts = v.split('.')
    while len(parts) < 3:
        parts.append("0")

    major, minor, rest = parts
    sub, rest = extract_number(rest)

    if not rest:
        val = 50000
    elif rest[0] == 'p':
        num, rest = extract_number(rest[1:])
        val = 50000 + num
    elif rest[0] == 'i':
        num, rest = extract_number(rest[1:])
        val = 10000 + num * 100

        if rest and rest[0] == 'p':
            num, rest = extract_number(rest[1:])
            val += num
    elif rest[0] == 'b':
        num, rest = extract_number(rest[1:])
        val = 20000 + num * 100

    return int('%02d%02d%02d%05d' % (int(major), int(minor), sub, val))