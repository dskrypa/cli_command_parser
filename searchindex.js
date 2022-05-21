Search.setIndex({docnames:["advanced","api","api/cli_command_parser.actions","api/cli_command_parser.command_parameters","api/cli_command_parser.commands","api/cli_command_parser.config","api/cli_command_parser.context","api/cli_command_parser.core","api/cli_command_parser.error_handling","api/cli_command_parser.exceptions","api/cli_command_parser.formatting","api/cli_command_parser.nargs","api/cli_command_parser.parameters","api/cli_command_parser.parser","api/cli_command_parser.testing","api/cli_command_parser.utils","basic","commands","index","parameters"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":5,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.intersphinx":1,"sphinx.ext.viewcode":1,sphinx:56},filenames:["advanced.rst","api.rst","api/cli_command_parser.actions.rst","api/cli_command_parser.command_parameters.rst","api/cli_command_parser.commands.rst","api/cli_command_parser.config.rst","api/cli_command_parser.context.rst","api/cli_command_parser.core.rst","api/cli_command_parser.error_handling.rst","api/cli_command_parser.exceptions.rst","api/cli_command_parser.formatting.rst","api/cli_command_parser.nargs.rst","api/cli_command_parser.parameters.rst","api/cli_command_parser.parser.rst","api/cli_command_parser.testing.rst","api/cli_command_parser.utils.rst","basic.rst","commands.rst","index.rst","parameters.rst"],objects:{"cli_command_parser.actions":[[2,1,1,"","help_action"]],"cli_command_parser.command_parameters":[[3,2,1,"","CommandParameters"]],"cli_command_parser.command_parameters.CommandParameters":[[3,3,1,"","__init__"],[3,4,1,"","action"],[3,4,1,"","action_flags"],[3,4,1,"","combo_option_map"],[3,4,1,"","command"],[3,4,1,"","command_parent"],[3,3,1,"","find_nested_option_that_accepts_values"],[3,3,1,"","find_nested_pass_thru"],[3,3,1,"","find_option_that_accepts_values"],[3,3,1,"","get_option_param_value_pairs"],[3,4,1,"","groups"],[3,3,1,"","long_option_to_param_value_pair"],[3,3,1,"","missing"],[3,4,1,"","option_map"],[3,4,1,"","options"],[3,4,1,"","parent"],[3,5,1,"","pass_thru"],[3,4,1,"","positionals"],[3,3,1,"","short_option_to_param_value_pairs"],[3,4,1,"","sub_command"]],"cli_command_parser.commands":[[4,2,1,"","Command"],[4,1,1,"","main"]],"cli_command_parser.commands.Command":[[4,3,1,"","__call__"],[4,3,1,"","__new__"],[4,3,1,"","_after_main_"],[4,3,1,"","_before_main_"],[4,4,1,"","ctx"],[4,3,1,"","main"],[4,3,1,"","parse"],[4,3,1,"","parse_and_run"]],"cli_command_parser.commands.Command.__call__.params":[[4,6,1,"","args"],[4,6,1,"","kwargs"]],"cli_command_parser.commands.Command._after_main_.params":[[4,6,1,"","args"],[4,6,1,"","kwargs"]],"cli_command_parser.commands.Command._before_main_.params":[[4,6,1,"","args"],[4,6,1,"","kwargs"]],"cli_command_parser.commands.Command.main.params":[[4,6,1,"","args"],[4,6,1,"","kwargs"]],"cli_command_parser.commands.Command.parse.params":[[4,6,1,"","argv"]],"cli_command_parser.commands.Command.parse_and_run.params":[[4,6,1,"","args"],[4,6,1,"","argv"],[4,6,1,"","kwargs"]],"cli_command_parser.config":[[5,2,1,"","CommandConfig"]],"cli_command_parser.config.CommandConfig":[[5,3,1,"","__init__"],[5,4,1,"","action_after_action_flags"],[5,4,1,"","add_help"],[5,4,1,"","allow_missing"],[5,4,1,"","always_run_after_main"],[5,3,1,"","as_dict"],[5,4,1,"","error_handler"],[5,4,1,"","ignore_unknown"],[5,4,1,"","multiple_action_flags"]],"cli_command_parser.context":[[6,2,1,"","Context"],[6,1,1,"","get_current_context"]],"cli_command_parser.context.Context":[[6,3,1,"","__init__"],[6,4,1,"","action_after_action_flags"],[6,5,1,"","after_main_actions"],[6,4,1,"","allow_missing"],[6,4,1,"","always_run_after_main"],[6,5,1,"","before_main_actions"],[6,4,1,"","error_handler"],[6,3,1,"","get_error_handler"],[6,3,1,"","get_parsed"],[6,3,1,"","get_parsing_value"],[6,4,1,"","ignore_unknown"],[6,4,1,"","multiple_action_flags"],[6,3,1,"","num_provided"],[6,5,1,"","params"],[6,5,1,"","parsed_action_flags"],[6,3,1,"","record_action"],[6,3,1,"","set_parsing_value"]],"cli_command_parser.context.get_current_context.params":[[6,6,1,"","silent"]],"cli_command_parser.core":[[7,2,1,"","CommandMeta"],[7,1,1,"","get_config"],[7,1,1,"","get_params"],[7,1,1,"","get_parent"],[7,1,1,"","get_top_level_commands"]],"cli_command_parser.core.CommandMeta":[[7,3,1,"","__new__"],[7,3,1,"","config"],[7,3,1,"","meta"],[7,3,1,"","params"],[7,3,1,"","parent"]],"cli_command_parser.core.CommandMeta.__new__.params":[[7,6,1,"","action_after_action_flags"],[7,6,1,"","add_help"],[7,6,1,"","allow_missing"],[7,6,1,"","always_run_after_main"],[7,6,1,"","choice"],[7,6,1,"","description"],[7,6,1,"","epilog"],[7,6,1,"","error_handler"],[7,6,1,"","help"],[7,6,1,"","ignore_unknown"],[7,6,1,"","multiple_action_flags"],[7,6,1,"","prog"],[7,6,1,"","usage"]],"cli_command_parser.error_handling":[[8,2,1,"","ErrorHandler"],[8,2,1,"","NullErrorHandler"]],"cli_command_parser.error_handling.ErrorHandler":[[8,3,1,"","__call__"],[8,3,1,"","__init__"],[8,3,1,"","cls_handler"],[8,3,1,"","copy"],[8,3,1,"","get_handler"],[8,3,1,"","register"],[8,3,1,"","unregister"]],"cli_command_parser.exceptions":[[9,7,1,"","BadArgument"],[9,7,1,"","CommandDefinitionError"],[9,7,1,"","CommandParserException"],[9,7,1,"","InvalidChoice"],[9,7,1,"","MissingArgument"],[9,7,1,"","NoActiveContext"],[9,7,1,"","NoSuchOption"],[9,7,1,"","ParamConflict"],[9,7,1,"","ParamUsageError"],[9,7,1,"","ParameterDefinitionError"],[9,7,1,"","ParamsMissing"],[9,7,1,"","ParserExit"],[9,7,1,"","UsageError"]],"cli_command_parser.exceptions.CommandParserException":[[9,4,1,"","code"],[9,3,1,"","exit"],[9,3,1,"","show"]],"cli_command_parser.exceptions.InvalidChoice":[[9,3,1,"","__init__"]],"cli_command_parser.exceptions.MissingArgument":[[9,4,1,"","message"]],"cli_command_parser.exceptions.ParamConflict":[[9,3,1,"","__init__"],[9,4,1,"","message"]],"cli_command_parser.exceptions.ParamUsageError":[[9,3,1,"","__init__"],[9,4,1,"","message"]],"cli_command_parser.exceptions.ParamsMissing":[[9,3,1,"","__init__"],[9,4,1,"","message"]],"cli_command_parser.exceptions.ParserExit":[[9,3,1,"","__init__"]],"cli_command_parser.formatting":[[10,2,1,"","HelpEntryFormatter"],[10,2,1,"","HelpFormatter"]],"cli_command_parser.formatting.HelpEntryFormatter":[[10,3,1,"","__call__"],[10,3,1,"","__init__"],[10,3,1,"","process_description"],[10,3,1,"","process_usage"]],"cli_command_parser.formatting.HelpFormatter":[[10,3,1,"","__init__"],[10,3,1,"","format_help"],[10,3,1,"","format_usage"],[10,3,1,"","maybe_add_group"],[10,3,1,"","maybe_add_param"]],"cli_command_parser.nargs":[[11,2,1,"","Nargs"]],"cli_command_parser.nargs.Nargs":[[11,3,1,"","__init__"],[11,3,1,"","satisfied"]],"cli_command_parser.parameters":[[12,2,1,"","Action"],[12,2,1,"","ActionFlag"],[12,2,1,"","BaseOption"],[12,2,1,"","BasePositional"],[12,2,1,"","Counter"],[12,2,1,"","Flag"],[12,2,1,"","Option"],[12,2,1,"","ParamGroup"],[12,2,1,"","Parameter"],[12,2,1,"","PassThru"],[12,2,1,"","Positional"],[12,2,1,"","SubCommand"],[12,4,1,"","action_flag"],[12,8,1,"","after_main"],[12,8,1,"","before_main"]],"cli_command_parser.parameters.Action":[[12,3,1,"","__call__"],[12,3,1,"","register"],[12,3,1,"","register_action"]],"cli_command_parser.parameters.Action.__call__.params":[[12,6,1,"","choice"],[12,6,1,"","default"],[12,6,1,"","help"],[12,6,1,"","method_or_choice"]],"cli_command_parser.parameters.Action.register.params":[[12,6,1,"","choice"],[12,6,1,"","default"],[12,6,1,"","help"],[12,6,1,"","method_or_choice"]],"cli_command_parser.parameters.ActionFlag":[[12,3,1,"","__call__"],[12,3,1,"","__init__"],[12,5,1,"","func"],[12,3,1,"","result"]],"cli_command_parser.parameters.ActionFlag.params":[[12,6,1,"","before_main"],[12,6,1,"","func"],[12,6,1,"","kwargs"],[12,6,1,"","option_strs"],[12,6,1,"","order"]],"cli_command_parser.parameters.BaseOption":[[12,3,1,"","__init__"],[12,3,1,"","format_basic_usage"],[12,3,1,"","format_usage"],[12,5,1,"","long_opts"],[12,4,1,"","short_combinable"],[12,5,1,"","short_opts"]],"cli_command_parser.parameters.BaseOption.params":[[12,6,1,"","action"],[12,6,1,"","kwargs"],[12,6,1,"","option_strs"]],"cli_command_parser.parameters.BasePositional":[[12,3,1,"","__init__"],[12,3,1,"","format_basic_usage"],[12,3,1,"","format_usage"]],"cli_command_parser.parameters.BasePositional.params":[[12,6,1,"","action"],[12,6,1,"","kwargs"]],"cli_command_parser.parameters.Counter":[[12,3,1,"","__init__"],[12,4,1,"","accepts_none"],[12,4,1,"","accepts_values"],[12,3,1,"","append"],[12,4,1,"","nargs"],[12,3,1,"","prepare_value"],[12,3,1,"","result"],[12,3,1,"","result_value"],[12,4,1,"","type"],[12,3,1,"","validate"]],"cli_command_parser.parameters.Counter.params":[[12,6,1,"","action"],[12,6,1,"","const"],[12,6,1,"","default"],[12,6,1,"","kwargs"],[12,6,1,"","option_strs"]],"cli_command_parser.parameters.Flag":[[12,3,1,"","__init__"],[12,4,1,"","accepts_none"],[12,4,1,"","accepts_values"],[12,3,1,"","append_const"],[12,4,1,"","nargs"],[12,3,1,"","result"],[12,3,1,"","result_value"],[12,3,1,"","store_const"],[12,3,1,"","would_accept"]],"cli_command_parser.parameters.Flag.params":[[12,6,1,"","action"],[12,6,1,"","const"],[12,6,1,"","default"],[12,6,1,"","kwargs"],[12,6,1,"","option_strs"]],"cli_command_parser.parameters.Option":[[12,3,1,"","__init__"],[12,3,1,"","append"],[12,3,1,"","store"]],"cli_command_parser.parameters.Option.params":[[12,6,1,"","action"],[12,6,1,"","default"],[12,6,1,"","kwargs"],[12,6,1,"","nargs"],[12,6,1,"","option_strs"],[12,6,1,"","required"],[12,6,1,"","type"]],"cli_command_parser.parameters.ParamGroup":[[12,3,1,"","__init__"],[12,3,1,"","active_group"],[12,3,1,"","add"],[12,5,1,"","contains_positional"],[12,4,1,"","description"],[12,3,1,"","format_description"],[12,3,1,"","format_help"],[12,3,1,"","format_usage"],[12,4,1,"","members"],[12,4,1,"","mutually_dependent"],[12,4,1,"","mutually_exclusive"],[12,3,1,"","register"],[12,3,1,"","register_all"],[12,5,1,"","show_in_help"],[12,3,1,"","validate"]],"cli_command_parser.parameters.ParamGroup.format_help.params":[[12,6,1,"","add_default"],[12,6,1,"","clean"],[12,6,1,"","group_type"],[12,6,1,"","width"]],"cli_command_parser.parameters.ParamGroup.params":[[12,6,1,"","description"],[12,6,1,"","hide"],[12,6,1,"","mutually_dependent"],[12,6,1,"","mutually_exclusive"],[12,6,1,"","name"],[12,6,1,"","required"]],"cli_command_parser.parameters.Parameter":[[12,3,1,"","__init__"],[12,3,1,"","__init_subclass__"],[12,4,1,"","accepts_none"],[12,4,1,"","accepts_values"],[12,4,1,"","choices"],[12,3,1,"","format_help"],[12,3,1,"","format_usage"],[12,3,1,"","is_valid_arg"],[12,4,1,"","metavar"],[12,4,1,"","nargs"],[12,3,1,"","prepare_value"],[12,3,1,"","result"],[12,3,1,"","result_value"],[12,5,1,"","show_in_help"],[12,3,1,"","take_action"],[12,4,1,"","type"],[12,5,1,"","usage_metavar"],[12,3,1,"","validate"],[12,3,1,"","would_accept"]],"cli_command_parser.parameters.Parameter.__init_subclass__.params":[[12,6,1,"","accepts_none"],[12,6,1,"","accepts_values"],[12,6,1,"","repr_attrs"]],"cli_command_parser.parameters.Parameter.params":[[12,6,1,"","action"],[12,6,1,"","choices"],[12,6,1,"","default"],[12,6,1,"","help"],[12,6,1,"","hide"],[12,6,1,"","metavar"],[12,6,1,"","name"],[12,6,1,"","required"]],"cli_command_parser.parameters.PassThru":[[12,3,1,"","__init__"],[12,3,1,"","format_basic_usage"],[12,4,1,"","nargs"],[12,3,1,"","store_all"],[12,3,1,"","take_action"]],"cli_command_parser.parameters.PassThru.params":[[12,6,1,"","action"],[12,6,1,"","kwargs"]],"cli_command_parser.parameters.Positional":[[12,3,1,"","__init__"],[12,3,1,"","append"],[12,3,1,"","store"]],"cli_command_parser.parameters.Positional.params":[[12,6,1,"","action"],[12,6,1,"","default"],[12,6,1,"","kwargs"],[12,6,1,"","nargs"],[12,6,1,"","type"]],"cli_command_parser.parameters.SubCommand":[[12,3,1,"","__init__"],[12,3,1,"","register"],[12,3,1,"","register_command"]],"cli_command_parser.parameters.SubCommand.params":[[12,6,1,"","args"],[12,6,1,"","kwargs"],[12,6,1,"","required"]],"cli_command_parser.parameters.SubCommand.register.params":[[12,6,1,"","choice"],[12,6,1,"","command_or_choice"],[12,6,1,"","help"]],"cli_command_parser.parser":[[13,2,1,"","CommandParser"]],"cli_command_parser.parser.CommandParser":[[13,3,1,"","__init__"],[13,3,1,"","consume_values"],[13,3,1,"","handle_long"],[13,3,1,"","handle_pass_thru"],[13,3,1,"","handle_positional"],[13,3,1,"","handle_short"],[13,3,1,"","parse_args"]],"cli_command_parser.testing":[[14,2,1,"","ParserTest"]],"cli_command_parser.testing.ParserTest":[[14,3,1,"","assert_call_fails"],[14,3,1,"","assert_call_fails_cases"],[14,3,1,"","assert_parse_fails"],[14,3,1,"","assert_parse_fails_cases"],[14,3,1,"","assert_parse_results"],[14,3,1,"","assert_parse_results_cases"]],"cli_command_parser.utils":[[15,2,1,"","ProgramMetadata"],[15,2,1,"","cached_class_property"],[15,1,1,"","camel_to_snake_case"],[15,1,1,"","get_annotation_value_type"],[15,1,1,"","get_args"],[15,1,1,"","get_descriptor_value_type"],[15,1,1,"","is_numeric"],[15,1,1,"","validate_positional"]],"cli_command_parser.utils.ProgramMetadata":[[15,3,1,"","__init__"],[15,3,1,"","format_epilog"]],"cli_command_parser.utils.cached_class_property":[[15,3,1,"","__init__"]],cli_command_parser:[[2,0,0,"-","actions"],[3,0,0,"-","command_parameters"],[4,0,0,"-","commands"],[5,0,0,"-","config"],[6,0,0,"-","context"],[7,0,0,"-","core"],[8,0,0,"-","error_handling"],[9,0,0,"-","exceptions"],[10,0,0,"-","formatting"],[11,0,0,"-","nargs"],[12,0,0,"-","parameters"],[13,0,0,"-","parser"],[14,0,0,"-","testing"],[15,0,0,"-","utils"]]},objnames:{"0":["py","module","Python module"],"1":["py","function","Python function"],"2":["py","class","Python class"],"3":["py","method","Python method"],"4":["py","attribute","Python attribute"],"5":["py","property","Python property"],"6":["py","parameter","Python parameter"],"7":["py","exception","Python exception"],"8":["py","data","Python data"]},objtypes:{"0":"py:module","1":"py:function","2":"py:class","3":"py:method","4":"py:attribute","5":"py:property","6":"py:parameter","7":"py:exception","8":"py:data"},terms:{"0":[0,7,12,13,17,19],"0x26dfa94fbb0":0,"0x26dfcad6e00":0,"0x7fd6c4cb4400":5,"1":[0,6,12,17,19],"2":[0,9,10,19],"2671379799232":0,"3":[4,15],"30":[10,12],"484":19,"7":15,"8":15,"9":15,"boolean":[12,19],"break":5,"case":[4,11,12,14,17,19],"class":[0,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19],"const":[0,12,19],"default":[0,4,5,6,7,12,16,17,19],"do":[4,12,17,19],"final":[4,5,17],"float":12,"function":[0,4,6,8,10,12,17,19],"import":[16,17],"int":[4,6,9,10,11,12,13,19],"long":[4,12,16,17,19],"new":19,"return":[0,4,5,6,7,11,12],"short":[12,19],"static":[4,7],"super":[4,17],"true":[0,4,5,6,7,10,11,12,15,17,19],"while":[0,6,9,17],A:[4,12,17,19],As:4,By:[12,17,19],For:[0,11,17,19],If:[0,4,6,12,17,19],In:[4,19],It:[0,12,17,19],NOT:12,One:19,Such:19,The:[0,4,5,6,7,12,16,17,18,19],There:[0,17],To:[4,17],_:15,__call__:[4,5,7,8,10,12,17],__init__:[0,3,4,5,6,8,9,10,11,12,13,15,17],__init_subclass__:12,__main__:[0,16,17],__name__:[16,17],__new__:[4,7],__subclasses__:7,_after_main_:[4,5,7,17,19],_before_main_:[4,17],_notset:5,abc:[4,12],abcmeta:7,abl:4,about:0,abov:[0,4,11,17],abstractcontextmanag:6,accept:[11,12,19],accepts_non:12,accepts_valu:12,access:0,act:19,action:[1,3,4,5,7,9,12,17,18],action_after_action_flag:[5,6,7,17],action_flag:[0,3,4,5,7,12,17],action_with_arg:19,actionflag:[3,4,6,12,17,18],activ:[6,9],active_group:12,ad:[0,5,7,12,16,17,19],add:12,add_default:[10,12],add_help:[5,7,17],addit:[12,19],addition:[0,11,17],advanc:[11,18],advanced_subcommand:17,advantag:17,affect:[6,17],after:[0,4,12,16,17,19],after_main:[0,4,12,19],after_main_act:6,alia:12,alias:17,all:[4,5,7,9,12,17,18,19],allow:[0,5,6,7,11,12,17,18,19],allow_miss:[5,6,7,17],along:17,alreadi:4,also:[0,11,12,17,19],altern:[4,17],alwai:[0,5,7,17],always_run_after_main:[5,6,7,17,19],amount:[12,18,19],an:[0,5,7,9,12,17,18,19],ani:[0,4,5,6,7,9,10,12,14,15,17,19],annot:[12,15,17,19],api:0,appear:[0,12,17,19],append:12,append_const:12,applic:[0,17],ar:[0,4,5,7,11,12,17,19],arbitrari:[12,19],arg:[0,4,12,13,17],argpars:[11,19],argument:[0,4,5,7,9,12,13,16,17,18,19],argv:[0,4,6,7,14,17],around:15,as_dict:5,as_posix:19,asctim:17,asdict:5,assert_call_fail:14,assert_call_fails_cas:14,assert_parse_fail:14,assert_parse_fails_cas:14,assert_parse_result:14,assert_parse_results_cas:14,assign:12,associ:[4,19],attempt:9,attr:15,attribut:[12,16,17,19],author:[2,3,4,5,6,7,8,9,10,11,12,13,14,15],auto:[0,7,17],automat:[0,12,16,17,19],avail:[12,16],avoid:0,b:[0,17,19],back:12,backup:[0,19],backup_dir:19,backup_rst:0,badargu:9,bar:[0,12,17,19],base:[3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19],baseexcept:8,baseopt:[3,12],baseposit:[3,12],basic:[16,17],basic_subcommand:19,basicconfig:17,baz:[0,17,19],becaus:[0,5,7,17],been:11,befor:[0,4,12,17,19],before_main:[0,4,12,19],before_main_act:6,behav:15,behavior:[5,6,17,19],being:[0,12,19],below:[11,19],better:[12,17,19],between:[17,19],block:[5,12,17,19],boilerpl:18,bool:[5,6,7,10,11,12,15],both:[0,12,17,19],bound:19,brief:12,browser:0,build:[0,12,19],build_dir:19,build_doc:0,builddoc:0,builtin:17,c:[0,19],cached_class_properti:15,call:[0,4,5,7,8,10,12,17,19],callabl:[8,12,14,15,19],camel_to_snake_cas:15,camelcas:12,can:[0,4,12,16,17,19],cannot:12,cast:19,categori:19,caus:[9,17],chain:19,chang:[17,19],charact:19,check:0,check_cal:19,choic:[7,9,12,15,17,19],choicemap:12,chosen:12,cl:4,classmethod:[4,8,12,13,15],clean:[0,12,18],cleanup:19,clearer:19,cli:[5,7,17],cli_command_pars:[0,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17],cls_handler:8,cmd_cl:14,code:[4,9,17,18],collect:[6,9,12,19],column:12,combin:[5,7,9,12,17,19],combo:19,combo_option_map:3,command:[0,1,3,5,6,7,9,10,12,14,19],command_cl:15,command_or_choic:12,command_par:3,command_paramet:[1,18],command_wrapp:19,commandconfig:[5,7,17,19],commanddefinitionerror:9,commandmeta:7,commandobj:4,commandparamet:[0,3,6,7,10],commandpars:13,commandparserexcept:9,commandtyp:[3,6,10,12,13,14],common:[2,4,17,18,19],compat:15,complet:17,condit:12,config:[1,6,7,17,18],configur:[0,4,5,19],conflict:0,constant:12,consume_valu:13,contact:17,contain:[0,12,17,19],contains_posit:12,context:[1,4,9,12,18,19],continu:4,control:17,conveni:[4,17],convert:12,copi:[5,8,19],core:[1,4,14,18],correctli:9,correspond:17,could:4,count:[4,11,12],counter:[0,12,17],ctx:[0,4],current:6,custom:12,customiz:19,d:[0,17],dataclass:5,date:17,dead:7,debug:17,decor:[0,4,12,17,19],def:[0,16,17,19],defin:[0,4,9,12,17,18,19],deleg:12,delim:[10,12,15],depend:[12,19],dequ:13,descript:[0,7,10,12,15,16,17],descriptor:18,desir:17,detect:[4,12],determin:[12,19],develop:17,dict:[3,5,6,7,14],dictionari:0,did:12,differ:[11,12,17,19],differenti:19,dir:0,direct:[4,7,17],directli:12,directori:[0,19],disabl:[7,17],discov:17,displai:[7,12,17],distinct:19,doc:0,docs_url:15,document:0,doe:[7,9,12,15,17],don:18,doug:[2,3,4,5,6,7,8,9,10,11,12,13,14,15],dry_run:0,dure:[4,12],e:[12,19],each:[0,17,19],easi:18,easier:0,echo:[17,19],effect:12,either:[0,17],els:17,email:15,enabl:0,encount:[5,7,17],enough:7,entri:[0,4,17],epilog:[7,15,17],equival:19,error:[4,7,9,17],error_handl:[1,4,5,6,7,17,18],errorhandl:[4,5,6,7,8,17],escap:[17,19],etc:[0,12],even:[0,4,5,7,16,17,19],everi:12,exampl:[0,12,17,18,19],exc:[8,14,15],exc_typ:8,exceed:11,except:[1,4,5,7,8,12,14,15,17,18,19],exclud:6,exclus:[9,12,19],execut:[0,12,19],exist:[0,17,19],exit:[0,9,16,17,19],expect:[12,14,17],expected_exc:14,expected_pattern:14,experi:17,explicit:[12,19],explicitli:[4,12,16,19],extend:[4,12,15,17,19],extended_epilog:10,extended_error_handl:17,extens:19,extra:17,f:[0,16,17,19],fail:0,fake:17,fals:[0,4,5,6,11,12,16,17,19],far:4,fbar:19,file:0,find_nested_option_that_accepts_valu:3,find_nested_pass_thru:3,find_option_that_accepts_valu:3,first:[12,19],flag:[0,12,17],flexibl:19,follow:[0,7,16,17,19],foo:[0,12,17,19],form:[12,16,19],format:[1,12,17,18],format_basic_usag:12,format_descript:12,format_epilog:15,format_help:[10,12],format_usag:[10,12],forwardref:5,found:[4,13],from:[0,12,16,17,19],full:12,func:[0,12,14,15],functool:12,further:12,gener:[0,4,7,12,16,17,19],get:[6,18],get_annotation_value_typ:15,get_arg:15,get_config:7,get_current_context:6,get_descriptor_value_typ:15,get_error_handl:6,get_handl:8,get_option_param_value_pair:3,get_par:7,get_param:7,get_pars:[0,6],get_parsing_valu:6,get_top_level_command:7,given:[4,5,7,9,11,12,17,19],goal:18,greet:[16,17],group:[3,10,12,19],group_typ:[10,12],h:[0,5,7,16,17,19],ha:[11,17],handl:[0,4,6,7,11,12,17,18,19],handle_long:13,handle_pass_thru:13,handle_posit:13,handle_short:13,handler:[4,8],have:[0,4,11,12,17,19],hello:[16,17,19],hello_world:16,helloworld:[16,17],help:[0,5,7,12,16,17,19],help_act:[0,2],helpentryformatt:10,helper:[11,14,19],helpformatt:10,here:[4,12],hide:12,hierarchi:6,higher:[0,12],hold:[6,12],hoop:19,host:19,howev:17,html:0,hunt:17,i:[12,19],id:17,ignor:[5,7,17],ignore_unknown:[5,6,7,17],immedi:19,implement:[7,12],includ:[0,11,12,17,19],include_abc:7,include_meta:12,incorrect:17,increas:[0,12,17,19],increment:12,indefinit:19,index:1,indic:[12,18,19],individu:12,inf:[0,12],infer:[7,19],infin:0,info:[12,17],inform:0,inherit:[17,18],initi:[0,4,12,18,19],input:[0,6,17,19],insid:[0,12,19],inspect:0,instal:[18,19],install_dir:19,instanc:[0,4],instanti:12,instead:[0,4,12,17,19],integ:[11,12,19],intend:[0,4,12,19],interact:0,interpret:12,intuit:17,invalid:9,invalidchoic:9,invoc:[5,7,17],is_numer:15,is_valid_arg:12,issu:17,iter:[6,12,14],its:[0,4,17,19],john:16,join:[17,19],jump:19,keep:17,keyword:[4,12,17,19],known:17,kwarg:[4,7,12,14,17],last:[12,19],later:0,least:12,less:19,let:17,level:[7,12,17,19],levelnam:17,lib:0,librari:0,like:[0,12,15,19],line:[17,19],lineno:17,list:[3,6,7,12,14,17,19],log:[0,17,19],log_fmt:17,long_opt:12,long_option_to_param_value_pair:3,longer:17,look:17,lower:[12,17,19],lpad:10,mai:[12,17,19],main:[0,4,5,7,12,16,17,19],maintain:17,major:19,make:[12,15,18,19],manag:[12,19],mani:19,manner:18,map:[7,17],mark:[0,12,19],match:[9,11],maximum:11,maybe_add_group:10,maybe_add_param:10,mcl:7,mean:11,meant:12,member:[12,19],mention:4,messag:[0,7,9,12,14,16,17,19],meta:7,metavar:12,method:[0,4,5,7,12,18,19],method_or_choic:12,methodnam:14,minim:17,minimum:11,miss:[3,5,7,9,17],missingargu:9,mix:18,modifi:17,modul:18,more:[9,11,12,15,17,19],most:19,multi:19,multipl:[0,4,5,7,16,17,19],multiple_action_flag:[5,6,7,17],multipli:12,must:[4,11,12,17,19],mutual:[9,12,19],mutually_depend:12,mutually_exclus:[12,19],mycommand:19,n:[16,17,19],name:[0,7,12,16,17,19],namespac:7,narg:[0,1,12,17,18,19],natur:19,necessari:[4,5,12,18,19],need:[4,12,17,18,19],neg:0,neither:0,nest:[12,19],never:17,next:17,no_wait:19,noactivecontext:[6,9],noisycommand:19,non:5,none:[3,4,5,6,7,9,12,14,15,17,19],nosuchopt:9,note:[0,17],noth:0,nullerrorhandl:[6,8],num_provid:6,number:[0,4,11,12,19],o:0,object:[0,3,5,6,8,10,11,12,13,15,17],often:19,old:0,omit:12,onc:18,one:[0,4,9,11,12,17,19],onli:[0,4,12,17,19],open:0,option:[0,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18],option_map:3,option_str:12,order:[0,4,12,19],org:17,organ:[0,17,18,19],origin:12,other:[0,4,9,12,17,18],otherwis:[0,12],output:17,over:[0,17],overrid:[4,6],overridden:17,own:17,page:1,param:[0,6,7,9,10,12,13],param_cl:15,parambas:12,paramconflict:9,paramet:[0,1,3,4,6,7,9,10,11,13,16,17,18],parameter_act:12,parameterdefinitionerror:[9,15],paramgroup:[3,10,12],paramorgroup:[6,9],paramsmiss:9,paramusageerror:9,parent:[3,4,6,7,12,17,19],pars:[0,4,6,12,13,18],parse_and_run:[0,4,17],parse_arg:13,parsed_action_flag:6,parser:[0,1,6,9,12],parserexit:9,parsertest:14,partial:12,pass:[4,12,13,17],pass_thru:3,passthru:[3,12],path:19,pattern:14,pep:19,perform:[9,12],person:[16,17],pick:12,pip:16,place:4,placehold:12,point:[4,17],posit:[0,3,4,5,7,12,17,18],position:12,possibl:[0,4,12,17,19],post:18,potenti:0,pre:[9,17],preced:[0,12,19],prefix:[12,15,19],prepar:12,prepare_valu:12,present:[4,12,17,19],prevent:0,primari:[4,12,17,18],print:[0,16,17,19],prioriti:12,problemat:0,process:[0,12,17,19],process_descript:10,process_usag:10,produc:19,prog:[7,15,17,19],program:[4,7,12,16,17,19],programmetadata:[7,15],project:[0,18],properti:[3,6,12],provid:[9,11,12,17,19],purpos:17,put:17,py:[0,16,17,19],pypi:16,quickli:7,quot:[17,19],r:19,rais:[4,5,6,7,9,12,17,19],rang:[11,12],re:0,readi:4,record_act:6,recurs:6,reduc:18,refer:[4,7,12,17],regardless:17,regist:[4,8,12,17,19],register_act:12,register_al:12,register_command:12,registr:19,rel:[12,19],relationship:17,releas:7,remain:[12,19],remov:0,renam:17,repeat:18,repr:12,repr_attr:12,repres:[0,5,19],requir:[0,5,7,9,11,12,17,19],resolv:4,respect:[0,17,19],restart:19,result:[0,4,12,17,19],result_valu:12,revers:19,rmtree:19,roughli:19,rst:0,run:[4,5,7,16,18,19],runtest:14,runtimeerror:[4,9],s:[0,4,12,17,19],sai:[16,17,19],same:[0,11,12,17,19],satisfi:11,save:16,script:0,search:1,second:19,section:0,see:[12,16,19],self:[0,2,8,10,12,16,17,19],sens:[12,19],sentinel:5,separ:[4,12,17,19],sequenc:[4,6,11,12],servic:19,set:[6,11,12,17,18],set_parsing_valu:6,share:[17,19],short_combin:12,short_combo:12,short_opt:12,short_option_to_param_value_pair:3,should:[0,4,5,7,12,17,19],show:[0,9,16,17,19],show_in_help:12,shutil:19,signatur:17,silent:6,similar:[5,12,17,19],simpl:[16,17],simple_flag:19,simpli:19,simplifi:19,sinc:[0,17,19],singl:[12,13],skip:4,skrypa:[2,3,4,5,6,7,8,9,10,11,12,13,14,15],snake_cas:12,snippet:0,so:[0,4,12,18,19],some:[0,17],sourc:[2,3,4,5,6,7,8,9,10,11,12,13,14,15,17],space:[12,17,19],special:0,specif:[0,11,12,17,19],specifi:[0,4,5,7,11,12,16,17,19],sphinx:0,sphinx_build:0,split:19,stack:0,standard:17,start:18,state:13,statu:9,step:17,still:0,store:[0,4,12,16,17,19],store_al:12,store_const:[0,12],str:[3,4,5,6,7,9,10,11,12,13,14,15],string:[12,17,19],sub:[4,12,19],sub_cmd:[17,19],sub_command:3,subclass:[4,7,12,17],subcommand:[3,7,12,18],subprocess:[0,19],suit:[12,19],support:[12,17,19],sy:[4,7,17],t:18,tabl:18,take:[0,12,17,19],take_act:12,taken:[0,4],target:[4,12,19],task:[18,19],taskrunn:19,technic:[0,19],termin:0,test:[0,1,7,17,18],testcas:14,text:[0,7,12,15,16,17,19],than:[17,19],thei:[0,4,5,7,11,12,17,19],them:[0,12,17,19],therefor:19,thereof:17,thi:[0,4,5,6,7,11,12,16,17,18,19],those:[12,17,19],through:[4,19],time:[0,12,17,19],titl:12,togeth:19,tool:17,top:[7,17,19],total:4,transform:12,treat:12,trigger:[4,12],tupl:[6,7,11,12,14,15],twice:0,two:[0,12,19],type:[5,6,7,8,12,14,15,17,19],typic:[12,19],u:0,uco:0,unbound:12,unchang:12,under:12,unifi:11,union:[5,6,10,11,12,14,15],unit:14,unknown:[5,7,17],unless:12,unrecogn:17,unregist:8,up:[0,17,18],updat:[0,17],url:15,us:[0,4,5,7,9,11,12,13,16,17,19],usag:[7,10,12,15,16,17,18,19],usage_metavar:12,usageerror:[9,14],user:[6,9,12,19],util:[1,18],v2:19,v:[0,17,19],val_count:6,valid:[4,11,12,19],validate_posit:15,valu:[0,5,6,7,9,11,12,15,17,18,19],variabl:[12,17],variat:16,verbatim:12,verbos:[0,17,19],versa:[12,19],version:[12,15],via:[0,4,12,17],vice:[12,19],virtual:12,vv:19,w:19,wa:[0,4,5,7,9,12,16,17,19],wai:[0,11,12,17,19],wait:19,want:[0,12],we:16,web:0,well:[17,19],were:[0,4,9,17,19],what:[7,17],when:[0,4,5,7,9,12,17,19],whenev:12,where:[12,17,19],whether:[5,7,12,17,19],which:[0,4,5,12,16,17,19],width:[10,12],without:[0,12,16,17,19],word:19,work:[4,17],world:[16,17,19],would:[0,12,17,19],would_accept:12,wrap:[7,12,17],wrapper:[15,19],write:17,x:17,you:[0,4,12,17],your:0},titles:["Advanced Usage","API Documentation","Actions Module","Command_Parameters Module","Commands Module","Config Module","Context Module","Core Module","Error_Handling Module","Exceptions Module","Formatting Module","Nargs Module","Parameters Module","Parser Module","Testing Module","Utils Module","Getting Started","Commands","CLI Command Parser","Parameters"],titleterms:{action:[0,2,19],actionflag:[0,19],advanc:0,api:[1,18],cli:[16,18],command:[4,16,17,18],command_paramet:3,config:5,configur:17,context:[0,6],core:7,counter:19,document:[1,18],error_handl:8,exampl:16,except:9,flag:19,format:10,get:16,guid:18,indic:1,initi:17,instal:16,metadata:17,method:17,mix:0,modul:[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],narg:11,option:19,other:19,paramet:[12,19],paramgroup:19,pars:17,parser:[13,16,18],passthru:19,posit:19,post:0,run:[0,17],start:16,subcommand:[17,19],tabl:1,test:14,usag:0,user:18,util:15}})