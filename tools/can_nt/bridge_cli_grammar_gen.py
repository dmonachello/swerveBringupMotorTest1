"""
NAME
    bridge_cli_grammar_gen.py - Generated Lark grammar.
"""

GRAMMAR = r'''
line: ws? command ws? 
command: common | exec | config | group | device | test 
common: "exit" | "end" | "help" | "ping" | "echo" ws ("on" | "off") | "quit" 
exec: show_exec | "configure" ws "terminal" | "connect" | "disconnect" 
show_exec: "show" ws show_target ( ws show_flags )? 
show_target: "status" | "groups" | "group" ws name | "devices" | "device" ws name | "device" ws "registry" ws name | "bindings" | "selected-device" | "runtime-state" | "config" | "config" ws "local-raw" | "profiles" | "profile" | "tests" | "test" ws name 
show_source: "robot" | "local" | "both" 
show_flags: show_flag ( ws show_flag )* 
show_flag: show_source | "--json" 
config: "group" ws name | "no" ws "group" ws name | "profile" ws name | "selected-device" ws name | "selected-mode" ws ("on" | "off") | "merge" ws "config" ws path | "import" ws "config" ws path | "export" ws "runtime-groups" ws path | "export" ws "cli-script" ws path | "save" ws "config" ws path | "save" ws "local-config" ws path | "save" ws "profiles" ws path | "save" ws "unified-config" ws path | "rename" ws "device" ws name ws name | "device" ws name | "device" ws name ws "set" ws field ws value_text | "validate" ws "config" ( ws path )? | "show" ws show_target ( ws show_flags )? | "write" ws "tests" ws path | "test" ws ("set" ws name | "create" ws name | "delete" ws name | name) 
group: "show" | "show" ws "members" | "show" ws "binding" | "show" ws show_target ( ws show_flags )? | "add" ws "device" ws name | "no" ws "device" ws name | "member" ws name ws ("enable" | "disable" | "toggle") | "bind" ws input ws "analog" | "bind" ws input ws ("hold" | "toggle" | "jog-forward" | "jog-reverse") ws value | "no" ws "bind" | "enable" | "disable" | "run" ws "test" ( ws name )? | "write" ws "tests" ws path 
device: "show" | "show" ws show_target ( ws show_flags )? | "set" ws field ws value_or_text | "no" ws field | "write" ws "tests" ws path 
test: "show" | "type" ws ("joystick" | "button" | "composite" | "deadbandSweep") | "device" ws "add" ws name | "no" ws "device" ws name | "inputSource" ws name | "deadband" ws number | "duty" ws number | "rotation" ws "limit" ws number | "rotation" ws ("encoderKey" | "encoderSource") ws name | "rotation" ws ("encoderMotorIndex" | "encoderCountsPerRev") ws number | "time" ws "timeout" ws number | "time" ws "onTimeout" ws name | "hold" ws "onRelease" ws name | "limitswitch" ws ("onHit" | "id") ws name | "deadbandSweep" ws ("startDuty" | "maxDuty" | "stepDuty" | "stepHoldSec" | "motionThresholdRot") ws number | "deadbandSweep" ws "requiredSamples" ws number | "deadbandSweep" ws ("encoderKey" | "encoderSource") ws name | "deadbandSweep" ws ("encoderMotorIndex" | "encoderCountsPerRev") ws number | "enabled" ws ("true" | "false" | "on" | "off") | "termination" ws "hold" | "termination" ws "time" ws number | "termination" ws "rotation" ws number | "termination" ws "limitswitch" ( ws name )? | "write" ws "tests" ws path 
value_or_text: number | value_text 
exec_line: ws? (common | exec) ws?
config_line: ws? (common | config) ws?
group_line: ws? (common | group) ws?
device_line: ws? (common | device) ws?
test_line: ws? (common | test) ws?
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
