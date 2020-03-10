local console = require('console')

local cartridge = {}

cartridge.topology = {}

function cartridge.cfg(opts)
    assert(type(opts.console_sock == 'string'))

    local ok, err = pcall(console.listen, 'unix/:' .. opts.console_sock)
    if not ok then
        return nil, err
    end

    return true
end

return cartridge
