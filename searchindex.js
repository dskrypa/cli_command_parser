Search.setIndex({docnames:["cli_command_parser.actions","cli_command_parser.args","cli_command_parser.command_parameters","cli_command_parser.commands","cli_command_parser.config","cli_command_parser.error_handling","cli_command_parser.exceptions","cli_command_parser.formatting","cli_command_parser.nargs","cli_command_parser.parameters","cli_command_parser.parser","cli_command_parser.testing","cli_command_parser.utils","index"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":4,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.intersphinx":1,"sphinx.ext.viewcode":1,sphinx:56},filenames:["cli_command_parser.actions.rst","cli_command_parser.args.rst","cli_command_parser.command_parameters.rst","cli_command_parser.commands.rst","cli_command_parser.config.rst","cli_command_parser.error_handling.rst","cli_command_parser.exceptions.rst","cli_command_parser.formatting.rst","cli_command_parser.nargs.rst","cli_command_parser.parameters.rst","cli_command_parser.parser.rst","cli_command_parser.testing.rst","cli_command_parser.utils.rst","index.rst"],objects:{"cli_command_parser.actions":[[0,1,1,"","help_action"]],"cli_command_parser.args":[[1,2,1,"","Args"]],"cli_command_parser.args.Args":[[1,3,1,"","action_flags"],[1,3,1,"","after_main_actions"],[1,3,1,"","before_main_actions"],[1,4,1,"","find_all"],[1,4,1,"","num_provided"],[1,4,1,"","record_action"]],"cli_command_parser.args.Args.params":[[1,5,1,"","args"]],"cli_command_parser.command_parameters":[[2,2,1,"","CommandParameters"]],"cli_command_parser.command_parameters.CommandParameters":[[2,6,1,"","action"],[2,4,1,"","args_to_dict"],[2,6,1,"","combo_option_map"],[2,6,1,"","command"],[2,6,1,"","command_parent"],[2,4,1,"","find_nested_option_that_accepts_values"],[2,4,1,"","find_option_that_accepts_values"],[2,4,1,"","get_option_param_value_pairs"],[2,6,1,"","groups"],[2,4,1,"","long_option_to_param_value_pair"],[2,6,1,"","option_map"],[2,6,1,"","options"],[2,6,1,"","parent"],[2,3,1,"","pass_thru"],[2,6,1,"","positionals"],[2,4,1,"","short_option_to_param_value_pairs"],[2,6,1,"","sub_command"]],"cli_command_parser.commands":[[3,2,1,"","Command"]],"cli_command_parser.commands.Command":[[3,4,1,"","__init_subclass__"],[3,4,1,"","after_main"],[3,6,1,"","args"],[3,4,1,"","before_main"],[3,3,1,"","command_config"],[3,4,1,"","main"],[3,3,1,"","params"],[3,4,1,"","parse"],[3,4,1,"","parse_and_run"],[3,3,1,"","parser"],[3,4,1,"","run"]],"cli_command_parser.commands.Command.__init_subclass__.params":[[3,5,1,"","abstract"],[3,5,1,"","action_after_action_flags"],[3,5,1,"","add_help"],[3,5,1,"","allow_missing"],[3,5,1,"","allow_unknown"],[3,5,1,"","choice"],[3,5,1,"","description"],[3,5,1,"","epilog"],[3,5,1,"","error_handler"],[3,5,1,"","help"],[3,5,1,"","multiple_action_flags"],[3,5,1,"","prog"],[3,5,1,"","usage"]],"cli_command_parser.commands.Command.after_main.params":[[3,5,1,"","args"],[3,5,1,"","kwargs"]],"cli_command_parser.commands.Command.before_main.params":[[3,5,1,"","args"],[3,5,1,"","kwargs"]],"cli_command_parser.commands.Command.main.params":[[3,5,1,"","args"],[3,5,1,"","kwargs"]],"cli_command_parser.commands.Command.parse.params":[[3,5,1,"","args"]],"cli_command_parser.commands.Command.parse_and_run.params":[[3,5,1,"","args"],[3,5,1,"","argv"],[3,5,1,"","kwargs"]],"cli_command_parser.commands.Command.run.params":[[3,5,1,"","args"],[3,5,1,"","kwargs"]],"cli_command_parser.config":[[4,2,1,"","CommandConfig"]],"cli_command_parser.config.CommandConfig":[[4,6,1,"","action_after_action_flags"],[4,6,1,"","add_help"],[4,6,1,"","allow_missing"],[4,6,1,"","allow_unknown"],[4,4,1,"","as_dict"],[4,6,1,"","error_handler"],[4,6,1,"","multiple_action_flags"]],"cli_command_parser.error_handling":[[5,2,1,"","ErrorHandler"],[5,2,1,"","NullErrorHandler"]],"cli_command_parser.error_handling.ErrorHandler":[[5,4,1,"","cls_handler"],[5,4,1,"","copy"],[5,4,1,"","get_handler"],[5,4,1,"","register"],[5,4,1,"","unregister"]],"cli_command_parser.exceptions":[[6,7,1,"","BadArgument"],[6,7,1,"","CommandDefinitionError"],[6,7,1,"","CommandParserException"],[6,7,1,"","InvalidChoice"],[6,7,1,"","MissingArgument"],[6,7,1,"","NoSuchOption"],[6,7,1,"","ParamConflict"],[6,7,1,"","ParamUsageError"],[6,7,1,"","ParameterDefinitionError"],[6,7,1,"","ParamsMissing"],[6,7,1,"","ParserExit"],[6,7,1,"","UsageError"]],"cli_command_parser.exceptions.CommandParserException":[[6,6,1,"","code"],[6,4,1,"","exit"],[6,4,1,"","show"]],"cli_command_parser.exceptions.MissingArgument":[[6,6,1,"","message"]],"cli_command_parser.exceptions.ParamConflict":[[6,6,1,"","message"]],"cli_command_parser.exceptions.ParamUsageError":[[6,6,1,"","message"]],"cli_command_parser.exceptions.ParamsMissing":[[6,6,1,"","message"]],"cli_command_parser.formatting":[[7,2,1,"","HelpEntryFormatter"],[7,2,1,"","HelpFormatter"]],"cli_command_parser.formatting.HelpEntryFormatter":[[7,4,1,"","process_description"],[7,4,1,"","process_usage"]],"cli_command_parser.formatting.HelpFormatter":[[7,4,1,"","format_help"],[7,4,1,"","format_usage"],[7,4,1,"","maybe_add_group"],[7,4,1,"","maybe_add_param"]],"cli_command_parser.nargs":[[8,2,1,"","Nargs"]],"cli_command_parser.nargs.Nargs":[[8,4,1,"","satisfied"]],"cli_command_parser.parameters":[[9,2,1,"","Action"],[9,2,1,"","ActionFlag"],[9,2,1,"","BaseOption"],[9,2,1,"","BasePositional"],[9,2,1,"","Counter"],[9,2,1,"","Flag"],[9,2,1,"","Option"],[9,2,1,"","ParamGroup"],[9,2,1,"","Parameter"],[9,2,1,"","PassThru"],[9,2,1,"","Positional"],[9,2,1,"","SubCommand"],[9,6,1,"","action_flag"],[9,8,1,"","after_main"],[9,8,1,"","before_main"]],"cli_command_parser.parameters.Action":[[9,4,1,"","register"],[9,4,1,"","register_action"]],"cli_command_parser.parameters.Action.register.params":[[9,5,1,"","choice"],[9,5,1,"","help"],[9,5,1,"","method_or_choice"]],"cli_command_parser.parameters.ActionFlag":[[9,3,1,"","func"],[9,4,1,"","result"]],"cli_command_parser.parameters.BaseOption":[[9,4,1,"","format_basic_usage"],[9,4,1,"","format_usage"],[9,3,1,"","long_opts"],[9,6,1,"","short_combinable"],[9,3,1,"","short_opts"]],"cli_command_parser.parameters.BasePositional":[[9,4,1,"","format_basic_usage"],[9,4,1,"","format_usage"]],"cli_command_parser.parameters.Counter":[[9,6,1,"","accepts_none"],[9,6,1,"","accepts_values"],[9,4,1,"","append"],[9,6,1,"","nargs"],[9,4,1,"","prepare_value"],[9,4,1,"","result"],[9,4,1,"","result_value"],[9,6,1,"","type"],[9,4,1,"","validate"]],"cli_command_parser.parameters.Flag":[[9,6,1,"","accepts_none"],[9,6,1,"","accepts_values"],[9,4,1,"","append_const"],[9,6,1,"","nargs"],[9,4,1,"","result"],[9,4,1,"","result_value"],[9,4,1,"","store_const"],[9,4,1,"","would_accept"]],"cli_command_parser.parameters.Option":[[9,4,1,"","append"],[9,4,1,"","store"]],"cli_command_parser.parameters.ParamGroup":[[9,4,1,"","active_group"],[9,4,1,"","add"],[9,3,1,"","contains_positional"],[9,6,1,"","description"],[9,4,1,"","format_description"],[9,4,1,"","format_help"],[9,4,1,"","format_usage"],[9,6,1,"","members"],[9,6,1,"","mutually_dependent"],[9,6,1,"","mutually_exclusive"],[9,4,1,"","register"],[9,4,1,"","register_all"],[9,3,1,"","show_in_help"],[9,4,1,"","validate"]],"cli_command_parser.parameters.ParamGroup.format_help.params":[[9,5,1,"","add_default"],[9,5,1,"","clean"],[9,5,1,"","group_type"],[9,5,1,"","width"]],"cli_command_parser.parameters.Parameter":[[9,4,1,"","__init_subclass__"],[9,6,1,"","accepts_none"],[9,6,1,"","accepts_values"],[9,6,1,"","choices"],[9,4,1,"","format_help"],[9,4,1,"","format_usage"],[9,4,1,"","is_valid_arg"],[9,6,1,"","metavar"],[9,6,1,"","nargs"],[9,4,1,"","prepare_value"],[9,4,1,"","result"],[9,4,1,"","result_value"],[9,3,1,"","show_in_help"],[9,4,1,"","take_action"],[9,6,1,"","type"],[9,3,1,"","usage_metavar"],[9,4,1,"","validate"],[9,4,1,"","would_accept"]],"cli_command_parser.parameters.PassThru":[[9,4,1,"","format_basic_usage"],[9,6,1,"","nargs"],[9,4,1,"","store_all"],[9,4,1,"","take_action"]],"cli_command_parser.parameters.Positional":[[9,4,1,"","append"],[9,4,1,"","store"]],"cli_command_parser.parameters.SubCommand":[[9,4,1,"","register"],[9,4,1,"","register_command"]],"cli_command_parser.parameters.SubCommand.register.params":[[9,5,1,"","choice"],[9,5,1,"","command_or_choice"],[9,5,1,"","help"]],"cli_command_parser.parser":[[10,2,1,"","CommandParser"]],"cli_command_parser.parser.CommandParser":[[10,6,1,"","command"],[10,4,1,"","parse_args"]],"cli_command_parser.testing":[[11,2,1,"","ParserTest"]],"cli_command_parser.testing.ParserTest":[[11,4,1,"","assert_call_fails"],[11,4,1,"","assert_call_fails_cases"],[11,4,1,"","assert_parse_fails"],[11,4,1,"","assert_parse_fails_cases"],[11,4,1,"","assert_parse_results"],[11,4,1,"","assert_parse_results_cases"]],"cli_command_parser.utils":[[12,2,1,"","ProgramMetadata"],[12,1,1,"","camel_to_snake_case"],[12,2,1,"","classproperty"],[12,1,1,"","get_descriptor_value_type"],[12,1,1,"","is_numeric"],[12,1,1,"","validate_positional"]],"cli_command_parser.utils.ProgramMetadata":[[12,4,1,"","format_epilog"]],cli_command_parser:[[0,0,0,"-","actions"],[1,0,0,"-","args"],[2,0,0,"-","command_parameters"],[3,0,0,"-","commands"],[4,0,0,"-","config"],[5,0,0,"-","error_handling"],[6,0,0,"-","exceptions"],[7,0,0,"-","formatting"],[8,0,0,"-","nargs"],[9,0,0,"-","parameters"],[10,0,0,"-","parser"],[11,0,0,"-","testing"],[12,0,0,"-","utils"]]},objnames:{"0":["py","module","Python module"],"1":["py","function","Python function"],"2":["py","class","Python class"],"3":["py","property","Python property"],"4":["py","method","Python method"],"5":["py","parameter","Python parameter"],"6":["py","attribute","Python attribute"],"7":["py","exception","Python exception"],"8":["py","data","Python data"]},objtypes:{"0":"py:module","1":"py:function","2":"py:class","3":"py:property","4":"py:method","5":"py:parameter","6":"py:attribute","7":"py:exception","8":"py:data"},terms:{"0":[3,9],"0x7f3e83cd43d0":4,"1":[1,9],"2":[6,7],"3":3,"30":[7,9],"abstract":3,"break":4,"case":[9,11],"class":[1,2,3,4,5,6,7,8,9,10,11,12],"const":9,"default":[1,3,4,9],"do":[3,9,12],"final":3,"float":9,"int":[1,3,6,7,8,9],"return":[3,4,9,12],"super":3,"true":[3,4,7,9,12],"while":12,A:[3,9,12],If:[3,9],It:9,The:[1,3,4,9],To:3,_:12,__init__:3,__init_subclass__:[3,9],_notset:4,abc:9,abl:3,abov:[3,12],accepts_non:9,accepts_valu:9,accomplish:12,action:[1,2,3,4,9],action_after_action_flag:[3,4],action_flag:[1,3,4,9],actionflag:[1,3,9],active_group:9,ad:[3,4],add:9,add_default:[7,9],add_help:[3,4],after:[1,3,9,12],after_main:[3,9],after_main_act:1,again:12,alia:9,all:[3,4,6],allow:[3,4,9],allow_miss:[3,4,10],allow_unknown:[3,4,10],alreadi:3,also:9,altern:3,an:[3,4,6,9],ani:[1,2,3,4,6,7,9,10,11,12],append:9,append_const:9,appli:12,ar:[3,4,9],arg:[2,3,9,10],args_to_dict:2,argument:[1,3,4,6,9],argv:[1,3,11],as_dict:4,asdict:4,assert_call_fail:11,assert_call_fails_cas:11,assert_parse_fail:11,assert_parse_fails_cas:11,assert_parse_result:11,assert_parse_results_cas:11,associ:3,attr:12,author:[0,1,2,3,4,5,6,7,8,9,10,11,12],auto:3,automat:9,back:9,badargu:6,base:[1,2,3,4,5,6,7,8,9,10,11,12],baseexcept:5,baseopt:[2,9],baseposit:[2,9],becaus:4,befor:[1,3,9],before_main:[3,9],before_main_act:1,behavior:4,being:3,bool:[3,4,7,8,9,10,12],call:[3,9],callabl:[5,9,11,12],camel_to_snake_cas:12,camelcas:9,can:3,caus:6,checker:12,choic:[3,6,9,12],choicemap:9,chosen:9,classmethod:[3,5,9,12],classproperti:12,clean:9,cli:[3,4],cli_command_pars:[0,1,2,3,4,5,6,7,8,9,10,11,12],cls_handler:5,cmd_cl:11,code:[3,6],collect:[2,6,9],column:9,combin:[3,4,6,9],combo_option_map:2,command:[2,4,6,7,9,10,11],command_cl:12,command_config:3,command_or_choic:9,command_par:2,command_paramet:3,commandconfig:[3,4],commanddefinitionerror:6,commandobj:3,commandparamet:[2,3,7],commandpars:[3,10],commandparserexcept:6,commandtyp:[2,7,9,10,11],common:[0,3],config:3,configur:[3,4],confus:12,consid:3,contain:[3,9],contains_posit:9,convert:9,copi:[4,5],core:3,correctli:6,could:12,count:8,counter:9,dataclass:4,declar:12,decor:[3,9,12],defin:[3,6],delim:[7,9,12],depend:9,descript:[3,7,9,12],determin:9,dict:[1,2,4,11],did:12,directli:9,displai:[3,9],docs_url:12,document:12,doe:[3,6,9],doug:[0,1,2,3,4,5,6,7,8,9,10,11,12],dure:[1,3,9],email:12,encount:[3,4],entri:3,epilog:[3,12],error:[3,6],error_handl:[3,4],errorhandl:[3,4,5],exc:[5,11,12],exc_typ:5,except:[3,4,5,11,12],exclud:2,exclus:[6,9],execut:9,exit:6,expect:11,expected_exc:11,expected_pattern:11,explicitli:9,extend:[3,9,12],extended_epilog:7,fals:[3,4,9,10],far:3,find_al:1,find_nested_option_that_accepts_valu:2,find_option_that_accepts_valu:2,first:9,flag:9,follow:3,format:9,format_basic_usag:9,format_descript:9,format_epilog:12,format_help:[7,9],format_usag:[7,9],forwardref:[4,9],from:[3,9],full:9,func:[9,11,12],functool:9,further:9,gener:3,get_descriptor_value_typ:12,get_handl:5,get_option_param_value_pair:2,given:[3,4,6,9],group:[2,7,9],group_typ:[7,9],h:[3,4],handl:3,handler:[3,5],have:3,help:[3,4,9],help_act:0,helpentryformatt:7,helper:11,helpformatt:7,here:[3,9],hide:9,ignor:3,implement:[9,12],includ:[9,12],include_meta:9,index:13,initi:[3,9],instanc:3,instanti:9,instead:3,intend:3,interpret:9,invalid:6,invalidchoic:6,invoc:[3,4],is_numer:12,is_valid_arg:9,iter:[1,9,11],its:12,keep:1,keyword:[3,9],kwarg:[3,9,11],level:3,list:[2,9,11],long_opt:9,long_option_to_param_value_pair:2,lpad:7,mai:[3,9],main:[1,3,9],map:3,match:6,maybe_add_group:7,maybe_add_param:7,mean:12,member:9,mention:3,messag:[3,6,11],metavar:9,method:[3,4,9,12],method_or_choic:9,methodnam:11,miss:[3,4,6],missingargu:6,modul:13,more:6,multipl:[3,4],multiple_action_flag:[3,4],mutual:[6,9],mutually_depend:9,mutually_exclus:9,name:[3,9],narg:9,necessari:[3,4,9],need:[3,9],non:4,none:[2,3,4,6,9,11,12],nosuchopt:6,noth:9,nullerrorhandl:5,num_provid:1,number:3,object:[1,2,3,4,5,7,8,9,10,12],omit:9,one:6,onli:[9,12],option:[1,2,3,4,5,6,7,9,10,11,12],option_map:2,option_str:9,order:[3,9],origin:9,other:[3,6,9],overrid:3,overridden:9,page:13,param:[1,3,6,7,9],param_cl:12,param_typ:1,parambas:9,paramconflict:6,paramet:[1,2,3,6,7],parameterdefinitionerror:[6,12],paramgroup:[2,7,9],paramorgroup:[1,6],paramsmiss:6,paramusageerror:6,parent:[2,3,9],pars:[1,3,9],parse_and_run:3,parse_arg:10,parser:[3,6],parserexit:6,parsertest:11,partial:9,pass:3,pass_thru:2,passthru:[2,9],pattern:11,place:3,point:3,posit:[2,3,4,9],possibl:3,pre:6,prefix:12,prepar:9,prepare_valu:9,prevent:3,primari:[3,9],process_descript:7,process_usag:7,prog:[3,12],program:3,programmetadata:12,properli:12,properti:[1,2,3,9,12],provid:[6,9],pycharm:12,rais:[3,4,6],rang:[8,9],raw:1,read:12,readi:3,recogn:12,record_act:1,refer:[3,9],regist:[3,5,9],register_act:9,register_al:9,register_command:9,repres:4,requir:[3,4,6,9,12],resolv:3,result:[3,9],result_valu:9,run:[3,4],runtest:11,s:[3,12],satisfi:8,search:13,self:0,sentinel:4,separ:[3,12],sequenc:[1,3,8,9],set:[3,8,9],short_combin:9,short_combo:9,short_opt:9,short_option_to_param_value_pair:2,should:[1,3,4,9],show:6,show_in_help:9,skip:3,skrypa:[0,1,2,3,4,5,6,7,8,9,10,11,12],snake_cas:9,so:[3,9,12],sourc:[0,1,2,3,4,5,6,7,8,9,10,11,12],specifi:[3,4,9],sphinx:12,stack:12,statu:6,store:[1,3,9],store_al:9,store_const:9,str:[1,2,3,4,6,7,8,9,11,12],string:9,sub:3,sub_command:2,subclass:[3,9],subcommand:[2,3,9],sy:[1,3],take_act:9,taken:[1,3],target:3,testcas:11,text:[3,9,12],thei:[3,4],them:9,thi:[3,4,9,12],titl:9,top:3,total:3,track:1,trigger:3,tupl:[8,9,11],type:[1,5,9,11,12],unchang:9,union:[3,4,7,8,9,10,11,12],unit:11,unknown:[3,4],unregist:5,url:12,us:[3,4,6,9],usag:[3,7,9,12],usage_metavar:9,usageerror:[6,11],user:6,val_count:1,valid:[3,9],validate_posit:12,valu:[3,4,6,9,12],version:[9,12],via:3,virtual:9,wa:[3,4,6,9],wai:9,were:[1,3,6],what:3,when:[3,4,6,9,12],whether:[3,4,9],which:[3,4,9],width:[7,9],without:9,would_accept:9,wrap:[3,9],you:3},titles:["Actions Module","Args Module","Command_Parameters Module","Commands Module","Config Module","Error_Handling Module","Exceptions Module","Formatting Module","Nargs Module","Parameters Module","Parser Module","Testing Module","Utils Module","CLI Command Parser"],titleterms:{action:0,arg:1,cli:13,command:[3,13],command_paramet:2,config:4,error_handl:5,except:6,format:7,indic:13,modul:[0,1,2,3,4,5,6,7,8,9,10,11,12],narg:8,paramet:9,parser:[10,13],tabl:13,test:11,util:12}})