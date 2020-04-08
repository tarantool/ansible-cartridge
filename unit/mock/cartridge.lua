local console = require('console')

local cartridge = {}
cartridge.internal = {}

local cartridge_vshard_utils = {}
package.loaded['cartridge.vshard-utils'] = cartridge_vshard_utils

local cartridge_auth = {}
package.loaded['cartridge.auth'] = cartridge_auth

local cartridge_webui_auth = {}
package.loaded['cartridge.webui.api-auth'] = cartridge_webui_auth

local cartridge_admin = {}
package.loaded['cartridge.admin'] = cartridge_admin

local membership = {}
membership.internal = {}
package.loaded['membership'] = membership


local CARTRIDGE_ERR = 'cartridge err'

local fail_on = {
    increase_memtx_memory = false,
    edit_topology = false,
    bootstrap_vshard = false,
    config_patch_clusterwide = false,
    manage_failover = false,
    auth_set_params = false,
    auth_add_user = false,
    auth_edit_user = false,
    auth_remove_user = false,
}

local calls = {
    increase_memtx_memory = {},
    edit_topology = {},
    bootstrap_vshard = {},
    config_patch_clusterwide = {},
    manage_failover = {},
    auth_set_params = {},
    auth_add_user = {},
    auth_edit_user = {},
    auth_remove_user = {},
    admin_probe_server = {},
    box_cfg = {},
}

local vars = {
    config = {},
    failover = false,
    can_bootstrap_vshard = true,
    auth_params = {},
    webui_auth_params = {},
    users = {},
    membership_myself = {},
    membership_members = {},
    known_servers = {},
    become_unhealthy_after_edit = false,
}

local topology = {
    replicasets = {
        --[[
            ['r1-uuid'] = {
                uuid = 'r1-uuid',
                alias = 'r1',
                status = 'healthy',
                roles = {'role-1', 'role-2'},
                all_rw = true,
                weight = 100,
                servers = {{alias = 'r1-master', priority = 1}},
            }
        --]]
    },
    servers = {
        --[[
            ['r1-master-uuid'] = {
                uuid = 'r1-master-uuid',
                uri = 'r1-master-uri',
                alias = 'r1-master',
                status = 'healthy',
                replicaset = {uuid = 'r1-uuid', alias = 'r1', roles = {'role-1', 'role-2'}}
            }
        --]]
    },
}

local unjoined_servers = {
    --[[
    {
        uuid = 'r1-master-uuid',
        uri = 'r1-master-uri',
        alias = 'r1-master',
        status = 'healthy',
        replicaset = {uuid = 'r1-uuid', alias = 'r1', roles = {'role-1', 'role-2'}}
    }
    --]]
}

-- * ------------------------- box.cfg -------------------------

-- box.cfg mock
local mt = {}
mt.__call = function(self, opts)
    table.insert(calls.box_cfg, opts)

    if opts.memtx_memory == nil then
        return
    end

    if self.memtx_memory == nil then
        self.memtx_memory = opts.memtx_memory
    end

    if opts.memtx_memory == self.memtx_memory then
        return
    end

    if opts.memtx_memory < self.memtx_memory then
        error("cannot decrease memory size at runtime")
    end

    if fail_on.increase_memtx_memory then
        error("cannot decrease memory size at runtime")
    end

    self.memtx_memory = opts.memtx_memory
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

function cartridge.cfg(opts)
    assert(type(opts.console_sock == 'string'))

    local ok, err = pcall(console.listen, 'unix/:' .. opts.console_sock)
    if not ok then
        return nil, err
    end

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

function cartridge.admin_get_servers()
    local res = {}
    for _, s in ipairs(unjoined_servers) do
        table.insert(res, s)
    end

    for _, s in pairs(topology.servers) do
        table.insert(res, s)
    end

    return res
end

function cartridge.admin_get_replicasets()
    local res = {}
    for _, r in pairs(topology.replicasets) do
        table.insert(res, r)
    end
    return res
end

