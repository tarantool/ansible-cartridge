local console = require('console')

local cartridge = {}
cartridge.internal = {}

local known_servers = {}
local probed_servers = {}

-- cfg
function cartridge.cfg(opts)
    assert(type(opts.console_sock == 'string'))

    local ok, err = pcall(console.listen, 'unix/:' .. opts.console_sock)
    if not ok then
        return nil, err
    end

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

return cartridge
