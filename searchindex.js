Search.setIndex({docnames:["command_parser.actions","command_parser.args","command_parser.commands","command_parser.config","command_parser.error_handling","command_parser.exceptions","command_parser.formatting","command_parser.nargs","command_parser.parameters","command_parser.parser","command_parser.testing","command_parser.utils","index"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":4,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.intersphinx":1,"sphinx.ext.viewcode":1,sphinx:56},filenames:["command_parser.actions.rst","command_parser.args.rst","command_parser.commands.rst","command_parser.config.rst","command_parser.error_handling.rst","command_parser.exceptions.rst","command_parser.formatting.rst","command_parser.nargs.rst","command_parser.parameters.rst","command_parser.parser.rst","command_parser.testing.rst","command_parser.utils.rst","index.rst"],objects:{"command_parser.actions":[[0,1,1,"","help_action"]],"command_parser.args":[[1,2,1,"","Args"]],"command_parser.args.Args":[[1,3,1,"","action_flags"],[1,3,1,"","after_main_actions"],[1,3,1,"","before_main_actions"],[1,4,1,"","find_all"],[1,4,1,"","num_provided"],[1,4,1,"","record_action"]],"command_parser.args.Args.params":[[1,5,1,"","args"]],"command_parser.commands":[[2,2,1,"","Command"]],"command_parser.commands.Command":[[2,4,1,"","__init_subclass__"],[2,4,1,"","after_main"],[2,6,1,"","args"],[2,4,1,"","before_main"],[2,3,1,"","command_config"],[2,4,1,"","main"],[2,4,1,"","parse"],[2,4,1,"","parse_and_run"],[2,3,1,"","parser"],[2,4,1,"","run"]],"command_parser.commands.Command.__init_subclass__.params":[[2,5,1,"","abstract"],[2,5,1,"","action_after_action_flags"],[2,5,1,"","add_help"],[2,5,1,"","allow_missing"],[2,5,1,"","allow_unknown"],[2,5,1,"","choice"],[2,5,1,"","description"],[2,5,1,"","epilog"],[2,5,1,"","error_handler"],[2,5,1,"","help"],[2,5,1,"","multiple_action_flags"],[2,5,1,"","prog"],[2,5,1,"","usage"]],"command_parser.commands.Command.after_main.params":[[2,5,1,"","args"],[2,5,1,"","kwargs"]],"command_parser.commands.Command.before_main.params":[[2,5,1,"","args"],[2,5,1,"","kwargs"]],"command_parser.commands.Command.main.params":[[2,5,1,"","args"],[2,5,1,"","kwargs"]],"command_parser.commands.Command.parse.params":[[2,5,1,"","args"]],"command_parser.commands.Command.parse_and_run.params":[[2,5,1,"","args"],[2,5,1,"","argv"],[2,5,1,"","kwargs"]],"command_parser.commands.Command.run.params":[[2,5,1,"","args"],[2,5,1,"","kwargs"]],"command_parser.config":[[3,2,1,"","CommandConfig"]],"command_parser.config.CommandConfig":[[3,6,1,"","action_after_action_flags"],[3,6,1,"","add_help"],[3,6,1,"","allow_missing"],[3,6,1,"","allow_unknown"],[3,4,1,"","as_dict"],[3,6,1,"","error_handler"],[3,6,1,"","multiple_action_flags"]],"command_parser.error_handling":[[4,2,1,"","ErrorHandler"],[4,2,1,"","NullErrorHandler"]],"command_parser.error_handling.ErrorHandler":[[4,4,1,"","cls_handler"],[4,4,1,"","copy"],[4,4,1,"","get_handler"],[4,4,1,"","register"],[4,4,1,"","unregister"]],"command_parser.exceptions":[[5,7,1,"","BadArgument"],[5,7,1,"","CommandDefinitionError"],[5,7,1,"","CommandParserException"],[5,7,1,"","InvalidChoice"],[5,7,1,"","MissingArgument"],[5,7,1,"","NoSuchOption"],[5,7,1,"","ParamConflict"],[5,7,1,"","ParamUsageError"],[5,7,1,"","ParameterDefinitionError"],[5,7,1,"","ParamsMissing"],[5,7,1,"","ParserExit"],[5,7,1,"","UsageError"]],"command_parser.exceptions.CommandParserException":[[5,6,1,"","code"],[5,4,1,"","exit"],[5,4,1,"","show"]],"command_parser.exceptions.MissingArgument":[[5,6,1,"","message"]],"command_parser.exceptions.ParamConflict":[[5,6,1,"","message"]],"command_parser.exceptions.ParamUsageError":[[5,6,1,"","message"]],"command_parser.exceptions.ParamsMissing":[[5,6,1,"","message"]],"command_parser.formatting":[[6,2,1,"","HelpFormatter"]],"command_parser.formatting.HelpFormatter":[[6,4,1,"","format_help"],[6,4,1,"","format_usage"],[6,4,1,"","maybe_add"]],"command_parser.nargs":[[7,2,1,"","Nargs"]],"command_parser.nargs.Nargs":[[7,4,1,"","satisfied"]],"command_parser.parameters":[[8,2,1,"","Action"],[8,2,1,"","ActionFlag"],[8,2,1,"","BaseOption"],[8,2,1,"","BasePositional"],[8,2,1,"","Counter"],[8,2,1,"","Flag"],[8,2,1,"","Option"],[8,2,1,"","ParamGroup"],[8,2,1,"","Parameter"],[8,2,1,"","PassThru"],[8,2,1,"","Positional"],[8,2,1,"","SubCommand"],[8,6,1,"","action_flag"],[8,8,1,"","after_main"],[8,8,1,"","before_main"]],"command_parser.parameters.Action":[[8,4,1,"","register"],[8,4,1,"","register_action"]],"command_parser.parameters.Action.register.params":[[8,5,1,"","choice"],[8,5,1,"","help"],[8,5,1,"","method_or_choice"]],"command_parser.parameters.ActionFlag":[[8,3,1,"","func"],[8,4,1,"","result"]],"command_parser.parameters.BaseOption":[[8,4,1,"","format_basic_usage"],[8,4,1,"","format_usage"],[8,3,1,"","long_opts"],[8,6,1,"","short_combinable"],[8,3,1,"","short_opts"]],"command_parser.parameters.BasePositional":[[8,4,1,"","format_basic_usage"],[8,4,1,"","format_usage"]],"command_parser.parameters.Counter":[[8,6,1,"","accepts_none"],[8,6,1,"","accepts_values"],[8,4,1,"","append"],[8,6,1,"","nargs"],[8,4,1,"","prepare_value"],[8,4,1,"","result"],[8,4,1,"","result_value"],[8,6,1,"","type"],[8,4,1,"","validate"]],"command_parser.parameters.Flag":[[8,6,1,"","accepts_none"],[8,6,1,"","accepts_values"],[8,4,1,"","append_const"],[8,6,1,"","nargs"],[8,4,1,"","result"],[8,4,1,"","result_value"],[8,4,1,"","store_const"],[8,4,1,"","would_accept"]],"command_parser.parameters.Option":[[8,4,1,"","append"],[8,4,1,"","store"]],"command_parser.parameters.ParamGroup":[[8,4,1,"","active_group"],[8,4,1,"","add"],[8,6,1,"","description"],[8,4,1,"","format_description"],[8,4,1,"","format_help"],[8,4,1,"","format_usage"],[8,6,1,"","members"],[8,6,1,"","mutually_dependent"],[8,6,1,"","mutually_exclusive"],[8,4,1,"","register"],[8,4,1,"","register_all"],[8,3,1,"","show_in_help"],[8,4,1,"","validate"]],"command_parser.parameters.ParamGroup.format_help.params":[[8,5,1,"","add_default"],[8,5,1,"","clean"],[8,5,1,"","group_type"],[8,5,1,"","width"]],"command_parser.parameters.Parameter":[[8,4,1,"","__init_subclass__"],[8,6,1,"","accepts_none"],[8,6,1,"","accepts_values"],[8,6,1,"","choices"],[8,4,1,"","format_help"],[8,4,1,"","format_usage"],[8,4,1,"","is_valid_arg"],[8,6,1,"","metavar"],[8,6,1,"","nargs"],[8,4,1,"","prepare_value"],[8,4,1,"","result"],[8,4,1,"","result_value"],[8,3,1,"","show_in_help"],[8,4,1,"","take_action"],[8,6,1,"","type"],[8,3,1,"","usage_metavar"],[8,4,1,"","validate"],[8,4,1,"","would_accept"]],"command_parser.parameters.PassThru":[[8,4,1,"","format_basic_usage"],[8,6,1,"","nargs"],[8,4,1,"","store_all"],[8,4,1,"","take_action"]],"command_parser.parameters.Positional":[[8,4,1,"","append"],[8,4,1,"","store"]],"command_parser.parameters.SubCommand":[[8,4,1,"","register"],[8,4,1,"","register_command"]],"command_parser.parameters.SubCommand.register.params":[[8,5,1,"","choice"],[8,5,1,"","command_or_choice"],[8,5,1,"","help"]],"command_parser.parser":[[9,2,1,"","CommandParser"]],"command_parser.parser.CommandParser":[[9,6,1,"","action"],[9,6,1,"","action_flags"],[9,4,1,"","arg_dict"],[9,6,1,"","command"],[9,6,1,"","command_parent"],[9,6,1,"","formatter"],[9,4,1,"","get_params"],[9,4,1,"","get_sub_command_params"],[9,6,1,"","groups"],[9,4,1,"","has_pass_thru"],[9,6,1,"","long_options"],[9,6,1,"","options"],[9,6,1,"","parent"],[9,4,1,"","parse_args"],[9,6,1,"","pass_thru"],[9,6,1,"","positionals"],[9,6,1,"","short_combinable"],[9,6,1,"","short_options"],[9,6,1,"","sub_command"]],"command_parser.parser.CommandParser.get_params.params":[[9,5,1,"","args"],[9,5,1,"","item"]],"command_parser.testing":[[10,2,1,"","ParserTest"]],"command_parser.testing.ParserTest":[[10,4,1,"","assert_call_fails"],[10,4,1,"","assert_call_fails_cases"],[10,4,1,"","assert_parse_fails"],[10,4,1,"","assert_parse_fails_cases"],[10,4,1,"","assert_parse_results"],[10,4,1,"","assert_parse_results_cases"]],"command_parser.utils":[[11,2,1,"","ProgramMetadata"],[11,1,1,"","camel_to_snake_case"],[11,2,1,"","classproperty"],[11,1,1,"","format_help_entry"],[11,1,1,"","get_descriptor_value_type"],[11,1,1,"","is_numeric"],[11,1,1,"","validate_positional"]],"command_parser.utils.ProgramMetadata":[[11,4,1,"","format_epilog"]],command_parser:[[0,0,0,"-","actions"],[1,0,0,"-","args"],[2,0,0,"-","commands"],[3,0,0,"-","config"],[4,0,0,"-","error_handling"],[5,0,0,"-","exceptions"],[6,0,0,"-","formatting"],[7,0,0,"-","nargs"],[8,0,0,"-","parameters"],[9,0,0,"-","parser"],[10,0,0,"-","testing"],[11,0,0,"-","utils"]]},objnames:{"0":["py","module","Python module"],"1":["py","function","Python function"],"2":["py","class","Python class"],"3":["py","property","Python property"],"4":["py","method","Python method"],"5":["py","parameter","Python parameter"],"6":["py","attribute","Python attribute"],"7":["py","exception","Python exception"],"8":["py","data","Python data"]},objtypes:{"0":"py:module","1":"py:function","2":"py:class","3":"py:property","4":"py:method","5":"py:parameter","6":"py:attribute","7":"py:exception","8":"py:data"},terms:{"0":[2,8],"0x7fa923a2c3d0":3,"1":[1,8],"2":[5,11],"3":2,"30":[6,8,11],"abstract":2,"break":3,"case":[8,10],"class":[1,2,3,4,5,6,7,8,9,10,11],"const":8,"default":[1,2,3,8],"do":[2,8,11],"final":2,"float":8,"int":[1,2,5,6,7,8,11],"return":[2,3,8,9,11],"super":2,"true":[2,3,6,8,11],"while":11,A:[2,8,11],If:[2,8],It:8,The:[1,2,3,8,9],To:2,_:11,__init__:2,__init_subclass__:[2,8],_notset:3,abc:8,abl:2,abov:[2,11],accepts_non:8,accepts_valu:8,accomplish:11,action:[1,2,3,8,9],action_after_action_flag:[2,3],action_flag:[1,2,3,8,9],actionflag:[1,2,8,9],active_group:8,ad:[2,3],add:8,add_default:[6,8],add_help:[2,3],after:[1,2,8,11],after_main:[2,8],after_main_act:1,again:11,alia:8,all:[2,3,5],allow:[2,3,8],allow_miss:[2,3,9],allow_unknown:[2,3,9],alreadi:2,also:8,altern:2,an:[2,3,5,8,9],ani:[1,2,3,5,6,8,9,10,11],append:8,append_const:8,appli:11,ar:[2,3,8],arg:[2,8,9],arg_dict:9,argument:[1,2,3,5,8,9],argv:[1,2,10],as_dict:3,asdict:3,assert_call_fail:10,assert_call_fails_cas:10,assert_parse_fail:10,assert_parse_fails_cas:10,assert_parse_result:10,assert_parse_results_cas:10,associ:2,attr:11,author:[0,1,2,3,4,5,6,7,8,9,10,11],auto:2,automat:8,back:8,badargu:5,base:[1,2,3,4,5,6,7,8,9,10,11],baseexcept:4,baseopt:[8,9],baseposit:[8,9],becaus:3,befor:[1,2,8],before_main:[2,8],before_main_act:1,behavior:3,being:2,bool:[2,3,6,7,8,9,11],call:[2,8],callabl:[4,8,10,11],camel_to_snake_cas:11,camelcas:8,can:2,caus:5,checker:11,choic:[2,5,8,11],choicemap:8,chosen:8,classmethod:[2,4,8,11],classproperti:11,clean:8,cli:[2,3],cls_handler:4,cmd_cl:10,code:[2,5],collect:[5,8,9],column:8,combin:[2,3,5,8],command:[3,5,6,8,9,10],command_cl:11,command_config:2,command_or_choic:8,command_par:9,command_pars:[0,1,2,3,4,5,6,7,8,9,10,11],commandconfig:[2,3],commanddefinitionerror:5,commandobj:2,commandpars:[2,6,9],commandparserexcept:5,commandtyp:[6,8,9,10],common:[0,2],config:2,configur:[2,3],confus:11,consid:2,contain:[2,8,9],convert:8,copi:[3,4],core:2,correctli:5,could:11,count:7,counter:8,dataclass:3,declar:11,decor:[2,8,11],defin:[2,5],delim:[6,8,11],depend:8,descript:[2,8,11],determin:8,dict:[1,3,9,10],did:11,directli:8,displai:[2,8],docs_url:11,document:11,doe:[2,5,8],doug:[0,1,2,3,4,5,6,7,8,9,10,11],dure:[1,2,8],email:11,encount:[2,3],entri:2,epilog:[2,11],error:[2,5],error_handl:[2,3],errorhandl:[2,3,4],exc:[4,10,11],exc_typ:4,except:[2,3,4,10,11],exclud:9,exclus:[5,8],execut:8,exit:5,expect:10,expected_exc:10,expected_pattern:10,explicitli:8,extend:[2,8,11],extended_epilog:6,fals:[2,3,8,9],far:2,find_al:1,first:8,flag:8,follow:2,format:[8,9],format_basic_usag:8,format_descript:8,format_epilog:11,format_help:[6,8],format_help_entri:11,format_usag:[6,8],formatt:9,forwardref:[3,8],from:[2,8],full:8,func:[8,10,11],functool:8,further:8,gener:2,get_descriptor_value_typ:11,get_handl:4,get_param:9,get_sub_command_param:9,given:[2,3,5,8],group:[8,9],group_typ:[6,8],h:[2,3],handl:2,handler:[2,4],has_pass_thru:9,have:2,help:[2,3,8],help_act:0,helper:10,helpformatt:[6,9],here:[2,8],hide:8,ignor:2,implement:[8,11],includ:[8,11],include_meta:8,index:12,initi:[2,8],instanc:2,instanti:8,instead:2,intend:2,interpret:8,invalid:5,invalidchoic:5,invoc:[2,3],is_numer:11,is_valid_arg:8,item:9,iter:[1,8,10],its:11,keep:1,keyword:[2,8],kwarg:[2,8,10],level:2,list:[8,9,10],long_opt:[8,9],lpad:11,mai:[2,8],main:[1,2,8],map:2,match:[5,9],maybe_add:6,mean:11,member:8,mention:2,messag:[2,5,10],metavar:8,method:[2,3,8,11],method_or_choic:8,methodnam:10,miss:[2,3,5],missingargu:5,modul:12,more:5,multipl:[2,3],multiple_action_flag:[2,3],mutual:[5,8],mutually_depend:8,mutually_exclus:8,name:[2,8],narg:8,necessari:[2,3,8],need:[2,8],non:3,none:[2,3,5,8,9,10,11],nosuchopt:5,noth:8,nullerrorhandl:4,num_provid:1,number:2,object:[1,2,3,4,6,7,8,9,11],omit:8,one:5,onli:[8,11],option:[1,2,3,4,5,8,9,10,11],option_str:8,order:[2,8],origin:8,other:[2,5,8],otherwis:9,overrid:2,overridden:8,page:12,param:[1,5,6,8],param_cl:11,param_typ:1,parambas:8,paramconflict:5,paramet:[1,2,5,9],parameterdefinitionerror:[5,11],paramgroup:[6,8,9],paramorgroup:[1,5],paramsmiss:5,paramusageerror:5,parent:[2,8,9],pars:[1,2,8,9],parse_and_run:2,parse_arg:9,parser:[2,5,6],parserexit:5,parsertest:10,partial:[8,9],pass:2,pass_thru:9,passthru:[8,9],pattern:10,place:2,point:2,posit:[2,3,8,9],possibl:2,pre:5,prefix:11,prepar:8,prepare_valu:8,prevent:2,primari:[2,8],prog:[2,11],program:2,programmetadata:11,properli:11,properti:[1,2,8,11],provid:[5,8],pycharm:11,rais:[2,3,5],rang:[7,8],raw:[1,9],read:11,readi:2,recogn:11,record_act:1,refer:[2,8],regist:[2,4,8],register_act:8,register_al:8,register_command:8,repres:3,requir:[2,3,5,8,11],resolv:2,result:[2,8],result_valu:8,run:[2,3],runtest:10,s:[2,9,11],satisfi:7,search:12,self:0,sentinel:3,separ:[2,11],sequenc:[1,2,7,8],set:[2,7,8],short_combin:[8,9],short_combo:8,short_opt:[8,9],should:[1,2,3,8],show:5,show_in_help:8,skip:2,skrypa:[0,1,2,3,4,5,6,7,8,9,10,11],snake_cas:8,so:[2,8,11],sourc:[0,1,2,3,4,5,6,7,8,9,10,11],specifi:[2,3,8],sphinx:11,stack:11,statu:5,store:[1,2,8],store_al:8,store_const:8,str:[1,2,3,5,6,7,8,9,10,11],string:[8,9],sub:2,sub_command:9,subclass:[2,8],subcommand:[2,8,9],sy:[1,2],take_act:8,taken:[1,2],target:2,testcas:10,text:[2,8,11],thei:[2,3],them:8,thi:[2,3,8,9,11],titl:8,top:2,total:2,track:1,trigger:2,tupl:[7,8,9,10],type:[1,4,8,10,11],unchang:8,union:[2,3,6,7,8,9,10,11],unit:10,unknown:[2,3],unregist:4,url:11,us:[2,3,5,8],usag:[2,8,11],usage_metavar:8,usageerror:[5,10],user:5,val_count:1,valid:[2,8],validate_posit:11,valu:[2,3,5,8,11],version:[8,11],via:2,virtual:8,wa:[2,3,5,8],wai:8,were:[1,2,5],what:2,when:[2,3,5,8,11],whether:[2,3,8],which:[2,3,8],width:[6,8,11],without:8,would_accept:8,wrap:[2,8],you:2},titles:["Actions Module","Args Module","Commands Module","Config Module","Error_Handling Module","Exceptions Module","Formatting Module","Nargs Module","Parameters Module","Parser Module","Testing Module","Utils Module","Command Parser"],titleterms:{action:0,arg:1,command:[2,12],config:3,error_handl:4,except:5,format:6,indic:12,modul:[0,1,2,3,4,5,6,7,8,9,10,11],narg:7,paramet:8,parser:[9,12],tabl:12,test:10,util:11}})