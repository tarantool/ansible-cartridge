local console = require('console')

local cartridge = {}
cartridge.internal = {}

local vshard_utils = {}
package.loaded['cartridge.vshard-utils'] = vshard_utils

local admin = {}
package.loaded['cartridge.admin'] = admin

local known_servers = {}
local probed_servers = {}

local CARTRIDGE_ERR = 'cartridge err'

local fail_on = {
    increase_memtx_memory = false,
    edit_topology = false,
    bootstrap_vshard = false,
    config_patch_clusterwide = false,
    manage_failover = false,
}

local calls = {
    increase_memtx_memory = {},
    edit_topology = {},
    bootstrap_vshard = {},
    config_patch_clusterwide = {},
    manage_failover = {},
}

local vars = {
    config = {},
    failover = false,
    can_bootstrap_vshard = true,
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
    probed_servers[advertise_uri] = true

    if known_servers[advertise_uri] then
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

function vshard_utils.can_bootstrap()
    return vars.can_bootstrap_vshard
end

-- * ------------------- Module cartridge.admin -------------------

function admin.bootstrap_vshard()
    if fail_on.bootstrap_vshard then
        return nil, {err = CARTRIDGE_ERR}
    end

    return true
end

-- * ---------------------- Internal helpers ---------------------

-- * ----------------- cartridge functions calls -----------------

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

-- * ------------------------ membership ------------------------

function cartridge.internal.server_was_probed(advertise_uri)
    assert(type(advertise_uri) == 'string')
    return probed_servers[advertise_uri] == true
end

function cartridge.internal.clear_probed(advertise_uri)
    assert(type(advertise_uri) == 'string')
    probed_servers[advertise_uri] = nil
end

function cartridge.internal.set_known_server(advertise_uri, probe_ok)
    assert(type(advertise_uri) == 'string')
    assert(type(probe_ok) == 'boolean')

    known_servers[advertise_uri] = probe_ok
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
