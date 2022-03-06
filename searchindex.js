Search.setIndex({docnames:["advanced","api","api/cli_command_parser.actions","api/cli_command_parser.command_parameters","api/cli_command_parser.commands","api/cli_command_parser.config","api/cli_command_parser.context","api/cli_command_parser.error_handling","api/cli_command_parser.exceptions","api/cli_command_parser.formatting","api/cli_command_parser.nargs","api/cli_command_parser.parameters","api/cli_command_parser.parser","api/cli_command_parser.testing","api/cli_command_parser.utils","basic","index"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":4,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.intersphinx":1,"sphinx.ext.viewcode":1,sphinx:56},filenames:["advanced.rst","api.rst","api/cli_command_parser.actions.rst","api/cli_command_parser.command_parameters.rst","api/cli_command_parser.commands.rst","api/cli_command_parser.config.rst","api/cli_command_parser.context.rst","api/cli_command_parser.error_handling.rst","api/cli_command_parser.exceptions.rst","api/cli_command_parser.formatting.rst","api/cli_command_parser.nargs.rst","api/cli_command_parser.parameters.rst","api/cli_command_parser.parser.rst","api/cli_command_parser.testing.rst","api/cli_command_parser.utils.rst","basic.rst","index.rst"],objects:{"cli_command_parser.actions":[[2,1,1,"","help_action"]],"cli_command_parser.command_parameters":[[3,2,1,"","CommandParameters"]],"cli_command_parser.command_parameters.CommandParameters":[[3,3,1,"","action"],[3,3,1,"","action_flags"],[3,3,1,"","combo_option_map"],[3,3,1,"","command"],[3,3,1,"","command_parent"],[3,4,1,"","find_nested_option_that_accepts_values"],[3,4,1,"","find_option_that_accepts_values"],[3,4,1,"","get_option_param_value_pairs"],[3,3,1,"","groups"],[3,4,1,"","long_option_to_param_value_pair"],[3,4,1,"","missing"],[3,3,1,"","option_map"],[3,3,1,"","options"],[3,3,1,"","parent"],[3,5,1,"","pass_thru"],[3,3,1,"","positionals"],[3,4,1,"","short_option_to_param_value_pairs"],[3,3,1,"","sub_command"]],"cli_command_parser.commands":[[4,2,1,"","Command"]],"cli_command_parser.commands.Command":[[4,4,1,"","__init_subclass__"],[4,3,1,"","ctx"],[4,4,1,"","main"],[4,5,1,"","params"],[4,4,1,"","parse"],[4,4,1,"","parse_and_run"],[4,4,1,"","run"]],"cli_command_parser.commands.Command.__init_subclass__.params":[[4,6,1,"","action_after_action_flags"],[4,6,1,"","add_help"],[4,6,1,"","allow_missing"],[4,6,1,"","choice"],[4,6,1,"","description"],[4,6,1,"","epilog"],[4,6,1,"","error_handler"],[4,6,1,"","help"],[4,6,1,"","ignore_unknown"],[4,6,1,"","multiple_action_flags"],[4,6,1,"","prog"],[4,6,1,"","usage"]],"cli_command_parser.commands.Command.main.params":[[4,6,1,"","args"],[4,6,1,"","kwargs"]],"cli_command_parser.commands.Command.parse.params":[[4,6,1,"","argv"]],"cli_command_parser.commands.Command.parse_and_run.params":[[4,6,1,"","args"],[4,6,1,"","argv"],[4,6,1,"","kwargs"]],"cli_command_parser.commands.Command.run.params":[[4,6,1,"","args"],[4,6,1,"","kwargs"]],"cli_command_parser.config":[[5,2,1,"","CommandConfig"]],"cli_command_parser.config.CommandConfig":[[5,3,1,"","action_after_action_flags"],[5,3,1,"","add_help"],[5,3,1,"","allow_missing"],[5,4,1,"","as_dict"],[5,3,1,"","error_handler"],[5,3,1,"","ignore_unknown"],[5,3,1,"","multiple_action_flags"]],"cli_command_parser.context":[[6,2,1,"","Context"],[6,1,1,"","get_current_context"]],"cli_command_parser.context.Context":[[6,3,1,"","action_after_action_flags"],[6,5,1,"","after_main_actions"],[6,3,1,"","allow_missing"],[6,5,1,"","before_main_actions"],[6,3,1,"","error_handler"],[6,4,1,"","get_error_handler"],[6,4,1,"","get_parsed"],[6,4,1,"","get_parsing_value"],[6,3,1,"","ignore_unknown"],[6,3,1,"","multiple_action_flags"],[6,4,1,"","num_provided"],[6,5,1,"","params"],[6,5,1,"","parsed_action_flags"],[6,4,1,"","record_action"],[6,4,1,"","set_parsing_value"]],"cli_command_parser.context.get_current_context.params":[[6,6,1,"","silent"]],"cli_command_parser.error_handling":[[7,2,1,"","ErrorHandler"],[7,2,1,"","NullErrorHandler"]],"cli_command_parser.error_handling.ErrorHandler":[[7,4,1,"","cls_handler"],[7,4,1,"","copy"],[7,4,1,"","get_handler"],[7,4,1,"","register"],[7,4,1,"","unregister"]],"cli_command_parser.exceptions":[[8,7,1,"","BadArgument"],[8,7,1,"","CommandDefinitionError"],[8,7,1,"","CommandParserException"],[8,7,1,"","InvalidChoice"],[8,7,1,"","MissingArgument"],[8,7,1,"","NoActiveContext"],[8,7,1,"","NoSuchOption"],[8,7,1,"","ParamConflict"],[8,7,1,"","ParamUsageError"],[8,7,1,"","ParameterDefinitionError"],[8,7,1,"","ParamsMissing"],[8,7,1,"","ParserExit"],[8,7,1,"","UsageError"]],"cli_command_parser.exceptions.CommandParserException":[[8,3,1,"","code"],[8,4,1,"","exit"],[8,4,1,"","show"]],"cli_command_parser.exceptions.MissingArgument":[[8,3,1,"","message"]],"cli_command_parser.exceptions.ParamConflict":[[8,3,1,"","message"]],"cli_command_parser.exceptions.ParamUsageError":[[8,3,1,"","message"]],"cli_command_parser.exceptions.ParamsMissing":[[8,3,1,"","message"]],"cli_command_parser.formatting":[[9,2,1,"","HelpEntryFormatter"],[9,2,1,"","HelpFormatter"]],"cli_command_parser.formatting.HelpEntryFormatter":[[9,4,1,"","process_description"],[9,4,1,"","process_usage"]],"cli_command_parser.formatting.HelpFormatter":[[9,4,1,"","format_help"],[9,4,1,"","format_usage"],[9,4,1,"","maybe_add_group"],[9,4,1,"","maybe_add_param"]],"cli_command_parser.nargs":[[10,2,1,"","Nargs"]],"cli_command_parser.nargs.Nargs":[[10,4,1,"","satisfied"]],"cli_command_parser.parameters":[[11,2,1,"","Action"],[11,2,1,"","ActionFlag"],[11,2,1,"","BaseOption"],[11,2,1,"","BasePositional"],[11,2,1,"","Counter"],[11,2,1,"","Flag"],[11,2,1,"","Option"],[11,2,1,"","ParamGroup"],[11,2,1,"","Parameter"],[11,2,1,"","PassThru"],[11,2,1,"","Positional"],[11,2,1,"","SubCommand"],[11,3,1,"","action_flag"],[11,8,1,"","after_main"],[11,8,1,"","before_main"]],"cli_command_parser.parameters.Action":[[11,4,1,"","register"],[11,4,1,"","register_action"]],"cli_command_parser.parameters.Action.register.params":[[11,6,1,"","choice"],[11,6,1,"","default"],[11,6,1,"","help"],[11,6,1,"","method_or_choice"]],"cli_command_parser.parameters.ActionFlag":[[11,5,1,"","func"],[11,4,1,"","result"]],"cli_command_parser.parameters.BaseOption":[[11,4,1,"","format_basic_usage"],[11,4,1,"","format_usage"],[11,5,1,"","long_opts"],[11,3,1,"","short_combinable"],[11,5,1,"","short_opts"]],"cli_command_parser.parameters.BasePositional":[[11,4,1,"","format_basic_usage"],[11,4,1,"","format_usage"]],"cli_command_parser.parameters.Counter":[[11,3,1,"","accepts_none"],[11,3,1,"","accepts_values"],[11,4,1,"","append"],[11,3,1,"","nargs"],[11,4,1,"","prepare_value"],[11,4,1,"","result"],[11,4,1,"","result_value"],[11,3,1,"","type"],[11,4,1,"","validate"]],"cli_command_parser.parameters.Flag":[[11,3,1,"","accepts_none"],[11,3,1,"","accepts_values"],[11,4,1,"","append_const"],[11,3,1,"","nargs"],[11,4,1,"","result"],[11,4,1,"","result_value"],[11,4,1,"","store_const"],[11,4,1,"","would_accept"]],"cli_command_parser.parameters.Option":[[11,4,1,"","append"],[11,4,1,"","store"]],"cli_command_parser.parameters.ParamGroup":[[11,4,1,"","active_group"],[11,4,1,"","add"],[11,5,1,"","contains_positional"],[11,3,1,"","description"],[11,4,1,"","format_description"],[11,4,1,"","format_help"],[11,4,1,"","format_usage"],[11,3,1,"","members"],[11,3,1,"","mutually_dependent"],[11,3,1,"","mutually_exclusive"],[11,4,1,"","register"],[11,4,1,"","register_all"],[11,5,1,"","show_in_help"],[11,4,1,"","validate"]],"cli_command_parser.parameters.ParamGroup.format_help.params":[[11,6,1,"","add_default"],[11,6,1,"","clean"],[11,6,1,"","group_type"],[11,6,1,"","width"]],"cli_command_parser.parameters.Parameter":[[11,4,1,"","__init_subclass__"],[11,3,1,"","accepts_none"],[11,3,1,"","accepts_values"],[11,3,1,"","choices"],[11,4,1,"","format_help"],[11,4,1,"","format_usage"],[11,4,1,"","is_valid_arg"],[11,3,1,"","metavar"],[11,3,1,"","nargs"],[11,4,1,"","prepare_value"],[11,4,1,"","result"],[11,4,1,"","result_value"],[11,5,1,"","show_in_help"],[11,4,1,"","take_action"],[11,3,1,"","type"],[11,5,1,"","usage_metavar"],[11,4,1,"","validate"],[11,4,1,"","would_accept"]],"cli_command_parser.parameters.PassThru":[[11,4,1,"","format_basic_usage"],[11,3,1,"","nargs"],[11,4,1,"","store_all"],[11,4,1,"","take_action"]],"cli_command_parser.parameters.Positional":[[11,4,1,"","append"],[11,4,1,"","store"]],"cli_command_parser.parameters.SubCommand":[[11,4,1,"","register"],[11,4,1,"","register_command"]],"cli_command_parser.parameters.SubCommand.register.params":[[11,6,1,"","choice"],[11,6,1,"","command_or_choice"],[11,6,1,"","help"]],"cli_command_parser.parser":[[12,2,1,"","CommandParser"]],"cli_command_parser.parser.CommandParser":[[12,4,1,"","consume_values"],[12,4,1,"","handle_long"],[12,4,1,"","handle_pass_thru"],[12,4,1,"","handle_positional"],[12,4,1,"","handle_short"],[12,4,1,"","parse_args"]],"cli_command_parser.testing":[[13,2,1,"","ParserTest"]],"cli_command_parser.testing.ParserTest":[[13,4,1,"","assert_call_fails"],[13,4,1,"","assert_call_fails_cases"],[13,4,1,"","assert_parse_fails"],[13,4,1,"","assert_parse_fails_cases"],[13,4,1,"","assert_parse_results"],[13,4,1,"","assert_parse_results_cases"]],"cli_command_parser.utils":[[14,2,1,"","ProgramMetadata"],[14,2,1,"","cached_class_property"],[14,1,1,"","camel_to_snake_case"],[14,1,1,"","get_descriptor_value_type"],[14,1,1,"","is_numeric"],[14,1,1,"","validate_positional"]],"cli_command_parser.utils.ProgramMetadata":[[14,4,1,"","format_epilog"]],cli_command_parser:[[2,0,0,"-","actions"],[3,0,0,"-","command_parameters"],[4,0,0,"-","commands"],[5,0,0,"-","config"],[6,0,0,"-","context"],[7,0,0,"-","error_handling"],[8,0,0,"-","exceptions"],[9,0,0,"-","formatting"],[10,0,0,"-","nargs"],[11,0,0,"-","parameters"],[12,0,0,"-","parser"],[13,0,0,"-","testing"],[14,0,0,"-","utils"]]},objnames:{"0":["py","module","Python module"],"1":["py","function","Python function"],"2":["py","class","Python class"],"3":["py","attribute","Python attribute"],"4":["py","method","Python method"],"5":["py","property","Python property"],"6":["py","parameter","Python parameter"],"7":["py","exception","Python exception"],"8":["py","data","Python data"]},objtypes:{"0":"py:module","1":"py:function","2":"py:class","3":"py:attribute","4":"py:method","5":"py:property","6":"py:parameter","7":"py:exception","8":"py:data"},terms:{"0":[4,11,12],"0x7fa0729fc3d0":5,"1":[6,11],"2":[8,9],"3":4,"30":[9,11],"break":5,"case":[11,13],"class":[3,4,5,6,7,8,9,10,11,12,13,14,16],"const":11,"default":[4,5,6,11],"do":[4,11],"final":4,"float":11,"function":6,"int":[4,6,8,9,10,11,12],"return":[4,5,6,11],"super":4,"true":[5,6,9,11,14],"while":[6,8],A:[4,11],If:[4,6,11],It:11,The:[4,5,6,11,16],To:4,_:14,__init__:4,__init_subclass__:[4,11],_after_main_:4,_before_main_:4,_notset:5,abc:[4,11],abl:4,abov:4,abstractcontextmanag:6,accepts_non:11,accepts_valu:11,action:[1,3,4,5,8,11,16],action_after_action_flag:[4,5,6],action_flag:[3,4,5,11],actionflag:[3,6,11],activ:[6,8],active_group:11,ad:[4,5],add:11,add_default:[9,11],add_help:[4,5],affect:6,after:11,after_main:11,after_main_act:6,alia:11,all:[4,5,8,16],allow:[4,5,6,11,16],allow_miss:[4,5,6],alreadi:4,also:11,altern:4,amount:16,an:[4,5,8,11,16],ani:[4,5,6,8,9,11,13,14],append:11,append_const:11,ar:[4,5,11],arg:[4,11,12],argument:[4,5,8,11,12,16],argv:[4,6,13],as_dict:5,asdict:5,assert_call_fail:13,assert_call_fails_cas:13,assert_parse_fail:13,assert_parse_fails_cas:13,assert_parse_result:13,assert_parse_results_cas:13,associ:4,attempt:8,attr:14,author:[2,3,4,5,6,7,8,9,10,11,12,13,14],auto:4,automat:11,avail:[11,15],back:11,badargu:8,base:[3,4,5,6,7,8,9,10,11,12,13,14,16],baseexcept:7,baseopt:[3,11],baseposit:[3,11],becaus:5,befor:[4,11],before_main:11,before_main_act:6,behavior:[5,6],boilerpl:16,bool:[4,5,6,9,10,11,14],cached_class_properti:14,call:[4,11],callabl:[7,11,13,14],camel_to_snake_cas:14,camelcas:11,can:4,caus:8,choic:[4,8,11,14],choicemap:11,chosen:11,classmethod:[4,7,11,12,14],clean:[11,16],cli:[4,5],cli_command_pars:[2,3,4,5,6,7,8,9,10,11,12,13,14],cls_handler:7,cmd_cl:13,code:[4,8,16],collect:[6,8,11],column:11,combin:[4,5,8,11],combo_option_map:3,command:[1,3,5,6,8,9,11,13],command_cl:14,command_or_choic:11,command_par:3,command_paramet:[1,4],commandconfig:[4,5],commanddefinitionerror:8,commandobj:4,commandparamet:[3,4,6,9],commandpars:12,commandparserexcept:8,commandtyp:[3,6,9,11,12,13],common:[2,4,16],config:[1,4,6],configur:[4,5],consume_valu:12,contain:11,contains_posit:11,context:[1,4,8],convert:11,copi:[5,7],core:4,correctli:8,count:10,counter:11,ctx:4,current:6,dataclass:5,decor:[4,11],defin:[4,8,16],delim:[9,11,14],depend:11,dequ:12,descript:[4,9,11,14],descriptor:16,determin:11,dict:[3,5,6,13],directli:11,displai:[4,11],docs_url:14,doe:[4,8,11],don:16,doug:[2,3,4,5,6,7,8,9,10,11,12,13,14],dure:[4,11],easi:16,email:14,encount:[4,5],entri:4,epilog:[4,14],error:[4,8],error_handl:[1,4,5,6],errorhandl:[4,5,6,7],exc:[7,13,14],exc_typ:7,except:[1,4,5,7,13,14],exclud:6,exclus:[8,11],execut:11,exit:8,expect:13,expected_exc:13,expected_pattern:13,explicit:11,explicitli:11,extend:[4,11,14],extended_epilog:9,fals:[5,6,11],far:4,find_nested_option_that_accepts_valu:3,find_option_that_accepts_valu:3,first:11,flag:11,follow:4,format:[1,11],format_basic_usag:11,format_descript:11,format_epilog:14,format_help:[9,11],format_usag:[9,11],forwardref:[5,11],found:12,from:11,full:11,func:[11,13,14],functool:11,further:11,gener:4,get:6,get_current_context:6,get_descriptor_value_typ:14,get_error_handl:6,get_handl:7,get_option_param_value_pair:3,get_pars:6,get_parsing_valu:6,given:[4,5,8,11],goal:16,group:[3,9,11],group_typ:[9,11],h:[4,5],handl:[4,6,16],handle_long:12,handle_pass_thru:12,handle_posit:12,handle_short:12,handler:[4,7],have:4,help:[4,5,11],help_act:2,helpentryformatt:9,helper:13,helpformatt:9,here:[4,11],hide:11,hierarchi:6,hold:6,ignor:[4,5],ignore_unknown:[4,5,6],implement:11,includ:11,include_meta:11,index:1,inherit:16,initi:[4,11,16],input:6,instanc:4,instanti:11,instead:4,intend:4,interpret:11,invalid:8,invalidchoic:8,invoc:[4,5],is_numer:14,is_valid_arg:11,iter:[6,11,13],keyword:[4,11],kwarg:[4,11,13],level:4,list:[3,6,11,13],long_opt:11,long_option_to_param_value_pair:3,lpad:9,mai:11,main:[4,11],make:16,manner:16,map:4,mark:11,match:8,maybe_add_group:9,maybe_add_param:9,member:11,mention:4,messag:[4,8,13],metavar:11,method:[4,5,11],method_or_choic:11,methodnam:13,miss:[3,4,5,8],missingargu:8,more:8,multipl:[4,5],multiple_action_flag:[4,5,6],must:11,mutual:[8,11],mutually_depend:11,mutually_exclus:11,name:[4,11],narg:[1,11],necessari:[4,5,11,16],need:[4,11,16],noactivecontext:[6,8],non:5,none:[3,4,5,6,8,11,13,14],nosuchopt:8,noth:11,nullerrorhandl:[6,7],num_provid:6,number:4,object:[3,5,6,7,9,10,11,12,14],omit:11,onc:16,one:8,onli:11,option:[3,4,5,6,7,8,9,11,12,13,14],option_map:3,option_str:11,order:[4,11],organ:16,origin:11,other:[4,8,11],overrid:[4,6],overridden:11,page:[0,1],param:[4,6,8,9,11,12],param_cl:14,parambas:11,paramconflict:8,paramet:[1,3,4,6,8,9,12,16],parameterdefinitionerror:[8,14],paramgroup:[3,9,11],paramorgroup:[6,8],paramsmiss:8,paramusageerror:8,parent:[3,6,11],pars:[4,6,11,12,16],parse_and_run:4,parse_arg:12,parsed_action_flag:6,parser:[1,6,8],parserexit:8,parsertest:13,partial:11,pass:[4,12],pass_thru:3,passthru:[3,11],pattern:13,perform:8,pip:15,place:4,point:4,posit:[3,4,5,11],possibl:4,pre:8,prefix:14,prepar:11,prepare_valu:11,primari:[4,11,16],process_descript:9,process_usag:9,prog:[4,14],program:4,programmetadata:14,progress:[0,16],project:16,properti:[3,4,6,11],provid:[8,11],pypi:15,rais:[4,5,6,8],rang:[10,11],readi:4,record_act:6,recurs:6,reduc:16,refer:[4,11],regist:[4,7,11],register_act:11,register_al:11,register_command:11,repeat:16,repres:5,requir:[4,5,8,11],resolv:4,result:[4,11],result_valu:11,run:[4,5],runtest:13,runtimeerror:8,s:4,satisfi:10,search:1,self:2,sentinel:5,separ:4,sequenc:[4,6,10,11],set:[6,10,11,16],set_parsing_valu:6,short_combin:11,short_combo:11,short_opt:11,short_option_to_param_value_pair:3,should:[4,5,11],show:8,show_in_help:11,silent:6,singl:12,skip:4,skrypa:[2,3,4,5,6,7,8,9,10,11,12,13,14],snake_cas:11,so:[4,11,16],sourc:[2,3,4,5,6,7,8,9,10,11,12,13,14],specifi:[4,5,11],state:12,statu:8,still:[0,16],store:[4,11],store_al:11,store_const:11,str:[3,4,5,6,8,9,10,11,12,13,14],string:11,sub:4,sub_command:3,subclass:[4,11],subcommand:[3,4,11,16],sy:4,t:16,take:11,take_act:11,taken:4,target:4,task:16,test:1,testcas:13,text:[4,11,14],thei:[4,5],them:11,thi:[0,4,5,6,11,16],titl:11,top:4,total:4,trigger:4,tupl:[6,10,11,13],type:[6,7,11,13,14],unchang:11,union:[5,6,9,10,11,13,14],unit:13,unknown:[4,5],unregist:7,up:16,url:14,us:[4,5,8,11,12],usag:[4,9,11,14],usage_metavar:11,usageerror:[8,13],user:[6,8],util:1,val_count:6,valid:11,validate_posit:14,valu:[4,5,6,8,11,14,16],version:[11,14],via:4,virtual:11,wa:[4,5,8,11],wai:11,want:11,were:[4,8],what:4,when:[4,5,8,11],whether:[4,5,11],which:[4,5,11],width:[9,11],without:11,work:[0,16],would_accept:11,wrap:[4,11],you:[4,11]},titles:["Advanced Usage","API Documentation","Actions Module","Command_Parameters Module","Commands Module","Config Module","Context Module","Error_Handling Module","Exceptions Module","Formatting Module","Nargs Module","Parameters Module","Parser Module","Testing Module","Utils Module","Getting Started","CLI Command Parser"],titleterms:{action:2,advanc:0,api:1,cli:[15,16],command:[4,15,16],command_paramet:3,config:5,context:6,document:1,error_handl:7,except:8,format:9,get:15,indic:1,instal:15,modul:[1,2,3,4,5,6,7,8,9,10,11,12,13,14],narg:10,paramet:11,parser:[12,15,16],start:15,tabl:1,test:13,usag:0,util:14}})