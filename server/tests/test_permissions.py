from lsia.domain.permissions import Permission, Role, has_permission


def test_admin_allows_everything():
    role = Role(kind="administrator")
    assert role.allows(Permission.FINALIZE_RESULTS)
    assert has_permission(role.to_json(), Permission.MANAGE_TEACHERS)


def test_teacher_defaults_block_admin_actions():
    role = Role(kind="teacher", classes=["SS2A"], subjects=["MATHEMATICS"])
    assert role.allows(Permission.ENTER_CA)
    assert not role.allows(Permission.MANAGE_TEACHERS)
    assert not role.allows(Permission.FINALIZE_RESULTS)
