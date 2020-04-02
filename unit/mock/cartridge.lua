local console = require('console')

local cartridge = {}
cartridge.internal = {}

local known_servers = {}
local probed_servers = {}
local fail_on_increasing_memtx_memory = false

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

    if fail_on_increasing_memtx_memory then
        error("cannot decrease memory size at runtime")
    end

    self.memtx_memory = opts.memtx_memory
end

local box_cfg_table = {}
setmetatable(box_cfg_table, mt)

local box_cfg_function = function() end

box.cfg = box_cfg_function

-- cfg
function cartridge.cfg(opts)
    assert(type(opts.console_sock == 'string'))

    local ok, err = pcall(console.listen, 'unix/:' .. opts.console_sock)
    if not ok then
        return nil, err
    end

    box.cfg = box_cfg_table

    return true
end

-- probe server
function cartridge.admin_probe_server(advertise_uri)
    assert(type(advertise_uri) == 'string')
    probed_servers[advertise_uri] = true

    if known_servers[advertise_uri] then
        return true
    end

    return false, string.format('Probe %q failed', advertise_uri)
end

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

function cartridge.internal.set_fail_on_memory_inc(value)
    assert(type(value) == 'boolean')
    fail_on_increasing_memtx_memory = value
end

function cartridge.internal.set_box_cfg_function(value)
    assert(type(value) == 'boolean')
    if value then
        box.cfg = box_cfg_function
    else
        box.cfg = box_cfg_table
    end
end

return cartridge
