local membership = {}
membership.internal = {}

local myself = {
    status = 'alive',
}

local members = {}

--[[
Member:
{
    uri: "localhost:33001"
    status: "alive"
    incarnation: 1
    payload:
      uuid: "2d00c500-2570-4019-bfcc-ab25e5096b73"
      alias: "instance-1"
    timestamp: 1522427330993752
    clock_delta: 27810
}
--]]

function membership.myself()
    return myself
end

function membership.members()
    return members
end

function membership.internal.set_status(status)
    myself.status = status
end

function membership.internal.add_member(opts)
    assert(type(opts.uri) == 'string')
    assert(type(opts.status) == 'string' or opts.status == nil)
    assert(type(opts.uuid) == 'string' or opts.uuid == nil)
    assert(type(opts.alias) == 'string' or opts.alias == nil)

    local member = {
        uri = opts.uri,
        status = opts.status or 'alive',
        incarnation = 1,
        payload = {
            uuid = opts.uuid,
            alias = opts.alias
        }
    }

    members[opts.uri] = member
end

function membership.internal.clear_members()
    members = {}
end

return membership
