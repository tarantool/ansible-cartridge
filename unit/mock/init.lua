#!/usr/bin/env tarantool
require('strict').on()

local fio = require('fio')

local script_dir = fio.abspath(fio.dirname(arg[0]))
package.path = package.path .. ';' .. script_dir .. '/?.lua'

require('fio-patch')

local cartridge = require('cartridge')

local console_sock = os.getenv('TARANTOOL_CONSOLE_SOCK')
assert(type(console_sock) == 'string')

local ok, err = pcall(cartridge.cfg, {
    console_sock = console_sock,
})
if not ok then
    require('log').error('%s', err)
    os.exit(1)
end
