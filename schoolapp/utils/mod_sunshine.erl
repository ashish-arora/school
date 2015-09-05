-module(mod_sunshine).

-behavior(gen_mod).

-include("ejabberd.hrl").

-export([start/2, stop/1, on_presence/4, on_unset/4]).

start(Host, _Opts) ->
    ?INFO_MSG("mod_sunshine starting", []),
    ejabberd_hooks:add(set_presence_hook, Host, ?MODULE, on_presence, 50),
    ejabberd_hooks:add(unset_presence_hook, Host, ?MODULE, on_unset, 50),
    ok.

stop(Host) ->
    ?INFO_MSG("mod_sunshine stopping", []),
    ejabberd_hooks:delete(set_presence_hook, Host, ?MODULE, on_presence, 50),
    ejabberd_hooks:add(unset_presence_hook, Host, ?MODULE, on_unset, 50),
    ok.

on_presence(_User, _Server, _Resource, _Packet) ->
    ?INFO_MSG("mod_sunshine on presence called by User : ~p", [_User]),
    ?INFO_MSG("mod_sunshine on presence called with resource : ~p", [_Resource]),
    OsReturn = os:cmd("/usr/bin/python /srv/Kevent/apps/manage.py on_jabber_logout " ++ "presence " ++ _User ++ " " ++ _Resource),
    ?INFO_MSG("Send to handler and got return ~s", [OsReturn]),
    none.

on_unset(_User, _Server, _Resource, _Packet) ->
    ?INFO_MSG("mod_sunshine on unset called by User : ~p", [_User]),
    ?INFO_MSG("mod_sunshine on unset called with resource : ~p", [_Resource]),
    OsReturn = os:cmd("/usr/bin/python /srv/Kevent/apps/manage.py on_jabber_logout " ++ "unset " ++ _User ++ " " ++ _Resource),
    ?INFO_MSG("Send to handler and got return ~s", [OsReturn]),
    none.