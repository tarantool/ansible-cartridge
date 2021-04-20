local fmt, age, t = ...

-- comment

--[[ one more comment ]]

---[[ this is one-line comment
local argparse = require('cartridge.argparse')
local opts, err = argparse.get_opts({
    app_name = 'string',
    instance_name = 'string',
})
---]]

--[[ ]] assert(err == nil, tostring(err))

local instance_id --[=[ ]=]
if opts.instance_name == nil then
    instance_id = opts.app_name
else
    instance_id = string.format('%s.%s', opts.app_name, opts.instance_name)
end

return unpack({
    [[This snippet was evaled from file]],
    string.format(fmt, instance_id),
    string.format([=[I am %s seconds old]=], age),
    require('yaml').encode(t),
})
