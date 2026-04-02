"""
NAME
    bridge_cli_constants_gen.py - Generated CLI parser constants.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class ParserSpec:
    bool_true: bool
    bool_false: bool
    count_zero: int
    count_one: int
    count_two: int
    count_three: int
    count_four: int
    count_five: int
    count_six: int
    idx_exec: int
    idx_config: int
    idx_group: int
    idx_device: int
    idx_test: int
    modes: tuple[str, ...]
    common: tuple[str, ...]
    show_flags: tuple[str, ...]
    show_source_robot: str
    show_source_local: str
    show_source_both: str
    show_targets: tuple[str, ...]
    show_target_config: str
    show_target_runtime_state: str
    show_target_tests: str
    show_target_test: str
    show_target_status: str
    show_target_groups: str
    show_target_devices: str
    show_target_bindings: str
    show_target_selected_device: str
    show_target_commands: str
    show_target_help: str
    show_target_sources: str
    show_target_device_usage: str
    show_target_device_group: str
    show_target_message_level: str
    bind_kinds: tuple[str, ...]
    cmd_connect: str
    cmd_disconnect: str
    cmd_configure: str
    cmd_cfg: str
    cmd_terminal: str
    cmd_show: str
    cmd_ls: str
    cmd_group: str
    cmd_no: str
    cmd_profile: str
    cmd_profiles: str
    cmd_prof: str
    cmd_selected_device: str
    cmd_selected_mode: str
    cmd_on: str
    cmd_off: str
    cmd_merge: str
    cmd_import: str
    cmd_config: str
    cmd_export: str
    cmd_export_runtime_groups: str
    cmd_export_cli_script: str
    cmd_save: str
    cmd_save_config: str
    cmd_save_local_config: str
    cmd_save_profiles: str
    cmd_save_unified: str
    cmd_savep: str
    cmd_push: str
    cmd_activate: str
    cmd_default: str
    cmd_rename: str
    cmd_device: str
    cmd_registry: str
    cmd_sources: str
    cmd_set: str
    cmd_write: str
    cmd_bindings: str
    cmd_can_mappings: str
    cmd_tests: str
    cmd_load: str
    cmd_create: str
    cmd_delete: str
    cmd_type: str
    cmd_input_source: str
    cmd_deadband: str
    cmd_duty: str
    cmd_termination: str
    cmd_limitswitch: str
    cmd_validate: str
    cmd_val: str
    cmd_add: str
    cmd_member: str
    cmd_enable: str
    cmd_disable: str
    cmd_toggle: str
    cmd_bind: str
    cmd_run: str
    cmd_test: str
    cmd_members: str
    cmd_binding: str
    cmd_show_all: str
    cmd_validate_all: str
    show_target_group: str
    show_target_device: str
    strict_default: bool
    allow_empty: bool
    disallow_empty: bool
    msg_unknown_mode_fmt: str
    msg_unknown_cmd_fmt: str
    msg_config_terminal: str
    msg_show_requires: str
    msg_unknown_show: str
    msg_show_name: str
    msg_show_too_many: str
    msg_too_many_fmt: str
    msg_group_name: str
    msg_no_group_name: str
    msg_profile_name: str
    msg_selected_device: str
    msg_selected_mode: str
    msg_selected_mode_value: str
    msg_merge_config: str
    msg_import_config: str
    msg_export_requires: str
    msg_export_target: str
    msg_save_requires: str
    msg_save_target: str
    msg_write_requires: str
    msg_rename_device: str
    msg_device_name: str
    msg_device_set: str
    msg_validate_config: str
    msg_add_device: str
    msg_no_device: str
    msg_member: str
    msg_member_action: str
    msg_bind: str
    msg_bind_kind: str
    msg_bind_value: str
    msg_no_bind: str
    msg_run_test: str
    msg_set: str
    msg_no: str
    msg_parse_error: str
    msg_mode_only_fmt: str
    msg_mode_name_exec: str
    msg_mode_name_config: str
    msg_mode_name_group: str
    msg_mode_name_device: str
    msg_mode_name_test: str
    label_connect: str
    label_configure: str
    label_group: str
    label_no_group: str
    label_selected_device: str
    label_selected_mode: str
    label_merge: str
    label_import: str
    label_export: str
    label_save: str
    label_rename: str
    label_device: str
    label_device_set: str
    label_device_delete: str
    mode_exec_cmds: tuple[str, ...]
    mode_config_cmds: tuple[str, ...]
    mode_group_cmds: tuple[str, ...]
    mode_device_cmds: tuple[str, ...]
    mode_test_cmds: tuple[str, ...]
    label_validate: str
    label_show_members: str
    label_add_device: str
    label_no_device: str
    label_member: str
    label_bind_analog: str
    label_bind: str
    label_no_bind: str
    label_enable: str
    label_run_test: str
    shlex_posix: bool
    empty_str: str
    space_str: str
    kind_common_exit: str
    kind_common_end: str
    kind_common_help: str
    kind_common_ping: str
    kind_exec_connect: str
    kind_exec_disconnect: str
    kind_exec_configure_terminal: str
    kind_show: str
    kind_config_group: str
    kind_config_no_group: str
    kind_config_no_device: str
    kind_config_profile: str
    kind_config_selected_device: str
    kind_config_selected_mode: str
    kind_config_merge: str
    kind_config_import: str
    kind_config_export: str
    kind_config_save: str
    kind_config_load: str
    kind_config_push: str
    kind_config_rename_device: str
    kind_config_device: str
    kind_config_device_set: str
    kind_config_validate: str
    kind_config_bindings: str
    kind_config_can_mappings: str
    kind_group_show: str
    kind_group_show_members: str
    kind_group_show_binding: str
    kind_group_add_device: str
    kind_group_no_device: str
    kind_group_member: str
    kind_group_bind: str
    kind_group_no_bind: str
    kind_group_enable: str
    kind_group_disable: str
    kind_group_run_test: str
    kind_device_show: str
    kind_device_set: str
    kind_device_no: str
    kind_device_delete: str

SPEC = ParserSpec(
    bool_true=True,
    bool_false=False,
    count_zero=0,
    count_one=1,
    count_two=2,
    count_three=3,
    count_four=4,
    count_five=5,
    count_six=6,
    idx_exec=0,
    idx_config=1,
    idx_group=2,
    idx_device=3,
    idx_test=4,
    modes=('exec', 'config', 'group', 'device', 'test'),
    common=('exit', 'end', 'help', 'ping', 'quit'),
    show_flags=('--json', '--pretty', 'robot', '--robot', 'local', '--local', 'both', '--both'),
    show_source_robot='robot',
    show_source_local='local',
    show_source_both='both',
    show_targets=('status', 'groups', 'group', 'devices', 'device', 'commands', 'help', 'version', 'device-usage', 'device-registry', 'bindings', 'selected-device', 'runtime-state', 'tests', 'test', 'config', 'sources', 'profiles', 'profile', 'message-level', 'workspace', 'session', 'controllers', 'device-group'),
    show_target_config='config',
    show_target_runtime_state='runtime-state',
    show_target_tests='tests',
    show_target_test='test',
    show_target_status='status',
    show_target_groups='groups',
    show_target_devices='devices',
    show_target_bindings='bindings',
    show_target_selected_device='selected-device',
    show_target_device_group='device-group',
    show_target_commands='commands',
    show_target_help='help',
    show_target_sources='sources',
    show_target_device_usage='device-usage',
    show_target_message_level='message-level',
    bind_kinds=('analog', 'hold', 'toggle', 'jog-forward', 'jog-reverse'),
    cmd_connect='connect',
    cmd_disconnect='disconnect',
    cmd_configure='configure',
    cmd_cfg='cfg',
    cmd_terminal='terminal',
    cmd_show='show',
    cmd_ls='ls',
    cmd_group='group',
    cmd_no='no',
    cmd_profile='profile',
    cmd_profiles='profiles',
    cmd_prof='prof',
    cmd_selected_device='selected-device',
    cmd_selected_mode='selected-mode',
    cmd_on='on',
    cmd_off='off',
    cmd_merge='merge',
    cmd_import='import',
    cmd_config='config',
    cmd_export='export',
    cmd_export_runtime_groups='runtime-groups',
    cmd_export_cli_script='cli-script',
    cmd_save='save',
    cmd_save_config='config',
    cmd_save_local_config='local-config',
    cmd_save_profiles='profiles',
    cmd_save_unified='unified-config',
    cmd_savep='savep',
    cmd_push='push',
    cmd_activate='--activate',
    cmd_default='default',
    cmd_rename='rename',
    cmd_device='device',
    cmd_registry='registry',
    cmd_sources='sources',
    cmd_set='set',
    cmd_write='write',
    cmd_bindings='bindings',
    cmd_can_mappings='can-mappings',
    cmd_tests='tests',
    cmd_load='load',
    cmd_create='create',
    cmd_delete='delete',
    cmd_type='type',
    cmd_input_source='inputSource',
    cmd_deadband='deadband',
    cmd_duty='duty',
    cmd_termination='termination',
    cmd_limitswitch='limitswitch',
    cmd_validate='validate',
    cmd_val='val',
    cmd_add='add',
    cmd_member='member',
    cmd_enable='enable',
    cmd_disable='disable',
    cmd_toggle='toggle',
    cmd_bind='bind',
    cmd_run='run',
    cmd_test='test',
    cmd_members='members',
    cmd_binding='binding',
    cmd_show_all='show-all',
    cmd_validate_all='--all',
    show_target_group='group',
    show_target_device='device',
    strict_default=False,
    allow_empty=True,
    disallow_empty=False,
    msg_unknown_mode_fmt="unknown mode '%s'",
    msg_unknown_cmd_fmt="unknown command '%s'",
    msg_config_terminal="configure requires 'terminal'",
    msg_show_requires='show requires a target',
    msg_unknown_show='unknown show target',
    msg_show_name='show %s requires a name',
    msg_show_too_many='too many arguments for show',
    msg_too_many_fmt='too many arguments for %s',
    msg_group_name='group requires group name',
    msg_no_group_name='no group requires group name',
    msg_profile_name='profile requires profile name',
    msg_selected_device='selected-device requires device',
    msg_selected_mode='selected-mode requires on/off',
    msg_selected_mode_value='selected-mode requires on/off',
    msg_merge_config="merge requires 'config <path>'",
    msg_import_config="import requires 'config <path>'",
    msg_export_requires='export requires target and path',
    msg_export_target='export requires runtime-groups or cli-script',
    msg_save_requires='save requires target and path (or sources/all)',
    msg_save_target='save requires all/config/local-config/profiles/unified-config/sources',
    msg_write_requires='write requires tests <path>',
    msg_rename_device="rename requires 'device <old> <new>'",
    msg_device_name='device requires device label',
    msg_device_set='device <device> set <field> <value>',
    msg_validate_config="validate requires 'config [path]'",
    msg_add_device='add device requires device label',
    msg_no_device='no device requires device label',
    msg_member='member requires device and action',
    msg_member_action='member requires enable/disable/toggle',
    msg_bind='bind requires input and kind',
    msg_bind_kind='bind requires analog/hold/toggle/jog-forward/jog-reverse',
    msg_bind_value='bind requires value',
    msg_no_bind='no bind',
    msg_run_test="run requires 'test [name]'",
    msg_set='set requires field and value',
    msg_no='no requires field',
    msg_parse_error='invalid command syntax',
    msg_mode_only_fmt='%s is only valid in %s mode',
    msg_mode_name_exec='exec',
    msg_mode_name_config='config',
    msg_mode_name_group='group',
    msg_mode_name_device='device',
    msg_mode_name_test='test',
    label_connect='connect/disconnect',
    label_configure='configure terminal',
    label_group='group',
    label_no_group='no group',
    label_selected_device='selected-device',
    label_selected_mode='selected-mode',
    label_merge='merge config',
    label_import='import config',
    label_export='export',
    label_save='save',
    label_rename='rename device',
    label_device='device',
    label_device_set='device set',
    label_device_delete='delete',
    mode_exec_cmds=('cfg', 'configure', 'connect', 'diagnose', 'disconnect', 'ls', 'prof', 'profile', 'show'),
    mode_config_cmds=('bindings', 'can-mappings', 'config', 'device', 'diagnose', 'export', 'group', 'import', 'load', 'ls', 'merge', 'no', 'prof', 'profile', 'profiles', 'rename', 'save', 'savep', 'selected-device', 'selected-mode', 'show', 'test', 'tests', 'val', 'validate'),
    mode_group_cmds=('add', 'bind', 'disable', 'enable', 'ls', 'member', 'no', 'run', 'show'),
    mode_device_cmds=('delete', 'ls', 'no', 'set', 'show'),
    mode_test_cmds=('action', 'brightness', 'color', 'deadband', 'deadbandsweep', 'device', 'duration', 'duty', 'enabled', 'hold', 'inputsource', 'limitswitch', 'ls', 'no', 'pattern', 'rotation', 'show', 'termination', 'time', 'type'),
    label_validate='validate config',
    label_show_members='show members/binding',
    label_add_device='add device',
    label_no_device='no device',
    label_member='member',
    label_bind_analog='bind analog',
    label_bind='bind',
    label_no_bind='no bind',
    label_enable='enable/disable',
    label_run_test='run test',
    shlex_posix=True,
    empty_str="",
    space_str=" ",
    kind_common_exit='common_exit',
    kind_common_end='common_end',
    kind_common_help='common_help',
    kind_common_ping='common_ping',
    kind_exec_connect='exec_connect',
    kind_exec_disconnect='exec_disconnect',
    kind_exec_configure_terminal='exec_configure_terminal',
    kind_show='show',
    kind_config_group='config_group',
    kind_config_no_group='config_no_group',
    kind_config_no_device='config_no_device',
    kind_config_profile='config_profile',
    kind_config_selected_device='config_selected_device',
    kind_config_selected_mode='config_selected_mode',
    kind_config_merge='config_merge',
    kind_config_import='config_import',
    kind_config_export='config_export',
    kind_config_save='config_save',
    kind_config_load='config_load',
    kind_config_push='config_push',
    kind_config_rename_device='config_rename_device',
    kind_config_device='config_device',
    kind_config_device_set='config_device_set',
    kind_config_validate='config_validate',
    kind_config_bindings='config_bindings',
    kind_config_can_mappings='config_can_mappings',
    kind_group_show='group_show',
    kind_group_show_members='group_show_members',
    kind_group_show_binding='group_show_binding',
    kind_group_add_device='group_add_device',
    kind_group_no_device='group_no_device',
    kind_group_member='group_member',
    kind_group_bind='group_bind',
    kind_group_no_bind='group_no_bind',
    kind_group_enable='group_enable',
    kind_group_disable='group_disable',
    kind_group_run_test='group_run_test',
    kind_device_show='device_show',
    kind_device_set='device_set',
    kind_device_no='device_no',
    kind_device_delete='device_delete',
)