local function __edit_replicaset(params)
    local replicaset
    local replicaset_uuid = params.uuid
    if replicaset_uuid == nil or topology.replicasets[replicaset_uuid] == nil then
        -- create replicaset
        if replicaset_uuid == nil then
            replicaset_uuid = string.format('%s-uuid', params.alias)
        end

        replicaset = {
            uuid = replicaset_uuid,
            alias = params.alias,
            servers = {},
            status = 'healthy',
        }
    else
        replicaset = topology.replicasets[replicaset_uuid]
    end

    if params.roles ~= nil then
        replicaset.roles = params.roles
    end

    if params.weight ~= nil then
        replicaset.weight = params.weight
    end

    if params.all_rw ~= nil then
        replicaset.all_rw = params.all_rw
    end

    if params.vshard_group ~= nil then
        replicaset.vshard_group = params.vshard_group
    end

    if params.join_servers ~= nil then
        for i, join_server in ipairs(params.join_servers) do
            -- find unjoined server
            local unjoined_server
            for _, server in ipairs(unjoined_servers) do
                if server.uri == join_server.uri then
                    unjoined_server = table.deepcopy(server)
                    table.remove(unjoined_servers, i)
                    break
                end
            end

            if unjoined_server == nil then
                return nil, string.format('Server %q is unknown', join_server.uri)
            end

            local server_uuid = string.format('%s-uuid', unjoined_server.alias)

            if topology.servers[server_uuid] ~= nil then
                return nil, string.format('Server %q is already joined', server_uuid)
            end

            topology.servers[server_uuid] = {
                uuid = server_uuid,
                uri = unjoined_server.uri,
                alias = unjoined_server.alias,
                status = 'healthy',
                replicaset = {
                    uuid = replicaset_uuid,
                    alias = replicaset.alias,
                    roles = replicaset.roles,
                }
            }

            table.insert(replicaset.servers, {
                alias = unjoined_server.alias,
                priority = #replicaset.servers + 1,
            })
        end
    end

    if params.failover_priority ~= nil then
        local new_servers = {}
        local added_servers = {}

        for _, s_uuid in ipairs(params.failover_priority) do
            assert(s_uuid ~= nil)
            assert(topology.servers[s_uuid] ~= nil, require('json').encode(topology.servers))

            local server = topology.servers[s_uuid]
            table.insert(new_servers, {
                alias = server.alias,
                priority = #new_servers + 1
            })

            added_servers[server.alias] = true
        end

        local other_servers = {}
        for _, s in ipairs(replicaset.servers) do
            if not added_servers[s.alias] then
                table.insert(other_servers, s.alias)
            end
        end

        table.sort(other_servers)

        for _, alias in ipairs(other_servers) do
            table.insert(new_servers, {
                alias = alias,
                priority = #new_servers + 1,
            })
        end

        replicaset.servers = new_servers
    end

    if vars.become_unhealthy_after_edit then
        replicaset.status = 'unhealthy'
    end

    topology.replicasets[replicaset_uuid] = replicaset
    return true
end

local function __edit_server(params)
    if params.expelled == true then
        assert(params.uuid ~= nil)
        assert(topology.servers[params.uuid] ~= nil)
        local server = topology.servers[params.uuid]

        topology.servers[params.uuid] = nil
        local replicaset_uuid = server.replicaset.uuid
        assert(topology.replicasets[replicaset_uuid] ~= nil)

        local replicaset = topology.replicasets[replicaset_uuid]
        local new_servers = {}
        for _, s in ipairs(replicaset.servers) do
            if s.alias ~= server.alias then
                table.insert(new_servers, {
                    alias = s.alias,
                    priority = #new_servers + 1
                })
            end
        end
        replicaset.servers = new_servers
    end

    return true
end

function cartridge.admin_edit_topology(opts)
    table.insert(calls.edit_topology, opts)

    if fail_on.edit_topology then
        return false, {err = CARTRIDGE_ERR}
    end

    for _, replicaset in ipairs(opts.replicasets or {}) do
        local ok, err = __edit_replicaset(replicaset)
        if ok == nil then return nil, {err = err} end
    end

    for _, server in ipairs(opts.servers or {}) do
        local ok, err = __edit_server(server)
        if ok == nil then return nil, {err = err} end
    end

    return {
        servers = cartridge.admin_get_servers(),
        replicasets = cartridge.admin_get_replicasets(),
    }
end

function cartridge.config_get_readonly()
    return vars.config
end

function cartridge.config_patch_clusterwide(patch)
    -- this function is used only to collect calls
    -- or fail if required
    table.insert(calls.config_patch_clusterwide, patch)

    if fail_on.config_patch_clusterwide then
        return nil, {err = CARTRIDGE_ERR}
    end

    return true
end

local function manage_failover(verb)
    assert(verb == 'enable' or verb == 'disable')
    table.insert(calls.manage_failover, verb)

    if fail_on.manage_failover then
        return nil, {err = CARTRIDGE_ERR}
    end

    return true
end

function cartridge.admin_get_failover()
    return vars.failover
end

function cartridge.admin_enable_failover()
    return manage_failover('enable')
end

function cartridge.admin_disable_failover()
    return manage_failover('disable')
end

-- * ---------------- Module cartridge.vshard-utils ---------------

function cartridge_vshard_utils.can_bootstrap()
    return vars.can_bootstrap_vshard
end

-- * ------------------- Module cartridge.admin -------------------

function cartridge_admin.bootstrap_vshard()
    table.insert(calls.bootstrap_vshard, true)

    if fail_on.bootstrap_vshard then
        return nil, {err = CARTRIDGE_ERR}
    end

    return true
end

-- * ------------------- Module cartridge.auth -------------------

function cartridge_auth.get_params()
    return vars.auth_params
end

function cartridge_auth.set_params(params)
    table.insert(calls.auth_set_params, params)

    if fail_on.auth_set_params then
        return nil, {err = CARTRIDGE_ERR}
    end

    assert(type(params.enabled) == 'boolean' or params.enabled == nil)
    assert(type(params.cookie_max_age) == 'number' or params.cookie_max_age == nil)
    assert(type(params.cookie_renew_age) == 'number' or params.cookie_renew_age == nil)

    if params.enabled ~= nil then
        vars.auth_params.enabled = params.enabled
    end

    if params.cookie_max_age ~= nil then
        vars.auth_params.cookie_max_age = params.cookie_max_age
    end

    if params.cookie_renew_age ~= nil then
        vars.auth_params.cookie_renew_age = params.cookie_renew_age
    end

    return true
