"""
NAME
    bridge_cli_grammar_gen.py - Generated Lark grammar.
"""

GRAMMAR = r'''
line: ws? command ws? ( "?" )? 
command: common | exec | config | group | device | test 
common: "exit" | "end" | "help" ( ws name ( ws name )* )? | "ping" | "echo" ws ("on" | "off") | "messages" ws ("beginner" | "medium" | "expert") | "debug" ws "grammar" ( ws "--json" )? ( ws "--dot" ws path )? | "debug" ws "grammar" ( ws "--dot" ws path )? ( ws "--json" )? | "quit" 
exec: show_exec | "configure" ws "terminal" | "cfg" | "connect" | "disconnect" | "add" ws ("next" | "all") | "tests" ws ("select" ws name | "toggle" | "run" | "run-all") | "profile" ws "device" ws "show-all" ws name | "prof" ws "device" ws "show-all" ws name | diagnose 
show_exec: ("show" | "ls") ws show_target ( ws show_flags )? 
show_target: "status" | "groups" | "group" ws name | "devices" | "device" ws name | "device" ws "registry" ws name | "commands" | "help" | "controllers" | "version" | "sources" | "controllers" | "version" | "sources" | "bindings" | "can-mappings" ( ws ("manufacturers" | "device-types" | "device-type") )? | "selected-device" | "runtime-state" | "config" | "config" ws "local-raw" | "config" ws "dirty" | "profiles" | "profile" ( ws name )? | "tests" | "test" ws name | "device-group" ws name | "device-usage" ws name | "message-level" | "workspace" | "session" 
show_source: "robot" | "local" | "both" 
show_flags: show_flag ( ws show_flag )* 
show_flag: show_source | "--json" | "--pretty" | "--all" 
config: "group" ws name | "no" ws "group" ws name | "no" ws "device" ws name | "profile" ws name | "profile" ws "default" ws name | "profile" ws "create" ws name | "profile" ws "delete" ws name | "profile" ws "export" ws name ws path | "profile" ws "device" ws "delete" ws name | "profile" ws "device" ws "show-all" ws name | "prof" ws name | "prof" ws "default" ws name | "prof" ws "create" ws name | "prof" ws "delete" ws name | "prof" ws "export" ws name ws path | "prof" ws "device" ws "delete" ws name | "prof" ws "device" ws "show-all" ws name | "selected-device" ws name | "selected-mode" ws ("on" | "off") | "merge" ws "config" ws path | "import" ws "config" ws path | "export" ws "runtime-groups" ws path | "export" ws "cli-script" ws path | "save" ws "tests" ws path ( ws "--force" )? | "save" ws "config" ws path ( ws "--force" )? | "save" ws "local-config" ws path ( ws "--force" )? | "save" ws "profiles" ( ws path )? ( ws "--force" )? | "save" ws "unified-config" ws path ( ws "--force" )? | "save" ws "all" ( ws "--prompt" )? ( ws "--force" )? | "save" ws "sources" ( ws "--force" )? | "save" ws "all" ( ws "--prompt" )? ( ws "--force" )? | "save" ws "sources" ( ws "--force" )? | "savep" ws path | "load" ws "sources" | "write" ws "tests" ws path | "rename" ws "device" ws name ws name | "rename" ws name ws name | "device" ws name | "device" ws name ws "set" ws device_field ws value_or_text | ("validate" | "val") ws "all" | ("validate" | "val") ws "config" ( ws path )? ( ws "--all" )? | ("validate" | "val") ws "file" ws path ( ws "--repair" )? | ("validate" | "val") ws "profiles" ( ws ("robot" | "local") )? ( ws "--active" )? | ("validate" | "val") ws "tests" ( ws "--active-set" )? | ("validate" | "val") ws "bindings" ( ws path )? | ("validate" | "val") ws "can-mappings" ( ws path )? | ("validate" | "val") ws "script" ws path | "recover" ws ("list" | "last-good" | "from" ws name) | "profiles" ws "init" | "profiles" ws "activate" ws name | "profiles" ws "export" ws path | "profiles" ws "push" ws path ( ws "--activate" ws name )? | "config" ws "push" ws path ( ws "--activate" ws name )? | "add" ws ("next" | "all") | ("show" | "ls") ws show_target ( ws show_flags )? | diagnose | "bindings" ( ws bindings_args )? | "can-mappings" ( ws mappings_args )? | "tests" ( ws tests_args )? | "test" ws ("set" ws name | "create" ws name | "delete" ws name | name) 
diagnose: "diagnose" ws name ws name 
bindings_args: ("show" | "ls") ( ws ("controllers" | "bindings" | "axes") )? ( ws show_flags )? | "controller" ws ("add" ws name ws name ws number | "set" ws name ws field ws value_text | "rename" ws name ws name | "list" | "no" ws name) | "binding" ws ("add" ws name ws name ws name ws name ws name | "set" ws number ws field ws value_text | "delete" ws number) | "axis" ws ("add" ws name ws name ws name ws "invert" ws ("on" | "off") ws "deadband" ws number | "set" ws number ws field ws value_text | "delete" ws number) | "load" ws path | "save" ws path | "validate" ( ws path )? 
mappings_args: ("show" | "ls") ( ws ("manufacturers" | "device-types" | "device-type") )? ( ws show_flags )? | "manufacturer" ws ("set" ws number ws value_text | "delete" ws number | "no" ws number) | "device-type" ws ("set" ws number ws value_text | "delete" ws number | "no" ws number) | "load" ws path | "save" ws path | "validate" ( ws path )? 
tests_args: "templates" | "clear" | "select" ws name | "toggle" | "run" | "run-all" 
group: ("show" | "ls") | ("show" | "ls") ws "members" | ("show" | "ls") ws "binding" | ("show" | "ls") ws show_target ( ws show_flags )? | "add" ws "device" ws name | "no" ws "device" ws name | "member" ws name ws ("enable" | "disable" | "toggle") | "bind" ws input ws "analog" | "bind" ws input ws ("hold" | "toggle" | "jog-forward" | "jog-reverse") ws value | "no" ws "bind" | "enable" | "disable" | "run" ws "test" ( ws name )? 
device: ("show" | "ls") | ("show" | "ls") ws show_target ( ws show_flags )? | "set" ws device_field ws value_or_text | "no" ws device_field | "delete" 
test: ("show" | "ls") | "type" ws ("joystick" | "button" | "composite" | "deadbandsweep" | "deadbandSweep" | "deviceaction" | "deviceAction") | "device" ws "add" ws name | "no" ws "device" ws name | "inputsource" ws name | "deadband" ws number | "duty" ws number | "action" ws name | "color" ws name | "pattern" ws name | "brightness" ws number | "duration" ws number | "rotation" ws "limit" ws number | "rotation" ws ("encoderKey" | "encoderSource") ws name | "rotation" ws ("encoderMotorIndex" | "encoderCountsPerRev") ws number | "time" ws "timeout" ws number | "time" ws "onTimeout" ws name | "hold" ws "onRelease" ws name | "limitswitch" ws ("onHit" | "id") ws name | "deadbandsweep" ws ("startDuty" | "maxDuty" | "stepDuty" | "stepHoldSec" | "motionThresholdRot") ws number | "deadbandsweep" ws "requiredSamples" ws number | "deadbandsweep" ws ("encoderKey" | "encoderSource") ws name | "deadbandsweep" ws ("encoderMotorIndex" | "encoderCountsPerRev") ws number | "enabled" ws ("true" | "false" | "on" | "off") | "termination" ws "hold" | "termination" ws "time" ws number | "termination" ws "rotation" ws number | "termination" ws "limitswitch" ( ws name )? 
value_or_text: number | value_text 
device_field: "interface" | "manufacturer" | "deviceType" | "id" | "model" | "type" | "dio" | "invert" | "pwm" | "analog" | "attachments" | "terminator" | "vendor" | "role" | "notes" | "tags" | "limits" 
exec_line: ws? (common | exec) ws?
config_line: ws? (common | config) ws?
group_line: ws? (common | group) ws?
device_line: ws? (common | device) ws?
test_line: ws? (common | test) ws?
TOKEN: /\"[^\"]*\"|[^\s]+/
NUMBER: /[+-]?\d+(\.\d+)?/
WS: /[ \t]+/
ws: WS
name: TOKEN | "default"
input: TOKEN
path: TOKEN
field: TOKEN | "type" | "invert"
value: NUMBER
number: NUMBER
value_text: (TOKEN | "true" | "false" | "on" | "off" | "default") (WS (TOKEN | "true" | "false" | "on" | "off" | "default"))*
%import common.WS_INLINE
%ignore /\r?\n/

'''
