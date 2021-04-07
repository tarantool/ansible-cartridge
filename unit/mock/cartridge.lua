local console = require('console')
local checks = require('checks')

local cartridge = {}
cartridge.internal = {}

local cartridge_roles = {}
package.loaded['cartridge.roles'] = cartridge_roles

local cartridge_vshard_utils = {}
package.loaded['cartridge.vshard-utils'] = cartridge_vshard_utils

local cartridge_webui_auth = {}
package.loaded['cartridge.webui.api-auth'] = cartridge_webui_auth

local cartridge_admin = {}
package.loaded['cartridge.admin'] = cartridge_admin

-- local cartridge_failover_lib = require('cartridge.failover')
local cartridge_failover= {}
package.loaded['cartridge.failover'] = cartridge_failover

local membership = {}
package.loaded['membership'] = membership

local confapplier = {}
package.loaded['cartridge.confapplier'] = confapplier

local cartridge_roles_vshard_router = {}
package.loaded['cartridge.roles.vshard-router'] = cartridge_roles_vshard_router

local cartridge_twophase = {}
package.loaded['cartridge.twophase'] = cartridge_twophase

local cartridge_auth_lib = require('cartridge.auth')
local cartridge_auth = {}
package.loaded['cartridge.auth'] = cartridge_auth

local errors = require('errors')
local CARTRIDGE_ERR = errors.new('CartridgeError', 'cartridge err')

local vars = {
    can_bootstrap_vshard = true,
    vshard_groups = {},
    webui_auth_params = {},
    users = {},
    membership_myself = {},
    membership_members = {},
    known_servers = {},
    user_has_version = true,
    cartridge_confapplier_state = '',
    unknown_buckets = {},
    roles_map = {},

    -- see below
    -- clusterwide_config = clusterwide_config.new(),
}

local fail_on = {}
local calls = {}

local function table_pack(...)
    return { n = select("#", ...), ... }
end

local function wrap_func(name, func)
    local function wrapper(...)
        local call = {}

        local args = table_pack(...)
        for i=1,args.n do
            call[i] = args[i]
        end

        call = table.deepcopy(call)

        if args.n == 1 then
            call = call[1]
        end
        calls[name] = calls[name] or {}
        table.insert(calls[name], call)

        if fail_on[name] then
            return nil, CARTRIDGE_ERR
        end

        return func(...)
    end

    return wrapper
end


-- * --------------- Module cartridge.webui.api-auth ---------------

function cartridge_webui_auth.get_auth_params()
    return vars.webui_auth_params
end

-- * --------------- Module cartridge.confapplier ------------------

function confapplier.get_state()
    return vars.cartridge_confapplier_state
end

function confapplier.get_readonly(section)
    return vars.clusterwide_config:get_readonly(section)
end

function confapplier.get_deepcopy(section)
    return vars.clusterwide_config:get_deepcopy(section)
end

function confapplier.get_active_config()
    return vars.clusterwide_config
end

function confapplier.validate_config()
    return true
end

function confapplier.wish_state(state)
    vars.cartridge_confapplier_state = state
    return state
end

-- * ----------------- Module cartridge.twophase -------------------

function cartridge_twophase.patch_clusterwide(patch)
    local new_clusterwide_config = vars.clusterwide_config:copy()
    for k, v in pairs(patch) do
        new_clusterwide_config:set_plaintext(k .. ".yml", require('yaml').encode(v))
    end

    new_clusterwide_config:update_luatables()

    local new_topology = new_clusterwide_config:get_readonly('topology')

    if new_topology ~= nil then
        for uuid, srv in pairs(new_topology.servers or {}) do
            if srv ~= 'expelled' then
                local member = vars.membership_members[srv.uri]
                if member == nil then
                    return nil, string.format('Server %s is not found in membership', srv.uri)
                end

                if srv.replicaset_uuid ~= nil and member.payload.uuid == nil then
                    member.payload.uuid = uuid
                    member.payload.state = 'RolesConfigured'
                end
            end
        end
    end

    vars.clusterwide_config = new_clusterwide_config

    return true
end

-- * ----------------- Module cartridge.roles -------------------

function cartridge_roles.get_known_roles()
    local known_roles = {}
    for role_name in pairs(vars.roles_map) do
        table.insert(known_roles, role_name)
    end
    return known_roles
end

function cartridge_roles.get_enabled_roles(rpl_roles)
    local enabled_roles = {}

    for k, v in pairs(rpl_roles) do
        local role_name
        if type(k) == 'number' and type(v) == 'string' then
            role_name = v
        else
            role_name = k
        end

        enabled_roles[role_name] = true
    end

    return enabled_roles
end

-- * ---------------------- Module membership ----------------------

membership.myself = wrap_func('membership_myself', function()
    return vars.membership_myself
end)

function membership.members()
    local members = {}
    for uri, member in pairs(vars.membership_members) do
        members[uri] = member
    end
    return members
end

function membership.subscribe()
    return require('fiber').cond()
end

function membership.get_member(uri)
    return membership.members()[uri]
end

