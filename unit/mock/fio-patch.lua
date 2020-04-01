local fio = require('fio')

local files = {}

-- class File

local File = {}

function File:new(opts)
    assert(type(opts.path) == 'string')
    assert(type(opts.content) == 'string' or opts.content == nil)

    local file = {}

    file.path = opts.path
    file.content = opts.content or ''
    file.content_was_read = false

    setmetatable(file, self)
    self.__index = self

    return file
end

function File:read()
    if self.content_was_read then
        return ''
    end

    self.content_was_read = true
    return self.content
end

function File:close()
    self.content_was_read = false
end

-- fio functions

fio.path.exists = function(path)
    return files[path] ~= nil
end

fio.open = function(path)
    return files[path]
end

-- test helpers

fio.path.write_file = function(opts)
    assert(type(opts.path) == 'string')
    assert(type(opts.content) == 'string' or opts.content == nil)

    local file = File:new(opts)
    files[file.path] = file
end

fio.path.remove_file = function(path)
    files[path] = nil
end
