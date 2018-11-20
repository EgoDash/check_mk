# Stubs for kubernetes.client.models.v1_pod_security_context (Python 2)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from typing import Any, Optional

class V1PodSecurityContext:
    swagger_types: Any = ...
    attribute_map: Any = ...
    discriminator: Any = ...
    fs_group: Any = ...
    run_as_group: Any = ...
    run_as_non_root: Any = ...
    run_as_user: Any = ...
    se_linux_options: Any = ...
    supplemental_groups: Any = ...
    sysctls: Any = ...
    def __init__(self, fs_group: Optional[Any] = ..., run_as_group: Optional[Any] = ..., run_as_non_root: Optional[Any] = ..., run_as_user: Optional[Any] = ..., se_linux_options: Optional[Any] = ..., supplemental_groups: Optional[Any] = ..., sysctls: Optional[Any] = ...) -> None: ...
    @property
    def fs_group(self): ...
    @fs_group.setter
    def fs_group(self, fs_group: Any) -> None: ...
    @property
    def run_as_group(self): ...
    @run_as_group.setter
    def run_as_group(self, run_as_group: Any) -> None: ...
    @property
    def run_as_non_root(self): ...
    @run_as_non_root.setter
    def run_as_non_root(self, run_as_non_root: Any) -> None: ...
    @property
    def run_as_user(self): ...
    @run_as_user.setter
    def run_as_user(self, run_as_user: Any) -> None: ...
    @property
    def se_linux_options(self): ...
    @se_linux_options.setter
    def se_linux_options(self, se_linux_options: Any) -> None: ...
    @property
    def supplemental_groups(self): ...
    @supplemental_groups.setter
    def supplemental_groups(self, supplemental_groups: Any) -> None: ...
    @property
    def sysctls(self): ...
    @sysctls.setter
    def sysctls(self, sysctls: Any) -> None: ...
    def to_dict(self): ...
    def to_str(self): ...
    def __eq__(self, other: Any): ...
    def __ne__(self, other: Any): ...