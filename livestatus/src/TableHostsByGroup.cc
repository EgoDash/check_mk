// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableHostsByGroup.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "TableHostGroups.h"
#include "TableHosts.h"
#include "auth.h"
#include "nagios.h"

extern host *host_list;
extern hostgroup *hostgroup_list;

namespace {
struct hostbygroup {
    host _host;
    hostgroup *_hostgroup;
};
}  // namespace

TableHostsByGroup::TableHostsByGroup(MonitoringCore *mc) : Table(mc) {
    TableHosts::addColumns(this, mc, "", -1, -1);
    TableHostGroups::addColumns(this, "hostgroup_",
                                DANGEROUS_OFFSETOF(hostbygroup, _hostgroup));
}

std::string TableHostsByGroup::name() const { return "hostsbygroup"; }

std::string TableHostsByGroup::namePrefix() const { return "host_"; }

void TableHostsByGroup::answerQuery(Query *query) {
    // When groupAuthorization() is set to AuthorizationKind::strict we need to
    // pre-check if every host of this group is visible to the _auth_user
    bool requires_precheck =
        query->authUser() != nullptr &&
        core()->groupAuthorization() == AuthorizationKind::strict;

    for (hostgroup *hg = hostgroup_list; hg != nullptr; hg = hg->next) {
        bool show_host_group = true;
        if (requires_precheck) {
            for (hostsmember *m = hg->members; m != nullptr; m = m->next) {
                if (!is_authorized_for(core(), query->authUser(), m->host_ptr,
                                       nullptr)) {
                    show_host_group = false;
                    break;
                }
            }
        }

        if (show_host_group) {
            for (hostsmember *m = hg->members; m != nullptr; m = m->next) {
                hostbygroup hbg = {*m->host_ptr, hg};
                if (!query->processDataset(Row(&hbg))) {
                    break;
                }
            }
        }
    }
}

bool TableHostsByGroup::isAuthorized(Row row, const contact *ctc) const {
    return is_authorized_for(core(), ctc, &rowData<hostbygroup>(row)->_host,
                             nullptr);
}

Row TableHostsByGroup::findObject(const std::string &objectspec) const {
    return Row(find_host(const_cast<char *>(objectspec.c_str())));
}
