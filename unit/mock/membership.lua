local membership = {}

local myself = {
    status = 'alive',
}

function membership.myself()
    return myself
end

function membership.set_status(status)
    myself.status = status
end

return membership
