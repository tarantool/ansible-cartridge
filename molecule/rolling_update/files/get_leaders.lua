local cartridge = require('cartridge')

local replicasets, err = cartridge.admin_get_replicasets()
assert(err == nil, tostring(err))

local ret = {}
for _, replicaset in ipairs(replicasets) do
    local replicaset_alias = replicaset.alias
    local leader_alias = replicaset.active_master.alias

    ret[replicaset_alias] = leader_alias
end

return ret
