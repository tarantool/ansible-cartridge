#!/usr/bin/env tarantool
require('strict').on()

local fio = require('fio')
local app_dir = fio.abspath(fio.dirname(arg[0]))

package.path = app_dir .. '/.rocks/share/tarantool/?.lua;' .. package.path
package.path = app_dir .. '/.rocks/share/tarantool/?/init.lua;' .. package.path
package.path = app_dir .. '/?/init.lua;' .. package.path
package.path = app_dir .. '/?.lua;' .. package.path

package.cpath = app_dir .. '/.rocks/lib/tarantool/?.so;' .. package.cpath
package.cpath = app_dir .. '/.rocks/lib/tarantool/?.dylib;' .. package.cpath
package.cpath = app_dir .. '/?.so;' .. package.cpath
package.cpath = app_dir .. '/?.dylib;' .. package.cpath

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
