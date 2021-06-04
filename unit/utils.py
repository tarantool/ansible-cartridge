def get_member(alias, with_alias=True, empty=False, empty_payload=False,
               uuid=None, with_uuid=False, status=None, state=None):
    member = {'uri': '%s-uri' % alias}

    if empty:
        member.update({'empty': True})
        return member

    if empty_payload:
        member.update({'empty_payload': True})
        return member

    if with_alias:
        member.update({'alias': alias})

    if uuid is not None:
        member.update({'uuid': uuid})
    elif with_uuid:
        member.update({'uuid': '%s-uuid' % alias})

    if status is not None:
        member.update({'status': status})

    if state is not None:
        member.update({'state': state})

    return member