end

function cartridge_auth.list_users()
    return vars.users
end

function cartridge_auth.add_user(username, password, fullname, email)
    assert(type(username) == 'string')
    assert(type(password) == 'string' or password == nil)
    assert(type(fullname) == 'string' or fullname == nil)
    assert(type(email) == 'string' or email == nil)

    table.insert(calls.auth_add_user, {
        username = username,
        fullname= fullname,
        email = email,
        password = password,
    })

    if fail_on.auth_add_user then
        return nil, {err = CARTRIDGE_ERR}
    end

    local user = {
        username = username,
        fullname= fullname,
        email = email,
    }

    table.insert(vars.users, user)
    return user
end

function cartridge_auth.get_user(username)
    if fail_on.auth_add_user then
        return nil, {err = CARTRIDGE_ERR}
    end

    for _, user in ipairs(vars.users) do
        if user.username == username then
            return user
        end
    end

    return nil, string.format('User %q not found', username)
end

function cartridge_auth.edit_user(username, password, fullname, email)
    assert(type(username) == 'string')
    assert(type(password) == 'string' or password == nil)
    assert(type(fullname) == 'string' or fullname == nil)
    assert(type(email) == 'string' or email == nil)

    table.insert(calls.auth_edit_user, {
        username = username,
        fullname= fullname,
        email = email,
        password = password,
    })

    if fail_on.auth_edit_user then
        return nil, {err = CARTRIDGE_ERR}
    end

    local user = cartridge_auth.get_user(username)
    if user == nil then
        return nil, string.format('User %q not found', username)
    end

    if password ~= nil then
        -- don't save password
    end

    if fullname ~= nil then
        user.fullname = fullname
    end

    if email ~= nil then
        user.email = email
    end

    return user
end

function cartridge_auth.remove_user(username)
    assert(type(username) == 'string')

    table.insert(calls.auth_remove_user, username)

    if fail_on.auth_remove_user then
        return nil, {err = CARTRIDGE_ERR}
    end

    local user = cartridge_auth.get_user(username)
    if user == nil then
        return nil, string.format('User %q not found', username)
    end

    return true
end

-- * --------------- Module cartridge.webui.api-auth ---------------

function cartridge_webui_auth.get_auth_params()
    return vars.webui_auth_params
end

-- * ---------------------- Module membership ----------------------

function membership.myself()
    return vars.membership_myself
end

function membership.members()
    return vars.membership_members
end

-- * ----------------------- Internal helpers ----------------------

-- * ----------------------- functions calls -----------------------

function cartridge.internal.set_fail(func, value)
    assert(fail_on[func] ~= nil)
    assert(type(value) == 'boolean')
    fail_on[func] = value
end

function cartridge.internal.clear_calls(func)
    assert(calls[func] ~= nil)
    calls[func] = {}
end

function cartridge.internal.get_calls(func)
    assert(calls[func] ~= nil)
    return calls[func]
end

-- * --------------------------- vars ---------------------------

function cartridge.internal.set_variable(name, value)
    assert(vars[name] ~= nil)
    assert(type(value) == type(vars[name]))
    vars[name] = value
end

-- * ------------------------- topology -------------------------

function cartridge.internal.add_topology_server(s)
    for _, p in ipairs({'uuid', 'uri', 'alias', 'status'}) do
        assert(type(s[p]) == 'string')
    end
    assert(s.replicaset ~= nil)
    assert(type(s.replicaset) == 'table')
    assert(type(s.replicaset.alias) == 'string')
    assert(type(s.replicaset.uuid) == 'string')
    assert(type(s.replicaset.roles) == 'table')

    assert(topology.servers[s.uuid] == nil)
    topology.servers[s.uuid] = s
end

function cartridge.internal.add_topology_replicaset(r)
    for _, p in ipairs({'uuid', 'alias', 'status'}) do
        assert(type(r[p]) == 'string')
    end
    assert(type(r.roles) == 'table')
    assert(type(r.weight) == 'number' or r.weight == nil)
    assert(type(r.all_rw) == 'boolean' or r.all_rw == nil)

    assert(type(r.servers) == 'table')
    for _, s in ipairs(r.servers) do
        assert(type(s.alias) == 'string')
        assert(type(s.priority) == 'number')
    end

    assert(topology.replicasets[r.uuid] == nil)
    topology.replicasets[r.uuid] = r
end

function cartridge.internal.add_unjoined_server(s)
    for _, p in ipairs({'uri', 'alias', 'status'}) do
        assert(type(s[p]) == 'string')
    end
    table.insert(unjoined_servers, s)
end

cartridge.internal.topology = topology
cartridge.internal.unjoined_servers = unjoined_servers

return cartridge
