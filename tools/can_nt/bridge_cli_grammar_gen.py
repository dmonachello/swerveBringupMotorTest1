"""
NAME
    bridge_cli_grammar_gen.py - Generated Lark grammar.
"""

GRAMMAR = r'''
line: ws? command ws? 
command: common | exec | config | group | device 
common: "exit" | "end" | "help" | "ping" | "quit" 
exec: show_exec | "configure" ws "terminal" | "connect" | "disconnect" 
show_exec: "show" ws show_target ( ws show_flags )? 
show_target: "status" | "groups" | "group" ws name | "devices" | "device" ws name | "bindings" | "selected-device" | "runtime-state" | "config" 
show_source: "robot" | "local" | "both" 
show_flags: show_flag ( ws show_flag )* 
show_flag: show_source | "--json" 
config: "group" ws name | "no" ws "group" ws name | "selected-device" ws name | "selected-mode" ws ("on" | "off") | "merge" ws "config" ws path | "import" ws "config" ws path | "export" ws "runtime-groups" ws path | "export" ws "cli-script" ws path | "save" ws "config" ws path | "save" ws "local-config" ws path | "save" ws "profiles" ws path | "save" ws "unified-config" ws path | "rename" ws "device" ws name ws name | "device" ws name | "device" ws name ws "set" ws field ws value_text | "validate" ws "config" ( ws path )? | "show" ws show_target ( ws show_flags )? 
group: "show" | "show" ws "members" | "show" ws "binding" | "show" ws show_target ( ws show_flags )? | "add" ws "device" ws name | "no" ws "device" ws name | "member" ws name ws ("enable" | "disable" | "toggle") | "bind" ws input ws "analog" | "bind" ws input ws ("hold" | "toggle" | "jog-forward" | "jog-reverse") ws value | "no" ws "bind" | "enable" | "disable" | "run" ws "test" ( ws name )? 
device: "show" | "show" ws show_target ( ws show_flags )? | "set" ws field ws value_or_text | "no" ws field 
value_or_text: number | value_text 
exec_line: ws? (common | exec) ws?
config_line: ws? (common | config) ws?
group_line: ws? (common | group) ws?
device_line: ws? (common | device) ws?
TOKEN: /\"[^\"]*\"|[^\s]+/
NUMBER: /[+-]?\d+(\.\d+)?/
WS: /[ \t]+/
ws: WS
name: TOKEN
input: TOKEN
path: TOKEN
field: TOKEN
value: NUMBER
number: NUMBER
value_text: TOKEN (WS TOKEN)*
%import common.WS_INLINE
%ignore /\r?\n/

'''