local clusterwide_config = require('cartridge.clusterwide-config')
local lua_api_topology = require('cartridge.lua-api.topology')


-- * ---------------------- Vshard router --------------------------

local function vshard_router_info(self)
    return {
        bucket = {
            unknown = vars.unknown_buckets[self.group_name]
        }
    }
end

function cartridge_roles_vshard_router.get(group_name)
    if vars.unknown_buckets[group_name] == nil then
        return nil
    end

    return {
        group_name = group_name,
        info = vshard_router_info,
    }
end

-- * ------------------------- box.cfg -------------------------

-- box.cfg mock
local mt = {}
mt.__call = function(self, opts)
    calls.box_cfg = calls.box_cfg or {}
    table.insert(calls.box_cfg, opts)

    for _, memory_size_param in ipairs({'memtx_memory', 'vinyl_memory'}) do
        if opts[memory_size_param] ~= nil then
            if self[memory_size_param] == nil then
                self[memory_size_param] = opts[memory_size_param]
            end

            if opts[memory_size_param] == self[memory_size_param] then
                return
            end

            if opts[memory_size_param] < self[memory_size_param] then
                error("cannot decrease memory size at runtime")
            end

            if fail_on.increase_memory_size then
                error("cannot decrease memory size at runtime")
            end

            self[memory_size_param] = opts[memory_size_param]
        end
    end

    for k, v in pairs(opts) do
        if k ~= 'memtx_memory' and k ~= 'vinyl_memory' then
            self[k] = v
        end
    end
end

local box_cfg_table = {}
setmetatable(box_cfg_table, mt)

local box_cfg_function = function() end

box.cfg = box_cfg_function

function cartridge.internal.set_box_cfg_function(value)
    assert(type(value) == 'boolean')
    if value then
        box.cfg = box_cfg_function
    else
        box.cfg = box_cfg_table
    end
end

function cartridge.internal.set_box_cfg(params)
    table.clear(box_cfg_table)

    for k, v in pairs(params) do
        box_cfg_table[k] = v
    end
end

-- * ------------------ Cartridge module functions ------------------

cartridge.version = '2.1.2'

function cartridge.is_healthy()
    return true
end

function cartridge.cfg(opts)
    assert(type(opts.console_sock == 'string'))

    local ok, err = pcall(console.listen, 'unix/:' .. opts.console_sock)
    assert(ok, err)

    box.cfg = box_cfg_table

    return true
end

function cartridge.admin_probe_server(advertise_uri)
    assert(type(advertise_uri) == 'string')

    table.insert(calls.admin_probe_server, advertise_uri)

    if vars.known_servers[advertise_uri] then
        return true
    end

    return false, string.format('Probe %q failed', advertise_uri)
end

-- cartridge modules
vars.clusterwide_config = clusterwide_config.new()

cartridge.admin_get_servers = lua_api_topology.get_servers
cartridge.admin_get_replicasets = lua_api_topology.get_replicasets

cartridge.admin_edit_topology = wrap_func('edit_topology', function(opts)
    -- set prettyfied uuids for join servers
    for _, replicaset in ipairs(opts.replicasets or {}) do
        for _, join_server in ipairs(replicaset.join_servers or {}) do
            if join_server.uuid == nil then
                local member = membership.get_member(join_server.uri)
                assert(member ~= nil, string.format('Member %s is not found', join_server.uri))
                join_server.uuid = string.format('%s-uuid', member.payload.alias)
            end
        end
    end

    return lua_api_topology.edit_topology(opts)
end)

cartridge.config_get_readonly = confapplier.get_readonly

cartridge.config_patch_clusterwide = wrap_func(
    'config_patch_clusterwide',
    cartridge_twophase.patch_clusterwide
)

-- * -------------------------- Failover --------------------------

cartridge_failover.get_active_leaders = function()
    return vars.active_leaders or {}
end

local lua_api_failover = require('cartridge.lua-api.failover')

cartridge.failover_get_params = lua_api_failover.get_params
cartridge.admin_get_failover = lua_api_failover.get_failover_enabled

local admin_manage_failover = wrap_func('manage_failover', lua_api_failover.set_failover_enabled)

function cartridge.admin_enable_failover()
    return admin_manage_failover(true)
end

function cartridge.admin_disable_failover()
    return admin_manage_failover(false)
end

cartridge.failover_set_params = wrap_func(
    'failover_set_params', lua_api_failover.set_params
)

cartridge.failover_promote = wrap_func(
    'failover_promote', function(replicaset_leaders)
        vars.active_leaders = vars.active_leaders or {}
        for rpl_uuid, instannce_uuid in pairs(replicaset_leaders) do
            vars.active_leaders[rpl_uuid] = instannce_uuid
        end
    end
)

-- * ---------------- Module cartridge.vshard-utils ---------------

function cartridge_vshard_utils.can_bootstrap()
    return vars.can_bootstrap_vshard
end

function cartridge_vshard_utils.get_known_groups()
    return vars.vshard_groups
end

function cartridge_vshard_utils.validate_config()
    return true
end

