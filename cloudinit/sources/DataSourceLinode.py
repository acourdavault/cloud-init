# Author: Eric Benner <ebenner@linode.com>
#
# This file is part of cloud-init. See LICENSE file for license information.

# Linode Metadata API:
# https://www.linode.com/metadata/

from cloudinit import log as log
from cloudinit import sources
from cloudinit import util
from cloudinit import version

import cloudinit.sources.helpers.linode as linode

LOG = log.getLogger(__name__)
BUILTIN_DS_CONFIG = {
    'url': 'http://45.79.49.222',
    'retries': 30,
    'timeout': 2,
    'wait': 2,
    'user-agent': 'Cloud-Init/%s - OS: %s Variant: %s' %
                  (version.version_string(),
                   util.system_info()['system'],
                   util.system_info()['variant'])
}


class DataSourceLinode(sources.DataSource):

    dsname = 'Linode'

    def __init__(self, sys_cfg, distro, paths):
        super(DataSourceLinode, self).__init__(sys_cfg, distro, paths)
        self.ds_cfg = util.mergemanydict([
            util.get_cfg_by_path(sys_cfg, ["datasource", "Linode"], {}),
            BUILTIN_DS_CONFIG])

    # Initiate data and check if Linode
    def _get_data(self):
        LOG.debug("Detecting if machine is a Linode instance")
        if not linode.is_linode():
            LOG.debug("Machine is not a Linode instance")
            return False

        LOG.debug("Machine is a Linode instance")

        # Fetch metadata
        self.metadata = self.get_metadata()
        self.metadata['instance-id'] = self.metadata['instanceid']
        self.metadata['local-hostname'] = self.metadata['hostname']
        self.userdata_raw = self.metadata["user-data"]

        # Generate config and process data
        self.get_datasource_data(self.metadata)

        # Dump some data so diagnosing failures is manageable
        LOG.debug("Linode Vendor Config:")
        LOG.debug(util.json_dumps(self.metadata['vendor-data']))
        LOG.debug("SUBID: %s", self.metadata['instance-id'])
        LOG.debug("Hostname: %s", self.metadata['local-hostname'])
        if self.userdata_raw is not None:
            LOG.debug("User-Data:")
            LOG.debug(self.userdata_raw)

        return True

    # Process metadata
    def get_datasource_data(self, md):
        # Generate network config
        if "cloud_interfaces" in md:
            # In the future we will just drop pre-configured
            # network configs into the array. They need names though.
            self.netcfg = linode.add_interface_names(md['cloud_interfaces'])
        else:
            self.netcfg = linode.generate_network_config(md['interfaces'])

        # Grab vendordata
        self.vendordata_raw = md['vendor-data']

        # Default hostname is "guest" for whitelabel
        if self.metadata['local-hostname'] == "":
            self.metadata['local-hostname'] = "guest"

        self.userdata_raw = md["user-data"]
        if self.userdata_raw == "":
            self.userdata_raw = None

    # Get the metadata by flag
    def get_metadata(self):
        return linode.get_metadata(self.ds_cfg['url'],
                                  self.ds_cfg['timeout'],
                                  self.ds_cfg['retries'],
                                  self.ds_cfg['wait'],
                                  self.ds_cfg['user-agent'])

    # Compare subid as instance id
    def check_instance_id(self, sys_cfg):
        if not linode.is_linode():
            return False

        # Baremetal has no way to implement this in local
        if linode.is_baremetal():
            return False

        subid = linode.get_sysinfo()['subid']
        return sources.instance_id_matches_system_uuid(subid)

    # Currently unsupported
    @property
    def launch_index(self):
        return None

    @property
    def network_config(self):
        return self.netcfg


# Used to match classes to dependencies
datasources = [
    (DataSourceLinode, (sources.DEP_FILESYSTEM,sources.DEP_NETWORK )),
]


# Return a list of data sources that match this set of dependencies
def get_datasource_list(depends):
    return sources.list_from_depends(depends, datasources)


if __name__ == "__main__":
    import sys

    if not linode.is_linode():
        print("Machine is not a Linode instance")
        sys.exit(1)

    md = linode.get_metadata(BUILTIN_DS_CONFIG['url'],
                            BUILTIN_DS_CONFIG['timeout'],
                            BUILTIN_DS_CONFIG['retries'],
                            BUILTIN_DS_CONFIG['wait'],
                            BUILTIN_DS_CONFIG['user-agent'])
    config = md['vendor-data']
    sysinfo = linode.get_sysinfo()

    print(util.json_dumps(sysinfo))
    print(util.json_dumps(config))

# vi: ts=4 expandtab