-- * ------------------- Module cartridge.admin -------------------

cartridge_admin.bootstrap_vshard = wrap_func('bootstrap_vshard', function()
    return true
end)

-- * ------------------- Module cartridge.auth -------------------

for func_name, func in pairs(cartridge_auth_lib) do
    cartridge_auth[func_name] = func
end

cartridge_auth.set_params = wrap_func('auth_set_params', cartridge_auth_lib.set_params)

local add_user_callback = wrap_func('auth_add_user', function(username, _, fullname, email)
    local user = {
        username = username,
        fullname= fullname,
        email = email,
    }

    if vars.user_has_version then
        user.version = 1
    end

    vars.users[user.username] = user
    return user
end)

local get_user_callback = wrap_func('auth_get_user', function(username)
    local user = vars.users[username]
    if user == nil then
        return nil, string.format('User %q not found', username)
    end

    return user
end)

local edit_user_callback = wrap_func('auth_edit_user', function(username, _, fullname, email)
    local user = vars.users[username]
    if user == nil then
        return nil, string.format('User %q not found', username)
    end

    if fullname ~= nil then
        user.fullname = fullname
    end

    if email ~= nil then
        user.email = email
    end

    if user.version ~= nil then
        user.version = user.version + 1
    end

    return user
end)

local list_users_callback = function()
    local users_list = {}

    for _, user in pairs(vars.users) do
        table.insert(users_list, user)
    end

    return users_list
end

local remove_user_callback = wrap_func('auth_remove_user', function(username)
    local user = cartridge_auth.get_user(username)
    if user == nil then
        return nil, string.format('User %q not found', username)
    end

    vars.users[username] = nil

    return user
end)

cartridge_auth.set_callbacks({
    add_user = add_user_callback,
    get_user = get_user_callback,
    edit_user = edit_user_callback,
    list_users = list_users_callback,
    remove_user = remove_user_callback,
})

-- * ----------------------- Internal helpers ----------------------

function cartridge.internal.add_membership_members(specified_members)
    for _, m in ipairs(specified_members) do
        assert(m.uri ~= nil)
        local member = {
            uri = m.uri,
            status = m.status or 'alive',
            incarnation = 1,
        }

        if not member.no_payload then
            member.payload = {
                uuid = m.uuid,
                alias = m.alias,
            }
        end

        vars.membership_members[m.uri] = member
    end
end

function cartridge.internal.add_replicaset(rpl)
    checks({
        alias = 'string',
        instances = 'table',
        roles = '?table',
        all_rw = '?boolean',
        weight = '?number',
        vshard_group = '?string',
    })

    -- add membership memebrs
    local new_members = {}
    for _, alias in ipairs(rpl.instances) do
        table.insert(new_members, {
            alias = alias,
            uri = string.format('%s-uri', alias),
        })
    end
    cartridge.internal.add_membership_members(new_members)

    local join_servers = {}
    for _, member in ipairs(new_members) do
        table.insert(join_servers, {
            uri = member.uri,
            uuid = string.format('%s-uuid', member.alias),
        })
    end

    -- add roles
    for _, role in ipairs(rpl.roles or {}) do
        vars.roles_map[role] = true
    end

    -- call edit_topology
    local _, err = lua_api_topology.edit_topology({
        replicasets = {
            {
                alias = rpl.alias,
                uuid = string.format('%s-uuid', rpl.alias),
                join_servers = join_servers,
                roles = rpl.roles,
                all_rw = rpl.all_rw,
                weight = rpl.weight,
                vshard_group = rpl.vshard_group,
            },
        }
    })

    assert(err == nil, tostring(err))
end

function cartridge.internal.bootstrap_cluster()
    local _, err = cartridge.internal.add_replicaset({
        alias='r1',
        instances = {'instance-1'},
    })
    assert(err == nil, tostring(err))
end

function cartridge.internal.set_auth(auth_cfg)
    local patch = {
        auth = auth_cfg,
    }

    local _, err = cartridge_twophase.patch_clusterwide(patch)
    assert(err == nil, tostring(err))
end

function cartridge.internal.set_users(users)
    vars.users = {}
    for _, user in ipairs(users) do
        vars.users[user.username] = user
    end
end

function cartridge.internal.set_failover_params(params)
    local _, err = lua_api_failover.set_params(params)
    assert(err == nil, tostring(err))
end

function cartridge.internal.set_config(new_config)
    vars.clusterwide_config = clusterwide_config.new()
    local _, err = cartridge_twophase.patch_clusterwide(new_config)
    assert(err == nil, tostring(err))
end

-- * ----------------------- functions calls -----------------------

function cartridge.internal.set_fail(func, value)
    assert(type(value) == 'boolean')
    fail_on[func] = value
end

function cartridge.internal.clear_calls(func)
    calls[func] = {}
end

function cartridge.internal.get_calls(func)
    return calls[func] or {}
end

-- * --------------------------- vars ---------------------------

function cartridge.internal.set_variable(name, value)
    vars[name] = value
end

cartridge.internal.vars = vars

return cartridge
